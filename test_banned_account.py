"""
测试被封禁账号的API响应
用于找出封禁时的真实返回信息
"""
from curl_cffi import requests as cf_requests
import json
import sys

def test_token_status(access_token, account_id):
    """测试Token状态，打印详细响应"""
    url = f"https://chatgpt.com/backend-api/accounts/{account_id}/users"

    headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
        "authorization": f"Bearer {access_token}",
        "chatgpt-account-id": account_id,
        "origin": "https://chatgpt.com",
        "referer": "https://chatgpt.com/admin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    print("="*60)
    print("🔍 测试Token状态")
    print("="*60)
    print(f"Account ID: {account_id}")
    print(f"Token: {access_token[:50]}...")
    print()

    try:
        response = cf_requests.get(url, headers=headers, impersonate="chrome110")

        print(f"📊 HTTP状态码: {response.status_code}")
        print(f"📋 响应头:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        print()

        print(f"📄 响应体:")
        try:
            data = response.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except:
            print(response.text)

        print()
        print("="*60)
        print("分析:")
        print("="*60)

        if response.status_code == 200:
            print("✅ Token有效")
        elif response.status_code == 401:
            print("❌ Token失效/过期")
        elif response.status_code == 403:
            print("🚫 可能被封禁或无权限")
        elif response.status_code == 429:
            print("⚠️ 请求限流")
        else:
            print(f"❓ 未知状态: {response.status_code}")

        # 尝试从响应体中提取更多信息
        try:
            data = response.json()
            if 'error' in data:
                print(f"错误信息: {data['error']}")
            if 'detail' in data:
                print(f"详细信息: {data['detail']}")
            if 'message' in data:
                print(f"消息: {data['message']}")
        except:
            pass

    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("""
    使用方法:
    python test_banned_account.py <access_token> <account_id>

    或者直接编辑此文件，填入测试数据：
    """)

    if len(sys.argv) == 3:
        access_token = sys.argv[1]
        account_id = sys.argv[2]
        test_token_status(access_token, account_id)
    else:
        # 在这里填入被封禁账号的信息进行测试
        TEST_ACCESS_TOKEN = "粘贴你被封禁账号的token"
        TEST_ACCOUNT_ID = "粘贴你被封禁账号的account_id"

        if TEST_ACCESS_TOKEN.startswith("粘贴"):
            print("❌ 请先在脚本中填入测试数据")
            print("或使用命令行参数: python test_banned_account.py <token> <account_id>")
        else:
            test_token_status(TEST_ACCESS_TOKEN, TEST_ACCOUNT_ID)
