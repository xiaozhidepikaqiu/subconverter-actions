import os
import sys
import json
import base64
import requests
import urllib.parse
from datetime import datetime, timedelta

def get_browser_headers():
    """返回模拟浏览器的请求头"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not_A Brand";v="8"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'DNT': '1'
    }

class CloudflareKV:
    def __init__(self, account_id, kv_id, account_api_token):
        self.account_id = account_id
        self.kv_id = kv_id
        self.account_api_token = account_api_token
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/{kv_id}/values"
        self.headers = {
            "Authorization": f"Bearer {account_api_token}",
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
        """更新 CF KV 存储"""
        try:
            is_update = self.check_key_exists(key_name)
            operation = "Updating" if is_update else "Creating"
            print(f"{operation} CF KV for {key_name}...")
            
            kv_data = {
                key_name: base64.b64encode(content.encode()).decode(),
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
            
            print(f"Successfully {operation.lower()}d CF KV for {key_name}")
            return True
            
        except Exception as e:
            print(f"Error: {operation.lower()}ing CF KV for {key_name}: {str(e)}")
            return False

def get_original_headers(url):
    """获取原始订阅的响应头"""
    try:
        session = requests.Session()
        headers = get_browser_headers()
        
        # 第一次请求，可能会触发 Cloudflare 检查
        response = session.get(url, headers=headers, timeout=30)
        if response.status_code == 403:
            # 如果被 Cloudflare 拦截，等待一下再试
            print("First attempt blocked, retrying...")
            import time
            time.sleep(3)
            response = session.get(url, headers=headers, timeout=30)
        
        if response.ok:
            headers = {}
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
                        content_disp = response.headers[header]
                        if 'filename' in content_disp:
                            if 'filename*=' in content_disp:
                                parts = content_disp.split("''")
                                if len(parts) > 1:
                                    encoding_part = parts[0]
                                    filename_part = parts[1]
                                    new_filename = f"T:{filename_part}"
                                    headers[header] = f"{encoding_part}''{new_filename}"
                            else:
                                filename_start = content_disp.find('filename=') + 9
                                filename = content_disp[filename_start:]
                                if filename.startswith('"'):
                                    filename = filename[1:-1]
                                new_filename = f"T:{filename}"
                                headers[header] = f"attachment;filename={new_filename}"
                    else:
                        headers[header] = response.headers[header]
            
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
    print("Start Subscription Conversion")
    base_url = "http://localhost:25500/sub"
    results = {}
    
    session = requests.Session()
    headers = get_browser_headers()
    
    for filename, params in subscribe_dict.items():
        print(f"Converting {filename}...")
        
        original_url = extract_url_from_params(params)
        print(f"Extracted URL for {filename}: {mask_sensitive_url(original_url)}")
        
        if not original_url:
            print(f"Warning: Could not extract URL from params for {filename}")
            continue
            
        print(f"Fetching headers for {filename} from {mask_sensitive_url(original_url)}")
        sub_headers = get_original_headers(original_url)
        
        if sub_headers:
            print(f"Successfully got headers for {filename}")
        else:
            print(f"Warning: No headers received for {filename}")
        
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

# 保持其他函数不变
def mask_sensitive_url(url):
    """对敏感 URL 进行脱敏处理"""
    try:
        if not url:
            return ""
        parsed = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed.query)
        for sensitive_param in ['token', 'password', 'key', 'secret']:
            if sensitive_param in query_params:
                value = query_params[sensitive_param][0]
                if len(value) > 8:
                    query_params[sensitive_param] = [f"{value[:4]}...{value[-4:]}"]
        masked_query = urllib.parse.urlencode(query_params, doseq=True)
        return f"{parsed.scheme}://{parsed.netloc}/...?{masked_query[:30]}..."
    except:
        return "masked_url"

def mask_params(params):
    """对参数进行脱敏处理"""
    try:
        if not params:
            return ""
        url_start = params.find("&url=")
        if url_start >= 0:
            prefix = params[:url_start + 5]
            remaining = params[url_start + 5:]
            url_end = remaining.find("&")
            if url_end >= 0:
                url_part = remaining[:url_end]
                after_url = remaining[url_end:]
            else:
                url_part = remaining
                after_url = ""
            decoded_url = urllib.parse.unquote(url_part)
            masked_url = mask_sensitive_url(decoded_url)
            return f"{prefix}{urllib.parse.quote(masked_url)}{after_url[:30]}..."
        return f"{params[:30]}..."
    except:
        return "masked_params"

def extract_url_from_params(params):
    """从参数中提取订阅 URL"""
    try:
        print(f"Processing params: {mask_params(params)}")
        start = params.find("&url=") + 5
        if start > 4:
            end = params.find("&", start)
            if end == -1:
                url = params[start:]
            else:
                url = params[start:end]
            decoded_url = urllib.parse.unquote(url)
            print(f"Decoded URL: {mask_sensitive_url(decoded_url)}")
            if not decoded_url.startswith(('http://', 'https://')):
                decoded_url = 'https://' + decoded_url
            return decoded_url
    except Exception as e:
        print(f"Error extracting URL from params: {str(e)}")
    return None

def main():
    try:
        print("\n=== Start running converter_push.py ===")
        print(f"Current time (UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")

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

        try:
            subscribe_dict = json.loads(base64.b64decode(os.environ['CONVERT_PARAM']).decode("utf-8"))
        except Exception as e:
            raise Exception(f"Failed to decode CONVERT_PARAM: {str(e)}")

        results = convert_subscribe(subscribe_dict)
        if not results:
            raise Exception("Error: configuration conversion failed")

        cf_kv = CloudflareKV(
            os.environ["CF_ACCOUNT_ID"],
            os.environ["CF_KV_ID"],
            os.environ["CF_ACCOUNT_API_TOKEN"]
        )

        success_count = 0
        for filename, data in results.items():
            if cf_kv.update_config(filename, data["content"], data["headers"]):
                success_count += 1
            else:
                print(f"Failed to update {filename} to CF KV")

        if success_count == 0:
            raise Exception("Error: the configuration update to kv failed")
        else:
            print(f"\n=== Successfully updated {success_count} configurations to KV ===")

    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
