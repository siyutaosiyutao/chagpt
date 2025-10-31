"""
测试踢人(移除成员)功能
"""
from curl_cffi import requests as cf_requests
import json

# Session 数据
SESSION_DATA = {
    "user": {
        "id": "user-u9dGYpfVnL72jos24slnRnuW",
        "email": "7hushdiadas2s@siyu.my",
        "idp": "auth0",
        "iat": 1761900235,
        "mfa": False
    },
    "expires": "2026-01-29T08:52:00.463Z",
    "account": {
        "id": "76e2e022-3d0c-4c83-94f9-2f96d3d7e6e2",
        "planType": "team",
        "structure": "workspace",
        "workspaceType": None,
        "organizationId": "org-OeQksFELsYDNPdsfjqrWp89q",
        "isDelinquent": False,
        "gracePeriodId": None
    },
    "accessToken": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE5MzQ0ZTY1LWJiYzktNDRkMS1hOWQwLWY5NTdiMDc5YmQwZSIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsiaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS92MSJdLCJjbGllbnRfaWQiOiJhcHBfWDh6WTZ2VzJwUTl0UjNkRTduSzFqTDVnSCIsImV4cCI6MTc2Mjc2NDIzNSwiaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS9hdXRoIjp7ImNoYXRncHRfY29tcHV0ZV9yZXNpZGVuY3kiOiJub19jb25zdHJhaW50IiwiY2hhdGdwdF9kYXRhX3Jlc2lkZW5jeSI6Im5vX2NvbnN0cmFpbnQiLCJ1c2VyX2lkIjoidXNlci11OWRHWXBmVm5MNzJqb3MyNHNsblJudVcifSwiaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS9wcm9maWxlIjp7ImVtYWlsIjoiN2h1c2hkaWFkYXMyc0BzaXl1Lm15IiwiZW1haWxfdmVyaWZpZWQiOnRydWV9LCJpYXQiOjE3NjE5MDAyMzQsImlzcyI6Imh0dHBzOi8vYXV0aC5vcGVuYWkuY29tIiwianRpIjoiZTkwYzZlN2YtY2EyMi00ZDcwLWEzNWYtMDQ5N2RmYzg3YjRlIiwibmJmIjoxNzYxOTAwMjM0LCJwd2RfYXV0aF90aW1lIjoxNzYxOTAwMjMxODIyLCJzY3AiOlsib3BlbmlkIiwiZW1haWwiLCJwcm9maWxlIiwib2ZmbGluZV9hY2Nlc3MiLCJtb2RlbC5yZXF1ZXN0IiwibW9kZWwucmVhZCIsIm9yZ2FuaXphdGlvbi5yZWFkIiwib3JnYW5pemF0aW9uLndyaXRlIl0sInNlc3Npb25faWQiOiJhdXRoc2Vzc185QWFzZGtyUEdNNmxrSWtpU3VWVzZMRGkiLCJzdWIiOiJhdXRoMHxLYmRPdVZtZFVETTd6ZjVjSkQwcERBNjEifQ.T5sIs41_xj4XXt3CIiBi-Xh8xQE3Szfjw4DE8gf3NvCZXJL5R5ATdQ81_Q80f3hErtZL5N4A6JqOG36_rgwRJhxADa3ogAHS-JehEn362zL5jMLztec_XRvDFoDpdSdmhNGLq3idhv5VcF0T2gU7Kb_cODYGkN16jPUjsmb6qIhwRHwe5AGl4roK59yiwg5KfuXI75UipGexjEX8eDseLINKQQ3oaSXpnvSRFMe9RqwlBTxT3K0lSxp-lJTGAH9nTIJe6GzRm_oTNd6Sa2-VCzrOqt5tFoM4L2PeKaVnbrUDnAYygrHdZ138M9n5vS52HcXbf_HBZTiTh2S9yuuUcMipN3HmcfwVz6aTgBYXo4uk_uRX08tbushNjqDHCBPGXOGlb-UdZokNlzY8P38HCiMdA2rAKOydyl4QpWQNYa5oau-Sd6wVS-w90kMDfdP3l8CEhFfV2lsg3z4s8EVkVQgOSKMJUZOwlbxymEfXeZHUqCSCQi12CCY_a1fTP4WricUHnTr19_hG8Ar5kYXCWR--z2vp6d836p8IWJwjdlsWCEm9lZlOqSM7qvLFfhhQLKDJTqNBAQjb_pgiWK9z8wA5CG8BDh7_JSCMX0pwGEYianrqVIypbLDYXKdwiBmU_cyP-AToy908YEU3AUUeWPO-4QwF7YGho5V7d1k2A3s",
    "authProvider": "openai"
}

# 要移除的成员信息
TARGET_MEMBER = {
    "email": "91239123@siyu.my",
    "user_id": "user-rJ1gjVxxQieYSDy9T21WmhEY",
    "account_user_id": "user-rJ1gjVxxQieYSDy9T21WmhEY__76e2e022-3d0c-4c83-94f9-2f96d3d7e6e2"
}

