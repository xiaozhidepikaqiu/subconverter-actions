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
            # 检查键是否已存在
            is_update = self.check_key_exists(key_name)
            operation = "Updating" if is_update else "Creating"
            print(f"{operation} CF KV for {key_name}...")
            
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
            
            print(f"Successfully {operation.lower()}d CF KV for {key_name}")
            return True
            
        except Exception as e:
            print(f"Error: {operation.lower()}ing CF KV for {key_name}: {str(e)}")
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
            
            # 检查 URL 是否包含协议前缀
            if not decoded_url.startswith(('http://', 'https://')):
                decoded_url = 'https://' + decoded_url
            
            return decoded_url
    except Exception as e:
        print(f"Error extracting URL from params: {str(e)}")
    return None


def check_subscription_content(url):
    """检查订阅内容"""
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
            content = response.text
            print(f"\nSubscription Content Analysis:")
            print(f"Status Code: {response.status_code}")
            print(f"Content Length: {len(content)}")
            print(f"Content Type: {response.headers.get('content-type', 'Not specified')}")
            
            # 尝试检测内容格式
            if content.startswith('mixed-port:') or 'proxies:' in content[:1000]:
                print("Format: Appears to be Clash configuration")
            elif content.startswith('vmess://') or content.startswith('ss://'):
                print("Format: Base64 encoded links")
            else:
                print("Format: Unknown")
            
            # 查找关键部分
            print("\nKey sections found:")
            if 'proxies:' in content:
                proxy_index = content.find('proxies:')
                print(f"Found 'proxies:' section at position {proxy_index}")
                # 显示proxies部分的前300个字符
                print("Proxies section preview:")
                section = content[proxy_index:proxy_index+300]
                print(section.replace('\n', '\n  '))
            else:
                print("No 'proxies:' section found")
            
            return content
    except Exception as e:
        print(f"Error checking subscription: {str(e)}")
        return None

def convert_subscribe(subscribe_dict):
    """转换订阅"""
    print("Start Subscription Conversion")
    base_url = "http://localhost:25500/sub"
    results = {}
    
    for filename, params in subscribe_dict.items():
        print(f"\n=== Processing {filename} ===")
        
        try:
            # 1. 提取并验证原始订阅URL
            original_url = extract_url_from_params(params)
            print(f"1. Original URL: {original_url}")
            
            if not original_url:
                print("Error: Failed to extract URL")
                continue
            
            # 2. 检查原始订阅内容
            print("\n2. Analyzing original subscription...")
            content = check_subscription_content(original_url)
            if not content:
                print("Error: Failed to get subscription content")
                continue
            
            # 3. 获取订阅头信息
            print("\n3. Fetching subscription headers...")
            sub_headers = get_original_headers(original_url)
            
            # 4. 转换配置
            print("\n4. Converting configuration...")
            url = f"{base_url}{params}"
            try:
                print("Making request to subconverter...")
                print(f"Full URL: {url}")
                
                response = requests.get(url, timeout=30)
                print(f"Response status: {response.status_code}")
                
                if response.ok:
                    content = response.text
                    if not content:
                        raise Exception("Empty response from subconverter")
                    
                    update_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                    content += f"\n\n# Updated on {update_time}\n"
                    results[filename] = {
                        "content": content,
                        "headers": sub_headers
                    }
                    print(f"Successfully converted {filename}")
                else:
                    print(f"Conversion failed with status {response.status_code}")
                    print(f"Error response: {response.text}")
                    # 尝试直接发送原始内容给subconverter
                    print("\nTrying direct conversion...")
                    encoded_content = base64.b64encode(content.encode()).decode()
                    alt_params = f"?target=clash&content={encoded_content}&config=https://raw.githubusercontent.com/xiaozhidepikaqiu/MySubconverterRemoteConfig/refs/heads/main/MyRemoteConfig.ini"
                    alt_url = f"{base_url}{alt_params}"
                    alt_response = requests.get(alt_url, timeout=30)
                    print(f"Direct conversion status: {alt_response.status_code}")
                    if alt_response.ok:
                        print("Direct conversion succeeded!")
                        content = alt_response.text
                        results[filename] = {
                            "content": content,
                            "headers": sub_headers
                        }
            except Exception as e:
                print(f"Error during conversion: {str(e)}")
                
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
    
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

        # 更新每个配置到 KV，使用文件名作为 key
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
