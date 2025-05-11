import requests
import sys
import json
import base64
import os
from urllib.parse import quote, unquote, urlparse, parse_qs
from datetime import datetime, timedelta

g_github_token = ""  # GitHub Token
g_gist_id = ""  # Gist ID


def extract_original_url(subscribe_url):
    """
    从订阅链接中提取原始的订阅 URL，并进行解码
    """
    try:
        # 解析 URL 中的参数
        parsed_url = urlparse(subscribe_url)
        query_params = parse_qs(parsed_url.query)

        # 提取 `url` 参数并解码
        encoded_url = query_params.get("url", [""])[0]
        original_url = unquote(encoded_url)

        print(f"Extracted original URL: {original_url}")
        return original_url
    except Exception as e:
        print(f"Error extracting original URL: {e}")
        return None


def fetch_subscription_userinfo(subscribe_url):
    """
    获取订阅链接的流量信息
    """
    # 提取并解码原始订阅链接
    original_url = extract_original_url(subscribe_url)
    if not original_url:
        return "Error extracting subscription URL."

    headers = {
        "User-Agent": "Clash/1.0.0",
        "Accept": "application/json",
        "Cache-Control": "no-cache",
    }
    try:
        response = requests.get(original_url, headers=headers, timeout=10)
        if response.status_code == 200:
            userinfo = response.headers.get("subscription-userinfo", "")
            if userinfo:
                print(f"Subscription userinfo: {userinfo}")
                return userinfo
            else:
                print("No subscription-userinfo found in response headers.")
                return "No subscription-userinfo available."
        else:
            print(f"Failed to fetch userinfo. Status code: {response.status_code}")
            return "Failed to fetch subscription-userinfo."
    except Exception as e:
        print(f"Error fetching subscription userinfo: {e}")
        return "Error fetching subscription-userinfo."


def update_gist(gist_id, filecontent_dict):
    """
    更新 Gist
    """
    global g_github_token
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {g_github_token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    url = f"https://api.github.com/gists/{gist_id}"
    data = {
        "description": "subconverter-actions",
        "files": {}
    }
    for gist_filename, gist_content in filecontent_dict.items():
        if gist_content is None:
            # 删除文件
            data["files"][gist_filename] = None
        else:
            data["files"][gist_filename] = {"content": gist_content}

    response = requests.patch(url, headers=headers, json=data)
    print(f"update_gist response: {response.status_code}")
    if response.status_code != 200:
        print(f"Error updating Gist: {response.text}")
    else:
        print("Gist updated successfully.")


def convert_subscribe(subscribe_dict):
    """
    调用 subconverter 服务转换订阅链接，并获取流量信息
    """
    base_url = "http://localhost:25500/sub"
    filecontent_dict = {}
    for filename, params in subscribe_dict.items():
        try:
            # 拼接完整的 URL
            full_url = f"{base_url}{params}"
            print(f"Processing {filename} with URL: {full_url}")

            # 获取流量信息
            userinfo = fetch_subscription_userinfo(full_url)

            # 发起转换请求
            response = requests.get(full_url, timeout=30)  # 增加超时时间
            if response.status_code == 200:
                # 添加流量信息和更新时间戳到文件内容
                filecontent_dict[filename] = (
                    f"# Subscription userinfo: {userinfo}\n"
                    f"{response.text}\n"
                    f"# Updated on {(datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                print(f"Successfully processed {filename}.")
            else:
                print(f"Failed to process {filename}. Status code: {response.status_code}, Response: {response.text}")
        except requests.exceptions.Timeout:
            print(f"Timeout occurred while processing {filename}. Consider increasing the timeout.")
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    print(f"Generated file content: {filecontent_dict}")
    return filecontent_dict


if __name__ == "__main__":

    try:
        # 解码订阅参数
        subscribe_dict = json.loads(base64.b64decode(os.environ['CONVERT_PARAM']).decode("utf-8"))
        print(f"Decoded CONVERT_PARAM: {subscribe_dict}")
    except Exception as e:
        print(f"Failed to decode CONVERT_PARAM: {e}")
        sys.exit(1)

    g_github_token = os.environ.get('PERSONAL_TOKEN', '')
    g_gist_id = os.environ.get('GIST_ID', '')

    if not g_github_token or not g_gist_id:
        print("GitHub token or Gist ID is missing. Skipping Gist update.")
        sys.exit(1)

    # 转换订阅链接并获取流量信息
    filecontent_dict = convert_subscribe(subscribe_dict)

    if not filecontent_dict:
        print("No content generated. Skipping Gist update.")
        sys.exit(1)

    # 更新到 Gist
    update_gist(gist_id=g_gist_id, filecontent_dict=filecontent_dict)