def get_headers(access_token, account_id):
    """构建请求头"""
    return {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
        "authorization": f"Bearer {access_token}",
        "chatgpt-account-id": account_id,
        "content-type": "application/json",
        "oai-device-id": "a9c9e9a0-f72d-4fbc-800e-2d0e1e3c3b54",
        "oai-language": "zh-CN",
        "origin": "https://chatgpt.com",
        "referer": "https://chatgpt.com/admin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }


def get_members(access_token, account_id):
    """获取成员列表"""
    url = f"https://chatgpt.com/backend-api/accounts/{account_id}/users"
    headers = get_headers(access_token, account_id)
    
    try:
        response = cf_requests.get(url, headers=headers, impersonate="chrome110")
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def test_remove_method(name, url, access_token, account_id, method="DELETE", payload=None):
    """测试移除成员的方法"""
    headers = get_headers(access_token, account_id)
    
    print(f"\n{'='*60}")
    print(f"🔍 测试: {name}")
    print(f"📍 URL: {url}")
    print(f"🔧 方法: {method}")
    if payload:
        print(f"📦 Payload: {json.dumps(payload, indent=2)}")
    print(f"{'='*60}")
    
    try:
        if method == "DELETE":
            if payload:
                response = cf_requests.delete(url, headers=headers, json=payload, impersonate="chrome110")
            else:
                response = cf_requests.delete(url, headers=headers, impersonate="chrome110")
        elif method == "POST":
            response = cf_requests.post(url, headers=headers, json=payload or {}, impersonate="chrome110")
        elif method == "PUT":
            response = cf_requests.put(url, headers=headers, json=payload or {}, impersonate="chrome110")
        
        print(f"📊 状态码: {response.status_code}")
        
        try:
            data = response.json()
            print(f"📄 响应内容:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return {"success": response.status_code in [200, 204], "data": data, "status_code": response.status_code}
        except:
            print(f"📄 响应内容 (非JSON): {response.text}")
            return {"success": response.status_code in [200, 204], "text": response.text, "status_code": response.status_code}
            
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return {"success": False, "error": str(e)}


def main():
    """主函数"""
    access_token = SESSION_DATA['accessToken']
    account_id = SESSION_DATA['account']['id']
    user_id = TARGET_MEMBER['user_id']
    account_user_id = TARGET_MEMBER['account_user_id']
    email = TARGET_MEMBER['email']
    
    print("=" * 60)
    print("🚀 ChatGPT Team 踢人功能测试")
    print("=" * 60)
    print(f"📧 当前账户: {SESSION_DATA['user']['email']}")
    print(f"🆔 Account ID: {account_id}")
    print(f"👤 目标成员: {email}")
    print(f"   User ID: {user_id}")
    print(f"   Account User ID: {account_user_id}")
    print("=" * 60)
    
    # 先获取当前成员列表
    print("\n【步骤 1】获取当前成员列表")
    members_result = get_members(access_token, account_id)
    if members_result['success']:
        members = members_result['data'].get('items', [])
        print(f"✅ 当前成员数: {len(members)}")
        for member in members:
            print(f"   - {member['email']} ({member['role']})")
    else:
        print(f"❌ 获取失败: {members_result.get('error')}")
    
    # 测试不同的移除方法
    print("\n【步骤 2】测试不同的移除方法")
    
    test_methods = [
        ("方法1: DELETE /accounts/{account_id}/users/{user_id}",
         f"https://chatgpt.com/backend-api/accounts/{account_id}/users/{user_id}",
         "DELETE", None),
        
        ("方法2: DELETE /accounts/{account_id}/users/{account_user_id}",
         f"https://chatgpt.com/backend-api/accounts/{account_id}/users/{account_user_id}",
         "DELETE", None),
        
        ("方法3: POST /accounts/{account_id}/users/remove",
         f"https://chatgpt.com/backend-api/accounts/{account_id}/users/remove",
         "POST", {"user_id": user_id}),
        
        ("方法4: POST /accounts/{account_id}/users/remove (account_user_id)",
         f"https://chatgpt.com/backend-api/accounts/{account_id}/users/remove",
         "POST", {"user_id": account_user_id}),
        
        ("方法5: DELETE /accounts/{account_id}/members/{user_id}",
         f"https://chatgpt.com/backend-api/accounts/{account_id}/members/{user_id}",
         "DELETE", None),
        
        ("方法6: POST /accounts/{account_id}/remove-user",
         f"https://chatgpt.com/backend-api/accounts/{account_id}/remove-user",
         "POST", {"user_id": user_id}),
    ]
    
    results = []
    for name, url, method, payload in test_methods:
        result = test_remove_method(name, url, access_token, account_id, method, payload)
        results.append((name, result))
        
        # 如果成功,立即检查成员列表
        if result['success']:
            print(f"\n✅ {name} 成功! 正在验证...")
            members_result = get_members(access_token, account_id)
            if members_result['success']:
                members = members_result['data'].get('items', [])
                print(f"   当前成员数: {len(members)}")
                if len(members) == 1:
                    print(f"   ✅ 成员已被成功移除!")
                    break
                else:
                    print(f"   ⚠️  成员仍在列表中")
    
    # 最终验证
    print("\n【步骤 3】最终验证")
    members_result = get_members(access_token, account_id)
    if members_result['success']:
        members = members_result['data'].get('items', [])
        print(f"✅ 当前成员数: {len(members)}")
        for member in members:
            print(f"   - {member['email']} ({member['role']})")
        
        if len(members) == 1:
            print(f"\n🎉 成功! 成员 {email} 已被移除!")
        else:
            print(f"\n⚠️  成员 {email} 仍在团队中")
    
    # 总结
    print("\n" + "=" * 60)
    print("📋 测试总结")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ 成功" if result['success'] else f"❌ 失败 ({result.get('status_code', 'N/A')})"
        print(f"{status} - {name}")
    
    print("=" * 60)


if __name__ == '__main__':
    main()

