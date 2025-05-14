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


def get_subscription_content(url, proxies=None):
    """获取订阅内容并解码"""
    try:
        headers = get_subscription_headers()
        response = requests.get(
            url, 
            headers=headers, 
            timeout=30,
            proxies=proxies,
            verify=False if proxies else True
        )
        
        if response.ok:
            content = response.text.strip()
            try:
                # 尝试 base64 解码
                decoded_content = base64.b64decode(content).decode('utf-8')
                return decoded_content
            except:
                # 如果解码失败，返回原始内容
                return content
        else:
            print(f"Error getting subscription content: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error in get_subscription_content: {str(e)}")
        return None


def convert_subscribe(subscribe_dict):
    """转换订阅"""
    print("Start Subscription Conversion")
    base_url = "http://localhost:25500/sub"
    results = {}
    
    # 初始化代理列表
    proxy_list = []
    
    # 首先尝试从成功的订阅获取代理
    for filename, params in subscribe_dict.items():
        original_url = extract_url_from_params(params)
        if not original_url:
            continue
            
        content = get_subscription_content(original_url)
        if content and ('vmess://' in content or 'trojan://' in content or 'ss://' in content):
            print(f"Attempting to extract proxies from {filename}")
            for line in content.splitlines():
                line = line.strip()
                try:
                    if line.startswith('vmess://'):
                        config = json.loads(base64.b64decode(line[8:]).decode('utf-8'))
                        proxy = f"socks5://{config['add']}:{config['port']}"
                        if proxy not in proxy_list:
                            proxy_list.append(proxy)
                            print(f"Added proxy from {filename}")
                    elif line.startswith(('trojan://', 'ss://')):
                        server = line.split('@')[1].split('?')[0].split('#')[0]
                        proxy = f"socks5://{server}"
                        if proxy not in proxy_list:
                            proxy_list.append(proxy)
                            print(f"Added proxy from {filename}")
                except Exception as e:
                    continue

    # 现在处理每个订阅
    for filename, params in subscribe_dict.items():
        print(f"\nConverting {filename}...")
        
        original_url = extract_url_from_params(params)
        print(f"Extracted URL for {filename}: {mask_sensitive_url(original_url)}")
        
        if not original_url:
            print(f"Warning: Could not extract URL from params for {filename}")
            continue
            
        print(f"Fetching headers for {filename} from {mask_sensitive_url(original_url)}")
        
        # 获取订阅内容
        sub_content = None
        sub_headers = None
        
        # 首先尝试直接连接
        print("Attempting direct connection...")
        sub_headers = get_original_headers(original_url)
        sub_content = get_subscription_content(original_url)
        
        # 如果直接连接失败，尝试使用代理
        if not sub_content and proxy_list:
            print("Direct connection failed, trying proxies...")
            for proxy in proxy_list:
                try:
                    proxies = {
                        'http': proxy,
                        'https': proxy
                    }
                    print(f"Trying proxy: {proxy}")
                    sub_headers = get_original_headers(original_url, proxies)
                    sub_content = get_subscription_content(original_url, proxies)
                    if sub_content:
                        print(f"Successfully got content using proxy {proxy}")
                        break
                except Exception as e:
                    print(f"Proxy {proxy} failed: {str(e)}")
                    continue
        
        if not sub_content:
            print(f"Failed to get subscription content for {filename}")
            continue
            
        # 转换配置
        url = f"{base_url}{params}"
        try:
            print(f"Converting configuration using URL: {mask_params(params)}")
            
            # 尝试使用代理进行转换
            response = None
            if proxy_list:
                for proxy in proxy_list:
                    try:
                        proxies = {
                            'http': proxy,
                            'https': proxy
                        }
                        print(f"Trying conversion with proxy: {proxy}")
                        response = requests.get(url, timeout=30, proxies=proxies, verify=False)
                        if response.ok and 'proxies:' in response.text:
                            print(f"Conversion successful with proxy {proxy}")
                            break
                        else:
                            print(f"Invalid response with proxy {proxy}")
                    except Exception as e:
                        print(f"Conversion failed with proxy {proxy}: {str(e)}")
                        continue
            
            # 如果代理都失败了，尝试直接连接
            if not response or not response.ok:
                print("Trying direct connection for conversion...")
                response = requests.get(url, timeout=30)
            
            if response.ok:
                content = response.text
                if 'proxies:' in content:
                    update_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                    content += f"\n\n# Updated on {update_time}\n"
                    results[filename] = {
                        "content": content,
                        "headers": sub_headers
                    }
                    print(f"Successfully converted {filename}")
                else:
                    print(f"Error: Invalid configuration format for {filename}")
                    print(f"Response preview: {content[:200]}")
            else:
                print(f"Error: converting {filename}: {response.status_code}")
                if response.text:
                    print(f"Error details: {response.text[:200]}")
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
