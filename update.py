import requests
import sys
import json
import base64
import os
from urllib.parse import urljoin, urlencode
from datetime import datetime, timedelta

g_github_token = ""  # GitHub Token
g_gist_id = ""  # Gist ID




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


def convert_subscribe(subscribe_dict):
    """
    调用 subconverter 服务转换订阅链接
    """
    base_url = "http://localhost:25500/sub"
    filecontent_dict = {}
    for filename, params in subscribe_dict.items():
        try:
            # 拼接完整的 URL
            url = f"{base_url}{params}"
            print(f"Processing {filename} with URL: {url}")

            # 发起请求
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # 添加更新时间戳
                filecontent_dict[filename] = (
                    response.text +
                    f"\n\n# Updated on {(datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                print(f"Successfully processed {filename}.")
            else:
                print(f"Failed to process {filename}. Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    return filecontent_dict


def test_param():
    """
    生成示例参数
    """
    template_params = "?target=clash&insert=false&exclude=%E5%A5%97%E9%A4%90%E5%88%B0%E6%9C%9F%7C%E8%8A%82%E7%82%B9%E8%B6%85%E6%97%B6%7C%E6%9B%B4%E6%8D%A2%7C%E5%89%A9%E4%BD%99%E6%B5%81%E9%87%8F%7C%E5%..."
    subscribe_url = {
        "template.yml": "https://example.com/subscribe?token=xxxxx",
    }
    subscribe_dict = {}
    for filename, url in subscribe_url.items():
        subscribe_dict[filename] = template_params + quote(url)
    convert_param = base64.b64encode(json.dumps(subscribe_dict).encode("utf-8")).decode("utf-8")
    print(f"CONVERT_PARAM={convert_param}")


if __name__ == "__main__":


    try:
        # 解码订阅参数
        subscribe_dict = json.loads(base64.b64decode(os.environ['CONVERT_PARAM']).decode("utf-8"))
    except Exception as e:
        print(f"Failed to decode CONVERT_PARAM: {e}")
        sys.exit(1)

    g_github_token = os.environ.get('PERSONAL_TOKEN', '')
    g_gist_id = os.environ.get('GIST_ID', '')

    # 转换订阅链接
    filecontent_dict = convert_subscribe(subscribe_dict)

    # 更新到 Gist
    if g_github_token and g_gist_id:
        update_gist(gist_id=g_gist_id, filecontent_dict=filecontent_dict)
    else:
        print("GitHub token or Gist ID is missing. Skipping Gist update.")
