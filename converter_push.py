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
            # 对键名进行 URL 编码以支持中文
            encoded_key_name = urllib.parse.quote(key_name)
            response = requests.get(
                f"{self.base_url}/{encoded_key_name}",
                headers=self.headers,
                timeout=30
            )
            return response.status_code == 200
        except:
            return False

    
    def update_config(self, key_name, content, headers=None):
        """更新 CF KV 存储"""
        try:
            # 对键名进行 URL 编码以支持中文
            encoded_key_name = urllib.parse.quote(key_name)
            
            # 检查键是否已存在
            is_update = self.check_key_exists(encoded_key_name)
            operation = "Updating" if is_update else "Creating"
            print(f"{operation} CF KV for {key_name}...")
            
            # 构建存储数据，使用文件名作为配置键
            kv_data = {
                key_name: base64.b64encode(content.encode()).decode(),  # 使用原始文件名作为键
                "update_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "headers": headers or {}
            }
            
            response = requests.put(
                f"{self.base_url}/{encoded_key_name}",  # 使用编码后的键名在 URL 中
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


def convert_subscribe(subscribe_dict):
    """转换订阅"""
    print("\n=== Detailed Subscription Conversion Process ===")
    print(f"Subscriptions to process: {len(subscribe_dict)}")
    print("=" * 60)
    
    base_url = "http://localhost:25500/sub"
    results = {}
    
    for idx, (filename, params) in enumerate(subscribe_dict.items(), 1):
        print(f"\n[{idx}/{len(subscribe_dict)}] Processing: {filename}")
        print("-" * 60)
        
        try:
            # 1. 详细的参数信息
            print("\n[Parameters]")
            print(f"Raw params: {params[:100]}...")
            decoded_params = urllib.parse.unquote(params)
            print(f"Decoded params: {decoded_params[:100]}...")
            
            # 2. URL提取
            print("\n[URL Extraction]")
            original_url = extract_url_from_params(params)
            if original_url:
                print(f"✓ URL extracted successfully")
                print(f"- Masked URL: {mask_sensitive_url(original_url)}")
                print(f"- URL length: {len(original_url)}")
            else:
                print("✗ Failed to extract URL")
                continue
            
            # 3. 获取原始订阅头信息
            print("\n[Original Subscription Headers]")
            sub_headers = get_original_headers(original_url)
            if sub_headers:
                print("✓ Headers retrieved successfully:")
                for key, value in sub_headers.items():
                    print(f"- {key}: {value}")
            else:
                print("⚠ No headers received")
            
            # 4. 转换配置
            print("\n[Configuration Conversion]")
            url = f"{base_url}{params}"
            try:
                print("Making request to subconverter:")
                print(f"- Base URL: {base_url}")
                print(f"- Params length: {len(params)}")
                print(f"- Full URL length: {len(url)}")
                
                # 添加请求头信息
                headers = {
                    'User-Agent': 'clash-verge/v1.0',
                    'Accept': '*/*',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive'
                }
                
                print("\nRequest Headers:")
                for key, value in headers.items():
                    print(f"- {key}: {value}")
                
                response = requests.get(url, headers=headers, timeout=30)
                
                print("\nResponse Details:")
                print(f"- Status Code: {response.status_code}")
                print(f"- Response Headers:")
                for key, value in response.headers.items():
                    print(f"  {key}: {value}")
                
                if not response.ok:
                    print("\n⚠ Error Response Content:")
                    print("-" * 40)
                    print(response.text)
                    print("-" * 40)
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
                
                content = response.text
                if not content:
                    raise Exception("Empty response content")
                
                print("\nResponse Content Preview:")
                print("-" * 40)
                print(f"Content length: {len(content)}")
                print(f"First 100 chars: {content[:100]}...")
                print("-" * 40)
                
                # 添加更新信息
                content += f"\n\n# Updated on {current_time}\n"
                content += f"# Updated by {current_user}\n"
                
                results[filename] = {
                    "content": content,
                    "headers": sub_headers
                }
                print(f"\n✓ Successfully processed {filename}")
                
            except requests.exceptions.RequestException as e:
                print(f"\n⚠ Network Error:")
                print(f"Type: {type(e).__name__}")
                print(f"Message: {str(e)}")
                print(f"URL: {mask_sensitive_url(url)}")
                raise
                
            except Exception as e:
                print(f"\n⚠ Processing Error:")
                print(f"Type: {type(e).__name__}")
                print(f"Message: {str(e)}")
                import traceback
                print("Traceback:")
                print(traceback.format_exc())
                raise
                
        except Exception as e:
            print(f"\n✗ Failed to process {filename}")
            print(f"Error: {str(e)}")
        
        print("\n" + "=" * 60)
    
    # 处理摘要
    print("\n=== Conversion Summary ===")
    print(f"Total subscriptions processed: {len(subscribe_dict)}")
    print(f"Successful conversions: {len(results)}")
    print(f"Failed conversions: {len(subscribe_dict) - len(results)}")
    if len(results) < len(subscribe_dict):
        print("\nFailed subscriptions:")
        for name in subscribe_dict.keys():
            if name not in results:
                print(f"- {name}")
    print("=" * 60 + "\n")
    
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
