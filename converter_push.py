import os
import sys
import json
import base64
import requests
import urllib.parse
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
            
            # 构建存储数据，使用文件名作为配置键
            kv_data = {
                key_name: base64.b64encode(content.encode()).decode(),  # 使用文件名作为键
                "update_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
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
                    if header == 'content-disposition':
                        # 处理 content-disposition 头，添加 T: 前缀
                        content_disp = response.headers[header]
                        if 'filename' in content_disp:
                            # 如果是 filename*= 格式
                            if 'filename*=' in content_disp:
                                parts = content_disp.split("''")
                                if len(parts) > 1:
                                    encoding_part = parts[0]
                                    filename_part = parts[1]
                                    new_filename = f"T:{filename_part}"
                                    headers[header] = f"{encoding_part}''{new_filename}"
                            # 如果是简单的 filename= 格式
                            else:
                                filename_start = content_disp.find('filename=') + 9
                                filename = content_disp[filename_start:]
                                if filename.startswith('"'):
                                    filename = filename[1:-1]
                                new_filename = f"T:{filename}"
                                headers[header] = f"attachment;filename={new_filename}"
                    else:
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


def extract_url_from_params(params):
    """从参数中提取订阅 URL"""
    try:
        print(f"Processing params: {params}")
        # 查找 "&url=" 和下一个 "&" 之间的内容
        start = params.find("&url=") + 5
        if start > 4:  # 确保找到了 "&url="
            end = params.find("&", start)
            if end == -1:  # 如果是最后一个参数
                url = params[start:]
            else:
                url = params[start:end]
            
            # URL 解码
            decoded_url = urllib.parse.unquote(url)
            print(f"Decoded URL: {decoded_url}")
            
            # 检查 URL 是否包含协议前缀，如果没有则添加 https://
            if not decoded_url.startswith(('http://', 'https://')):
                decoded_url = 'https://' + decoded_url
            
            return decoded_url
    except Exception as e:
        print(f"Error extracting URL from params: {str(e)}")
    return None


def convert_subscribe(subscribe_dict):
    """转换订阅"""
    print("Converting subscription...")
    base_url = "http://localhost:25500/sub"
    results = {}
    
    for filename, params in subscribe_dict.items():
        print(f"Converting {filename}...")
        
        # 从参数中提取原始订阅 URL
        original_url = extract_url_from_params(params)
        print(f"Extracted URL for {filename}: {original_url}")
        
        if not original_url:
            print(f"Warning: Could not extract URL from params for {filename}")
            continue
            
        # 获取该订阅的响应头
        print(f"Fetching headers for {filename} from {original_url}")
        sub_headers = get_original_headers(original_url)
        
        if sub_headers:
            print(f"Successfully got headers for {filename}")
        else:
            print(f"Warning: No headers received for {filename}")
        
        # 转换配置
        url = f"{base_url}{params}"
        try:
            print(f"Converting configuration using URL: {url}")
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
            "CF_KV_ID": "KV Namespace ID",
            "CF_ACCOUNT_API_TOKEN": "API Token",
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
            os.environ["CF_KV_ID"],
            os.environ["CF_ACCOUNT_API_TOKEN"]
        )

        # 更新每个配置到 KV，使用文件名作为 key
        success_count = 0
        for filename, data in results.items():
            if cf_kv.update_config(filename, data["content"], data["headers"]):
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
