import os
import sys
import json
import base64
import requests
import urllib.parse
from datetime import datetime, timedelta


class CloudflareKV:
    def __init__(self, account_id, kv_id, account_api_token):
        self.account_id = account_id
        self.kv_id = kv_id
        self.account_api_token = account_api_token
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/{kv_id}"
        self.headers = {
            "Authorization": f"Bearer {account_api_token}",
            "Content-Type": "application/json"
        }
        # 定义不会被清理的特殊键名
        self.protected_keys = ["CONVERT_PARAM"]
    
    def list_keys(self):
        """获取所有键名"""
        try:
            response = requests.get(
                f"{self.base_url}/keys",
                headers=self.headers,
                timeout=30
            )
            print(f"Listing keys response status: {response.status_code}")
            if response.ok:
                data = response.json()
                if data.get("success"):
                    keys = [key["name"] for key in data.get("result", [])]
                    print(f"Found existing keys: {keys}")
                    return keys
                else:
                    print(f"API error: {data}")
            return []
        except Exception as e:
            print(f"Error listing keys: {str(e)}")
            return []
    
    def delete_key(self, key_name):
        """删除指定的键"""
        try:
            # 检查是否是受保护的键
            if key_name in self.protected_keys:
                print(f"Skipping deletion of protected key: {key_name}")
                return False
                
            encoded_key = urllib.parse.quote(key_name)
            response = requests.delete(
                f"{self.base_url}/values/{encoded_key}",
                headers=self.headers,
                timeout=30
            )
            if response.ok:
                print(f"Successfully deleted key: {key_name}")
                return True
            print(f"Failed to delete key {key_name}: {response.status_code}")
            return False
        except Exception as e:
            print(f"Error deleting key {key_name}: {str(e)}")
            return False

    def clean_unused_configs(self, current_configs):
        """清理不再使用的配置"""
        print(f"Current configs to keep: {current_configs}")
        existing_keys = self.list_keys()
        print(f"Existing keys in KV: {existing_keys}")
        
        # 过滤掉受保护的键
        keys_to_delete = [
            key for key in existing_keys 
            if key not in current_configs and key not in self.protected_keys
        ]
        print(f"Keys that will be deleted: {keys_to_delete}")
        
        if not keys_to_delete:
            print("No unused configurations to clean")
            return 0

        print(f"\nCleaning {len(keys_to_delete)} unused configurations:")
        deleted_count = 0
        for key in keys_to_delete:
            if self.delete_key(key):
                deleted_count += 1
        
        print(f"Successfully cleaned {deleted_count} unused configurations")
        return deleted_count

    def check_key_exists(self, key_name):
        """检查 KV 键是否存在"""
        try:
            encoded_key = urllib.parse.quote(key_name)
            response = requests.get(
                f"{self.base_url}/values/{encoded_key}",
                headers=self.headers,
                timeout=30
            )
            return response.status_code == 200
        except:
            return False

    def update_config(self, key_name, content, headers=None):
        """更新 CF KV 存储"""
        try:
            # 检查键是否已存在
            is_update = self.check_key_exists(key_name)
            operation = "Updating" if is_update else "Creating"
            print(f"{operation} CF KV for {key_name}...")
            
            # URL encode the key name for the API request
            encoded_key = urllib.parse.quote(key_name)
            
            # 构建存储数据
            kv_data = {
                key_name: base64.b64encode(content.encode()).decode(),
                "update_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "headers": headers or {}
            }
            
            response = requests.put(
                f"{self.base_url}/values/{encoded_key}",
                headers=self.headers,
                data=json.dumps(kv_data, ensure_ascii=False),
                timeout=30
            )
            
            if not response.ok:
                raise Exception(f"API request failed: {response.status_code} - {response.text}")
            
            print(f"Successfully {operation.lower()}d CF KV for {key_name}")
            return True
            
        except Exception as e:
            print(f"Error: {operation.lower()}ing CF KV for {key_name}: {str(e)}")
            return False


def get_original_headers(url, config_name=None):
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
                        # 使用config_name作为新的文件名（支持中文）config_name: CONVERT_PARAM中的键名
                        if config_name:
                            # URL编码config_name以支持中文
                            encoded_name = urllib.parse.quote(f"{config_name}")  # (f"T:{config_name}")添加T:前缀
                            headers[header] = f"attachment; filename*=UTF-8''{encoded_name}"
                        else:
                            # 如果没有提供config_name，保持原有的content-disposition
                            headers[header] = response.headers[header]
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
    

def mask_sensitive_url(url):
    """对敏感 URL 进行脱敏处理"""
    try:
        if not url:
            return ""
        # 解析 URL
        parsed = urllib.parse.urlparse(url)
        
        # 获取查询参数
        query_params = urllib.parse.parse_qs(parsed.query)
        
        # 处理 token 或其他敏感参数
        for sensitive_param in ['token', 'password', 'key', 'secret']:
            if sensitive_param in query_params:
                value = query_params[sensitive_param][0]
                if len(value) > 8:
                    query_params[sensitive_param] = [f"{value[:4]}...{value[-4:]}"]
        
        # 重建查询字符串
        masked_query = urllib.parse.urlencode(query_params, doseq=True)
        
        # 重建 URL，只显示域名和处理后的参数
        return f"{parsed.scheme}://{parsed.netloc}/...?{masked_query[:30]}..."
    except:
        return "masked_url"

