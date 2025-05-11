import requests
import os
import json
import base64
from datetime import datetime, timedelta
import time

def fetch_subscription_userinfo(subscribe_url):
    """
    使用多种方式尝试获取订阅信息
    """
    try:
        # 使用不同的 User-Agent 尝试
        headers_list = [
            {'User-Agent': 'Clash/1.0.0'},
            {'User-Agent': 'ClashforWindows/0.20.39'},
            {'User-Agent': 'Stash/2.0.0'},
            {}  # 空 headers 作为后备
        ]
        
        for headers in headers_list:
            response = requests.get(subscribe_url, headers=headers, allow_redirects=True)
            print(f"Trying with headers: {headers}")
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            # 检查所有可能的 header 名称
            userinfo = (
                response.headers.get('subscription-userinfo') or
                response.headers.get('Subscription-Userinfo') or
                response.headers.get('SUBSCRIPTION-USERINFO') or
                response.headers.get('User-info') or
                response.headers.get('Flow-Info') or
                ''
            )
            
            if userinfo:
                print(f"Found userinfo in headers: {userinfo}")
                return userinfo
            
            # 如果在 headers 中没找到，尝试解析响应内容
            try:
                content = response.text
                if '剩余流量' in content or '总流量' in content:
                    import re
                    # 尝试多个正则表达式匹配
                    patterns = [
                        r'剩余流量：(.*?)\|总流量：(.*?)(?:\||$)',
                        r'总流量：(.*?)\|已使用：(.*?)(?:\||$)',
                        r'流量：(.*?) \| 剩余：(.*?)(?:\||$)'
                    ]
                    
                    for pattern in patterns:
                        matches = re.search(pattern, content)
                        if matches:
                            print(f"Found userinfo in content using pattern: {pattern}")
                            # 转换为标准格式
                            return f"upload=0;download=0;total={matches.group(2)};expire=0"
            except Exception as e:
                print(f"Error parsing content: {e}")
                
            # 如果这个 User-Agent 没有成功，继续尝试下一个
            time.sleep(1)  # 添加短暂延迟，避免请求过快
            
        print("No subscription info found in all attempts")
        return ""
        
    except Exception as e:
        print(f"Error in fetch_subscription_userinfo: {e}")
        return ""

def convert_subscribe(subscribe_dict):
    """
    转换订阅并保留流量信息
    """
    filecontent_dict = {}
    for filename, subscribe_url in subscribe_dict.items():
        try:
            print(f"Processing {filename} with URL: {subscribe_url}")
            
            # 1. 首先获取原始订阅信息
            userinfo = fetch_subscription_userinfo(subscribe_url)
            print(f"Original userinfo: {userinfo}")
            
            # 2. 使用 subconverter 进行转换
            base_url = "http://127.0.0.1:25500/sub"
            params = {
                'target': 'clash',
                'url': subscribe_url,
                'insert': 'false',
                'config': 'https://raw.githubusercontent.com/xiaozhidepikaqiu/MySubconverterRemoteConfig/refs/heads/main/clash_rule_base.yaml',
                'append_type': 'true',
                'emoji': 'true',
                'list': 'false',
                'sort': 'false',
                'include': userinfo,  # 包含获取到的用户信息
                'append_info': 'true',
                'expand': 'true',
                'classic': 'true',
                'udp': 'true',
                'scv': 'false',
                'fdn': 'true'
            }
            
            print(f"Calling subconverter with params: {params}")
            response = requests.get(base_url, params=params)
            
            if response.status_code == 200:
                converted_content = response.text
                print("Conversion successful")
                
                # 确保 userinfo 被添加到配置文件的开头
                if userinfo:
                    # 构造配置文件，确保 userinfo 在最前面
                    config_content = (
                        f"#!MANAGED-CONFIG {subscribe_url} interval=43200\n"
                        f"#subscription-userinfo: {userinfo}\n"
                        f"#update-interval: 43200\n"
                        f"#support-url: {subscribe_url}\n"
                        f"#profile-web-page-url: {subscribe_url}\n"
                        f"{converted_content}\n"
                        f"#update-time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    )
                else:
                    config_content = converted_content
                
                filecontent_dict[filename] = config_content
                print(f"Generated content for {filename} with headers")
                
                # 打印生成的内容的前几行，用于调试
                print("First few lines of generated content:")
                print("\n".join(config_content.split("\n")[:10]))
                
            else:
                print(f"Conversion failed with status code: {response.status_code}")
                print(f"Response: {response.text}")
                continue
                
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
            
    return filecontent_dict

def update_gist(gist_id, filecontent_dict):
    """
    更新 Gist 内容
    """
    github_token = os.getenv("PERSONAL_TOKEN")
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }
    url = f"https://api.github.com/gists/{gist_id}"
    
    # 添加文件更新时间戳
    for filename, content in filecontent_dict.items():
        if not content.startswith("#!MANAGED-CONFIG"):
            filecontent_dict[filename] = (
                f"#!MANAGED-CONFIG\n"
                f"#Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"{content}"
            )
    
    data = {
        "files": {filename: {"content": content} for filename, content in filecontent_dict.items()}
    }
    
    response = requests.patch(url, headers=headers, json=data)
    if response.status_code == 200:
        print("Gist updated successfully")
    else:
        print(f"Failed to update Gist. Status code: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    try:
        # 从环境变量中获取订阅参数
        subscribe_dict = json.loads(base64.b64decode(os.environ["CONVERT_PARAM"]).decode("utf-8"))
        print("Decoded CONVERT_PARAM successfully")
        
        # 等待 subconverter 服务完全启动
        print("Waiting for subconverter to start...")
        time.sleep(10)
        
        # 转换订阅并生成内容
        filecontent_dict = convert_subscribe(subscribe_dict)
        
        # 检查是否成功生成了内容
        if not filecontent_dict:
            print("No content was generated!")
            exit(1)
            
        # 更新到 Gist
        gist_id = os.getenv("GIST_ID")
        if gist_id:
            update_gist(gist_id, filecontent_dict)
        else:
            print("Missing Gist ID")
            
    except Exception as e:
        print(f"Error in main: {e}")
        exit(1)
