import requests
import os
import json
import base64
from datetime import datetime
import time
from urllib.parse import unquote, urlparse


def validate_and_fix_url(subscribe_url):
    """
    验证并修正订阅 URL 的格式
    """
    if not subscribe_url.startswith("http://") and not subscribe_url.startswith("https://"):
        subscribe_url = "https://" + subscribe_url

    # 解码嵌套的 URL 参数
    subscribe_url = unquote(subscribe_url)

    # 检查 URL 是否包含有效的主机名
    parsed_url = urlparse(subscribe_url)
    if not parsed_url.netloc:
        raise ValueError(f"Invalid URL: {subscribe_url}")

    return subscribe_url


def fetch_subscription_userinfo(subscribe_url):
    """
    Fetch subscription-userinfo header from the subscription URL.
    """
    try:
        subscribe_url = validate_and_fix_url(subscribe_url)
        headers = {
            'User-Agent': 'Clash/1.0.0',
            'Accept': 'application/json',
            'Cache-Control': 'no-cache'
        }
        response = requests.get(subscribe_url, headers=headers, allow_redirects=True)
        print(f"Response headers: {dict(response.headers)}")
        
        userinfo = response.headers.get('subscription-userinfo', '')
        if userinfo:
            print(f"Found userinfo: {userinfo}")
            return userinfo
        else:
            print("No subscription-userinfo found in headers.")
        
        return ""
        
    except Exception as e:
        print(f"Error fetching userinfo: {e}")
        return ""


def convert_subscribe(subscribe_dict):
    """
    Convert subscription links and add subscription-userinfo to the YAML file.
    """
    filecontent_dict = {}
    for filename, subscribe_url in subscribe_dict.items():
        try:
            print(f"Processing {filename} with URL: {subscribe_url}")
            
            # 验证并修正订阅 URL
            subscribe_url = validate_and_fix_url(subscribe_url)
            print(f"Validated URL: {subscribe_url}")
            
            # 获取订阅信息
            userinfo = fetch_subscription_userinfo(subscribe_url)
            print(f"Original userinfo: {userinfo}")
            
            # 调用 subconverter
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
                'include': userinfo,
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
                
                # 添加 userinfo 到配置文件
                if userinfo:
                    header = f"# subscription-userinfo: {userinfo}\n"
                else:
                    header = "# No subscription info available\n"
                
                filecontent_dict[filename] = (
                    f"#!MANAGED-CONFIG {subscribe_url} interval=43200\n"
                    f"{header}\n"
                    f"{converted_content}\n"
                    f"# Updated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
            else:
                print(f"Conversion failed with status code: {response.status_code}")
                print(f"Response: {response.text}")
                
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
