import os
import sys
import json
import base64
import requests
from datetime import datetime

def update_cloudflare_kv(account_id, namespace_id, api_token, original_url, config_content):
    # Cloudflare API endpoint
    base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/{namespace_id}/values"
    
    # 准备配置数据
    config_data = {
        "original_url": original_url,
        "converted_config": base64.b64encode(config_content.encode()).decode(),
        "update_time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    
    # 设置请求头
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    try:
        # 更新 KV
        response = requests.put(
            f"{base_url}/current_config",
            headers=headers,
            json=config_data
        )
        
        if response.status_code == 200:
            print("Successfully updated Cloudflare KV")
            return True
        else:
            print(f"Failed to update KV: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"Error updating KV: {str(e)}")
        return False

if __name__ == "__main__":
    # 从环境变量获取配置
    account_id = os.environ["CF_ACCOUNT_ID"]
    namespace_id = os.environ["CF_NAMESPACE_ID"]
    api_token = os.environ["CF_API_TOKEN"]
    original_url = os.environ["SUBSCRIPTION_URL"]
    
    # 读取转换后的配置文件
    try:
        with open("converted_config.yaml", "r", encoding="utf-8") as f:
            config_content = f.read()
    except Exception as e:
        print(f"Error reading config file: {str(e)}")
        sys.exit(1)
    
    # 更新 KV
    if not update_cloudflare_kv(account_id, namespace_id, api_token, original_url, config_content):
        sys.exit(1)
