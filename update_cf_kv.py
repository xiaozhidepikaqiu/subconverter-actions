import os
import sys
import json
import base64
import requests
from datetime import datetime, timedelta

class CloudflareKV:
    def __init__(self, account_id, namespace_id, api_token):
        self.account_id = account_id
        self.namespace_id = namespace_id
        self.api_token = api_token
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/{namespace_id}/values"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

    def update_config(self, content):
        """更新 Cloudflare KV 存储"""
        try:
            print("Updating Cloudflare KV...")
            response = requests.put(
                f"{self.base_url}/current_config",
                headers=self.headers,
                json={
                    "converted_config": base64.b64encode(content.encode()).decode(),
                    "update_time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                },
                timeout=30
            )
            
            if not response.ok:
                raise Exception(f"API request failed: {response.status_code} - {response.text}")
            
            print("Successfully updated Cloudflare KV")
            return True
            
        except Exception as e:
            print(f"Error updating KV: {str(e)}")
            return False

def convert_subscribe(subscribe_dict):
    """转换订阅"""
    print("Converting subscription...")
    base_url = "http://localhost:25500/sub"
    results = {}
    
    for filename, params in subscribe_dict.items():
        url = f"{base_url}{params}"
        print(f"Converting {filename}...")
        
        try:
            response = requests.get(url, timeout=30)
            if response.ok:
                content = response.text
                # 添加更新时间
                update_time = (datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
                content += f"\n\n# Updated on {update_time}\n"
                results[filename] = content
            else:
                print(f"Error converting {filename}: {response.status_code}")
        except Exception as e:
            print(f"Error converting {filename}: {str(e)}")
    
    return results

def main():
    try:
        print("\n=== Starting config update process ===")
        print(f"Current time (UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")

        # 检查环境变量
        required_vars = {
            "CF_ACCOUNT_ID": "Cloudflare Account ID",
            "CF_NAMESPACE_ID": "KV Namespace ID",
            "CF_API_TOKEN": "API Token",
            "CONVERT_PARAM": "Convert Parameters"
        }

        for var, desc in required_vars.items():
            if var not in os.environ:
                raise Exception(f"Missing {desc} ({var})")
            print(f"Found {var}")

        # 解码转换参数
        try:
            subscribe_dict = json.loads(base64.b64decode(os.environ['CONVERT_PARAM']).decode("utf-8"))
        except Exception as e:
            raise Exception(f"Failed to decode CONVERT_PARAM: {str(e)}")

        # 转换订阅
        results = convert_subscribe(subscribe_dict)
        if not results:
            raise Exception("No configurations were converted successfully")

        # 初始化 Cloudflare KV 客户端
        cf_kv = CloudflareKV(
            os.environ["CF_ACCOUNT_ID"],
            os.environ["CF_NAMESPACE_ID"],
            os.environ["CF_API_TOKEN"]
        )

        # 更新每个配置到 KV
        for filename, content in results.items():
            if not cf_kv.update_config(content):
                raise Exception(f"Failed to update {filename} to Cloudflare KV")

        print("\n=== Config update process completed successfully ===")

    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
