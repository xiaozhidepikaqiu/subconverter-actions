import os
import sys
import json
import base64
import shutil
import requests
import subprocess
import time
from datetime import datetime
from pathlib import Path

class SubConverter:
    def __init__(self):
        self.subconverter_dir = "subconverter"
        self.subconverter_exe = "subconverter"
        self.config_file = "converted_config.yaml"
        self.max_retries = 3
        self.timeout = 60  # 增加到 180 秒

    def download_subconverter(self):
        """下载并设置 subconverter"""
        try:
            print("Downloading subconverter...")
            
            # 清理旧文件
            if os.path.exists(self.subconverter_dir):
                shutil.rmtree(self.subconverter_dir)
            if os.path.exists("subconverter_linux64.tar.gz"):
                os.remove("subconverter_linux64.tar.gz")

            response = requests.get(
                "https://github.com/tindy2013/subconverter/releases/latest/download/subconverter_linux64.tar.gz",
                stream=True,
                timeout=30
            )
            response.raise_for_status()
            
            print("Saving subconverter archive...")
            with open("subconverter_linux64.tar.gz", "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print("Extracting subconverter...")
            subprocess.run(["tar", "-xzf", "subconverter_linux64.tar.gz"], check=True)
            
            print("Setting permissions...")
            subprocess.run(["chmod", "+x", f"{self.subconverter_dir}/{self.subconverter_exe}"], check=True)
            
            print("Cleaning up...")
            os.remove("subconverter_linux64.tar.gz")
            
            # 验证安装
            if not os.path.exists(f"{self.subconverter_dir}/{self.subconverter_exe}"):
                raise Exception("Subconverter executable not found after installation")
                
            print("Subconverter setup completed successfully")
            return True
            
        except Exception as e:
            print(f"Error setting up subconverter: {str(e)}")
            return False

    def convert_subscription(self, subscription_url):
        """转换订阅链接"""
        for attempt in range(self.max_retries):
            try:
                print(f"Conversion attempt {attempt + 1}/{self.max_retries}")
                
                if not os.path.exists(f"{self.subconverter_dir}/{self.subconverter_exe}"):
                    print("Subconverter not found, downloading...")
                    if not self.download_subconverter():
                        raise Exception("Failed to setup subconverter")

                print(f"Starting conversion process... (timeout: {self.timeout}s)")
                
                # 运行转换进程
                process = subprocess.Popen(
                    [
                        f"./{self.subconverter_dir}/{self.subconverter_exe}",
                        "-u", subscription_url,
                        "-t", "clash",
                        "--cache"
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                # 使用 communicate 带超时
                try:
                    stdout, stderr = process.communicate(timeout=self.timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    print(f"Process killed due to timeout ({self.timeout}s)")
                    raise Exception(f"Conversion timed out after {self.timeout} seconds")

                # 检查返回码
                if process.returncode != 0:
                    print(f"Conversion process failed with return code: {process.returncode}")
                    print(f"Error output: {stderr}")
                    raise Exception(f"Conversion failed: {stderr}")

                # 保存输出
                print("Saving converted configuration...")
                with open(self.config_file, "w", encoding="utf-8") as f:
                    f.write(stdout)

                # 验证输出文件
                if not os.path.exists(self.config_file):
                    raise Exception("Output file not created")

                file_size = os.path.getsize(self.config_file)
                print(f"Configuration file created successfully (size: {file_size} bytes)")
                
                if file_size == 0:
                    raise Exception("Output file is empty")

                return True

            except Exception as e:
                print(f"Error during conversion attempt {attempt + 1}: {str(e)}")
                if attempt < self.max_retries - 1:
                    print(f"Waiting 10 seconds before retry...")
                    time.sleep(10)
                else:
                    print("All conversion attempts failed")
                    raise

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
            print("Preparing config data for Cloudflare KV...")
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

            print(f"Cloudflare KV response status: {response.status_code}")
            
            if not response.ok:
                print(f"Response content: {response.text}")
                raise Exception(f"API request failed: {response.status_code} - {response.text}")

            print("Successfully updated Cloudflare KV")
            return True

        except Exception as e:
            print(f"Error updating Cloudflare KV: {str(e)}")
            return False
        finally:
            self.session.close()

def main():
    try:
        print("\n=== Starting config update process ===")
        print(f"Current time (UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
        print("System environment check...")
        
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

        # 初始化转换器并执行转换
        print("\n=== Starting subscription conversion ===")
        converter = SubConverter()
        
        if not converter.convert_subscription(os.environ["SUBSCRIPTION_URL"]):
            raise Exception("Failed to convert subscription")

        # 读取转换后的配置
        print("\n=== Reading converted configuration ===")
        if not os.path.exists(converter.config_file):
            raise Exception("Converted config file not found")

        with open(converter.config_file, "r", encoding="utf-8") as f:
            config_content = f.read()

        if not config_content.strip():
            raise Exception("Converted configuration is empty")

        print(f"Configuration file size: {len(config_content)} bytes")

        # 更新 Cloudflare KV
        print("\n=== Updating Cloudflare KV ===")
        cf_kv = CloudflareKV(
            os.environ["CF_ACCOUNT_ID"],
            os.environ["CF_NAMESPACE_ID"],
            os.environ["CF_API_TOKEN"]
        )

        if not cf_kv.update_config(os.environ["SUBSCRIPTION_URL"], config_content):
            raise Exception("Failed to update Cloudflare KV")

        print("\n=== Config update process completed successfully ===")

    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
