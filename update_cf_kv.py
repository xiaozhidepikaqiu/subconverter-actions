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
            # 下载 subconverter
            response = requests.get(
                "https://github.com/tindy2013/subconverter/releases/latest/download/subconverter_linux64.tar.gz",
                stream=True
            )
            response.raise_for_status()
            
            # 保存文件
            with open("subconverter_linux64.tar.gz", "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # 解压文件
            subprocess.run(["tar", "-xzf", "subconverter_linux64.tar.gz"], check=True)
            
            # 设置执行权限
            subprocess.run(["chmod", "+x", f"{self.subconverter_dir}/{self.subconverter_exe}"], check=True)
            
            # 清理下载文件
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

            print(f"Converting subscription: {subscription_url}")
            
            # 执行转换命令
            result = subprocess.run(
                [
                    f"./{self.subconverter_dir}/{self.subconverter_exe}",
                    "-u", subscription_url,
                    "-t", "clash"
                ],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                raise Exception(f"Conversion failed: {result.stderr}")

            # 保存转换后的配置
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

    def update_config(self, original_url, config_content):
        """更新 Cloudflare KV 存储"""
        try:
            # 准备配置数据
            config_data = {
                "original_url": original_url,
                "converted_config": base64.b64encode(config_content.encode()).decode(),
                "update_time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            }

            # 设置请求头
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }

            # 发送请求更新 KV
            response = requests.put(
                f"{self.base_url}/current_config",
                headers=headers,
                json=config_data
            )

            if not response.ok:
                raise Exception(f"API request failed: {response.status_code} - {response.text}")

            print("Successfully updated Cloudflare KV")
            return True

        except Exception as e:
            print(f"Error updating KV: {str(e)}")
            return False

def main():
    try:
        # 从环境变量获取配置
        required_env_vars = {
            "CF_ACCOUNT_ID": "Cloudflare Account ID",
            "CF_NAMESPACE_ID": "KV Namespace ID",
            "CF_API_TOKEN": "API Token",
            "SUBSCRIPTION_URL": "Subscription URL"
        }

        # 检查所需的环境变量
        for var, description in required_env_vars.items():
            if var not in os.environ:
                raise Exception(f"Missing required environment variable: {var} ({description})")

        # 初始化转换器
        converter = SubConverter()
        
        # 转换订阅
        if not converter.convert_subscription(os.environ["SUBSCRIPTION_URL"]):
            raise Exception("Subscription conversion failed")

        # 读取转换后的配置
        with open(converter.config_file, "r", encoding="utf-8") as f:
            config_content = f.read()

        # 初始化 Cloudflare KV 客户端
        cf_kv = CloudflareKV(
            os.environ["CF_ACCOUNT_ID"],
            os.environ["CF_NAMESPACE_ID"],
            os.environ["CF_API_TOKEN"]
        )

        # 更新 KV 存储
        if not cf_kv.update_config(os.environ["SUBSCRIPTION_URL"], config_content):
            raise Exception("Failed to update Cloudflare KV")

        print("Config update process completed successfully")

    except Exception as e:
        print(f"Error in main process: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
