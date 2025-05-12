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

    def check_key_exists(self, key_name):
        """检查 KV 键是否存在"""
        try:
            response = requests.get(
                f"{self.base_url}/{key_name}",
                headers=self.headers,
                timeout=30
            )
            return response.status_code == 200
        except:
            return False

    def update_config(self, key_name, content, headers=None):
        """更新 Cloudflare KV 存储"""
        try:
            # 检查键是否已存在
            is_update = self.check_key_exists(key_name)
            operation = "Updating" if is_update else "Creating"
            print(f"{operation} Cloudflare KV for {key_name}...")
            
            # 构建存储数据
            kv_data = {
                "converted_config": base64.b64encode(content.encode()).decode(),
                "update_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "current_user": "xiaozhidepikaqiu",  # 添加当前用户
                "headers": headers or {}
            }
            
            response = requests.put(
                f"{self.base_url}/{key_name}",
                headers=self.headers,
                json=kv_data,
                timeout=30
            )
            
            if not response.ok:
                raise Exception(f"API request failed: {response.status_code} - {response.text}")
            
            print(f"Successfully {operation.lower()}d Cloudflare KV for {key_name}")
            return True
            
        except Exception as e:
            print(f"Error {operation.lower()}ing KV for {key_name}: {str(e)}")
            return False


def get_original_headers(url):
    """获取原始订阅的响应头"""
    try:
        response = requests.get(
            url,
            headers={
                'User-Agent': 'clash-verge/v1.0',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            },
            timeout=30
        )
        
        if response.ok:
            headers = {}
            # 保存所有相关的响应头
            headers_to_save = [
                'subscription-userinfo',
                'content-disposition',
                'profile-update-interval',
                'profile-title',
                'profile-web-page-url',
                'profile-update-timestamp',
                'support-url'
            ]
            
            for header in headers_to_save:
                if header in response.headers:
                    headers[header] = response.headers[header]
            
            # 保存其他以 'profile-' 开头的头
            for key, value in response.headers.items():
                key_lower = key.lower()
                if key_lower.startswith('profile-') and key_lower not in headers:
                    headers[key_lower] = value
            
            return headers
    except Exception as e:
        print(f"Warning: Failed to fetch original headers: {str(e)}")
    
    return None

def convert_subscribe(subscribe_dict):
    """转换订阅"""
    print("Converting subscription...")
    base_url = "http://localhost:25500/sub"
    results = {}
    
    # 获取原始订阅的响应头
    sub_headers = None
    if 'SUBSCRIPTION_URL' in os.environ:
        sub_headers = get_original_headers(os.environ['SUBSCRIPTION_URL'])
    
    for filename, params in subscribe_dict.items():
        url = f"{base_url}{params}"
        print(f"Converting {filename}...")
        
        try:
            response = requests.get(url, timeout=30)
            if response.ok:
                content = response.text
                update_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                content += f"\n\n# Updated on {update_time}\n"
                results[filename] = {
                    "content": content,
                    "headers": sub_headers
                }
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

        # 更新每个配置到 KV，使用文件名作为 key
        success_count = 0
        for filename, data in results.items():
            # 从文件名中移除扩展名作为 KV 的 key
            key_name = filename.rsplit('.', 1)[0]
            if cf_kv.update_config(key_name, data["content"], data["headers"]):
                success_count += 1
            else:
                print(f"Failed to update {filename} to Cloudflare KV")

        if success_count == 0:
            raise Exception("No configurations were successfully updated to KV")
        else:
            print(f"\n=== Successfully updated {success_count} configurations to KV ===")

    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
