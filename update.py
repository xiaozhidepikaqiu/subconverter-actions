import requests
import os
import json
import base64
from datetime import datetime, timedelta


def fetch_subscription_userinfo(subscribe_url):
    """
    Fetch subscription-userinfo header from the subscription URL.
    """
    try:
        # 使用 HEAD 请求获取 Headers，包括 subscription-userinfo
        response = requests.head(subscribe_url)
        if response.status_code == 200:
            # 提取 subscription-userinfo Header
            userinfo = response.headers.get("subscription-userinfo", "")
            userinfo = userinfo.strip(";")  # 去除多余的分号
            return userinfo
        else:
            print(f"Failed to fetch subscription-userinfo, status code: {response.status_code}")
            return ""
    except Exception as e:
        print(f"Error fetching subscription-userinfo: {e}")
        return ""


def parse_subscription_userinfo(userinfo):
    """
    Parse the subscription-userinfo string into individual components.
    Example: "upload=123456789; download=987654321; total=10737418240; expire=1689897600"
    """
    try:
        userinfo_data = {}
        for item in userinfo.split(";"):
            if "=" in item:
                key, value = item.split("=")
                userinfo_data[key.strip()] = value.strip()

        # 将字节值转换为 GB，并解析到期时间
        upload = int(userinfo_data.get("upload", 0)) / (1024 ** 3)  # 转为 GB
        download = int(userinfo_data.get("download", 0)) / (1024 ** 3)
        total = int(userinfo_data.get("total", 0)) / (1024 ** 3)
        expire_timestamp = int(userinfo_data.get("expire", 0))
        expire_date = (
            datetime.utcfromtimestamp(expire_timestamp).strftime("%Y-%m-%d %H:%M:%S")
            if expire_timestamp > 0
            else "unknown"
        )

        return round(upload, 2), round(download, 2), round(total, 2), expire_date
    except Exception as e:
        print(f"Error parsing subscription-userinfo: {e}")
        return 0, 0, 0, "unknown"


def convert_subscribe(subscribe_dict):
    """
    Convert subscription links and add subscription-userinfo to the YAML file.
    """
    filecontent_dict = {}
    for filename, subscribe_url in subscribe_dict.items():
        # 获取订阅内容
        try:
            response = requests.get(subscribe_url)
            raw_content = response.text
        except Exception as e:
            print(f"Error fetching subscription content from {subscribe_url}: {e}")
            continue

        # 获取 subscription-userinfo 信息
        userinfo = fetch_subscription_userinfo(subscribe_url)
        if userinfo:
            # 解析 subscription-userinfo
            upload, download, total, expire_date = parse_subscription_userinfo(userinfo)
            header = (
                f"# subscription-userinfo: Upload={upload}GB; Download={download}GB; Total={total}GB; Expire={expire_date}\n"
            )
        else:
            header = "# subscription-userinfo: unavailable\n"

        # 构造最终的 YAML 内容
        filecontent_dict[filename] = (
            f"#!MANAGED-CONFIG {subscribe_url} interval=43200\n"
            f"{header}\n"
            f"{raw_content}\n\n"
            f"# Updated on {(datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        print(f"Generated content for {filename}:\n{filecontent_dict[filename]}")
    return filecontent_dict


def update_gist(gist_id, filecontent_dict):
    """
    Update the Gist with the generated content.
    """
    github_token = os.getenv("PERSONAL_TOKEN")
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }
    url = f"https://api.github.com/gists/{gist_id}"
    data = {
        "files": {filename: {"content": content} for filename, content in filecontent_dict.items()}
    }

    response = requests.patch(url, headers=headers, json=data)
    if response.status_code == 200:
        print("Gist updated successfully.")
    else:
        print(f"Failed to update Gist. Status code: {response.status_code}, response: {response.text}")


if __name__ == "__main__":
    try:
        # 从环境变量中获取订阅参数
        subscribe_dict = json.loads(base64.b64decode(os.environ["CONVERT_PARAM"]).decode("utf-8"))
    except Exception as e:
        print(f"Error decoding CONVERT_PARAM: {e}")
        exit(1)

    # 环境变量中获取 GitHub Token 和 Gist ID
    g_github_token = os.getenv("PERSONAL_TOKEN")
    g_gist_id = os.getenv("GIST_ID")

    # 转换订阅并生成内容
    filecontent_dict = convert_subscribe(subscribe_dict)

    # 上传到 Gist
    if g_github_token and g_gist_id:
        update_gist(g_gist_id, filecontent_dict)
    else:
        print("Missing GitHub token or Gist ID.")
