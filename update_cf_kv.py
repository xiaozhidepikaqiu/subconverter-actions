import os
import sys
import json
import base64
import shutil
import requests
import subprocess
from datetime import datetime
from pathlib import Path

class SubConverter:
    def __init__(self):
        self.subconverter_dir = "subconverter"
        self.subconverter_exe = "subconverter"
        self.config_file = "converted_config.yaml"

    def download_subconverter(self):
        """下载并设置 subconverter"""
        try:
            print("Downloading subconverter...")
            response = requests.get(
                "https://github.com/tindy2013/subconverter/releases/latest/download/subconverter_linux64.tar.gz",
                stream=True,
                timeout=30
            )
            response.raise_for_status()
            
            with open("subconverter_linux64.tar.gz", "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            subprocess.run(["tar", "-xzf", "subconverter_linux64.tar.gz"], check=True)
            subprocess.run(["chmod", "+x", f"{self.subconverter_dir}/{self.subconverter_exe}"], check=True)
            os.remove("subconverter_linux64.tar.gz")
            print("Subconverter setup completed")
            return True
            
        except Exception as e:
            print(f"Error setting up subconverter: {str(e)}")
            return False

    def convert_subscription(self, subscription_url):
        """转换订阅链接"""
        try:
            if not os.path.exists(f"{self.subconverter_dir}/{self.subconverter_exe}"):
                if not self.download_subconverter():
                    raise Exception("Failed to setup subconverter")

            print(f"Converting subscription...")
            
            result = subprocess.run(
                [
                    f"./{self.subconverter_dir}/{self.subconverter_exe}",
                    "-u", subscription_url,
                    "-t", "clash",
                    "--cache"
                ],
                capture_output=True,
                text=True,
                timeout=60  # 60秒超时
            )

            if result.returncode != 0:
                raise Exception(f"Conversion failed: {result.stderr}")

            with open(self.config_file, "w", encoding="utf-8") as f:
                f.write(result.stdout)

            print("Subscription converted successfully")
            return True

        except Exception as e:
            print(f"Error converting subscription: {str(e)}")
            return False

class CloudflareKV:
    def __init__(self, account_id, namespace_id, api_token):
        self.account_id = account_id
        self.namespace_id = namespace_id
        self.api_token = api_token
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/{namespace_id}/values"
        self.session = self._create_session()

    def _create_session(self):
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        })
        return session

    def update_config(self, original_url, config_content):
        """更新 Cloudflare KV 存储"""
        try:
            print("Preparing config data...")
            config_data = {
                "original_url": original_url,
                "converted_config": base64.b64encode(config_content.encode()).decode(),
                "update_time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            }

            print("Sending request to Cloudflare KV...")
            response = self.session.put(
                f"{self.base_url}/current_config",
                json=config_data,
                timeout=30
            )

            print(f"Response status code: {response.status_code}")
            
            if not response.ok:
                raise Exception(f"API request failed: {response.status_code} - {response.text}")

            print("Successfully updated Cloudflare KV")
            return True

        except Exception as e:
            print(f"Error updating KV: {str(e)}")
            return False
        finally:
            self.session.close()

def main():
    try:
        print("Starting config update process...")
        print(f"Current time (UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")

        # 检查环境变量
        required_vars = {
            "CF_ACCOUNT_ID": "Cloudflare Account ID",
            "CF_NAMESPACE_ID": "KV Namespace ID",
            "CF_API_TOKEN": "API Token",
            "SUBSCRIPTION_URL": "Subscription URL"
        }

        for var, desc in required_vars.items():
            if var not in os.environ:
                raise Exception(f"Missing {desc} ({var})")
            print(f"Found {var}")

        # 初始化转换器
        converter = SubConverter()
        
        # 转换订阅
        if not converter.convert_subscription(os.environ["SUBSCRIPTION_URL"]):
            raise Exception("Failed to convert subscription")

        # 读取转换后的配置
        print("Reading converted configuration...")
        if not os.path.exists(converter.config_file):
            raise Exception("Converted config file not found")

        with open(converter.config_file, "r", encoding="utf-8") as f:
            config_content = f.read()

        if not config_content.strip():
            raise Exception("Converted configuration is empty")

        # 更新 Cloudflare KV
        cf_kv = CloudflareKV(
            os.environ["CF_ACCOUNT_ID"],
            os.environ["CF_NAMESPACE_ID"],
            os.environ["CF_API_TOKEN"]
        )

        if not cf_kv.update_config(os.environ["SUBSCRIPTION_URL"], config_content):
            raise Exception("Failed to update Cloudflare KV")

        print("Config update process completed successfully")

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