def mask_params(params):
    """对参数进行脱敏处理"""
    try:
        if not params:
            return ""
        # 找到 url 参数的位置
        url_start = params.find("&url=")
        if url_start >= 0:
            # 保留 url= 之前的部分
            prefix = params[:url_start + 5]
            # 对 URL 部分进行处理
            remaining = params[url_start + 5:]
            url_end = remaining.find("&")
            if url_end >= 0:
                url_part = remaining[:url_end]
                after_url = remaining[url_end:]
            else:
                url_part = remaining
                after_url = ""
            
            # 解码并脱敏 URL
            decoded_url = urllib.parse.unquote(url_part)
            masked_url = mask_sensitive_url(decoded_url)
            
            # 返回处理后的参数字符串
            return f"{prefix}{urllib.parse.quote(masked_url)}{after_url[:30]}..."
        return f"{params[:30]}..."
    except:
        return "masked_params"


def extract_url_from_params(params):
    """从参数中提取订阅 URL"""
    try:
        print(f"Processing params: {mask_params(params)}")
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
            print(f"Decoded URL: {mask_sensitive_url(decoded_url)}")
            
            # 检查 URL 是否包含协议前缀
            if not decoded_url.startswith(('http://', 'https://')):
                decoded_url = 'https://' + decoded_url
            
            return decoded_url
    except Exception as e:
        print(f"Error extracting URL from params: {str(e)}")
    return None


def convert_subscribe(subscribe_dict):
    """转换订阅"""
    print("Start Subscription Conversion")
    base_url = "http://localhost:25500/sub"
    results = {}
    
    # 使用统一的 Clash 风格请求头
    headers = {
        'User-Agent': 'clash-verge/v1.0',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    }
    
    session = requests.Session()
    
    for filename, params in subscribe_dict.items():
        print(f"==============================\n")
        print(f"Converting {filename}...")

        # 从参数中提取原始订阅 URL
        original_url = extract_url_from_params(params)
        print(f"Extracted URL for {filename}: {mask_sensitive_url(original_url)}")
        
        if not original_url:
            print(f"Warning: Could not extract URL from params for {filename}")
            continue

        # 获取该订阅的响应头
        print(f"Fetching headers for {filename} from {mask_sensitive_url(original_url)}")
        sub_headers = get_original_headers(original_url, filename)
        
        if sub_headers:
            print(f"Successfully got headers for {filename}")
        else:
            print(f"Warning: No headers received for {filename}")

        # 转换配置
        url = f"{base_url}{params}"
        try:
            print(f"Converting configuration using URL: {mask_params(params)}")
            response = session.get(url, headers=headers, timeout=30)
            if response.ok:
                content = response.text
                update_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                content += f"\n\n# Updated on {update_time}\n"
                results[filename] = {
                    "content": content,
                    "headers": sub_headers
                }
            else:
                print(f"Error: converting {filename}: {response.status_code}")
        except Exception as e:
            print(f"Error: converting {filename}: {str(e)}")
    
    return results


def main():
    try:
        print("\n=== Start running converter_push.py ===")
        print(f"Current time (UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")

        # 检查环境变量
        required_vars = {
            "CF_ACCOUNT_ID": "CF Account ID",
            "CF_KV_ID": "CF KV ID",
            "CF_ACCOUNT_API_TOKEN": "CF Account API Token",
            "CONVERT_PARAM": "Convert Parame"
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
            raise Exception("Error: configuration conversion failed")

        # 初始化 Cloudflare KV 客户端
        cf_kv = CloudflareKV(
            os.environ["CF_ACCOUNT_ID"],
            os.environ["CF_KV_ID"],
            os.environ["CF_ACCOUNT_API_TOKEN"]
        )

        # 首先清理不再使用的配置
        print("\n=== Cleaning unused configurations ===")
        cf_kv.clean_unused_configs(set(results.keys()))

        # 更新每个配置到 KV，使用文件名作为 key
        success_count = 0
        for filename, data in results.items():
            if cf_kv.update_config(filename, data["content"], data["headers"]):
                success_count += 1
            else:
                print(f"Failed to update {filename} to CF KV")

        
        # 将 CONVERT_PARAM 也推送到 KV 中。  方便接着修改该介意去掉（update_config执行的时候会encode一次）
        print("\n=== Storing CONVERT_PARAM to KV ===")
        if cf_kv.update_config("CONVERT_PARAM", os.environ['CONVERT_PARAM'], {}):
            print("Successfully stored CONVERT_PARAM to KV")
        else:
            print("Failed to store CONVERT_PARAM to KV")

        
        if success_count == 0:
            raise Exception("Error: the configuration update to kv failed")
        else:
            print(f"\n=== Successfully updated {success_count} configurations to KV ===")

    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
