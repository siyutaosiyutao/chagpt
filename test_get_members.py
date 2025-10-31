"""
测试获取团队成员功能
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


def test_api_endpoint(name, url, access_token, account_id, method="GET"):
    """测试 API 端点"""
    headers = get_headers(access_token, account_id)
    
    print(f"\n{'='*60}")
    print(f"🔍 测试: {name}")
    print(f"📍 URL: {url}")
    print(f"🔧 方法: {method}")
    print(f"{'='*60}")
    
    try:
        if method == "GET":
            response = cf_requests.get(url, headers=headers, impersonate="chrome110")
        elif method == "POST":
            response = cf_requests.post(url, headers=headers, json={}, impersonate="chrome110")
        
        print(f"📊 状态码: {response.status_code}")
        
        try:
            data = response.json()
            print(f"📄 响应内容:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return {"success": response.status_code == 200, "data": data, "status_code": response.status_code}
        except:
            print(f"📄 响应内容 (非JSON):")
            print(response.text)
            return {"success": response.status_code == 200, "text": response.text, "status_code": response.status_code}
            
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return {"success": False, "error": str(e)}


def main():
    """主函数"""
    access_token = SESSION_DATA['accessToken']
    account_id = SESSION_DATA['account']['id']
    org_id = SESSION_DATA['account']['organizationId']
    
    print("=" * 60)
    print("🚀 ChatGPT Team 成员查看功能测试")
    print("=" * 60)
    print(f"📧 当前账户: {SESSION_DATA['user']['email']}")
    print(f"🆔 Account ID: {account_id}")
    print(f"🏢 Organization ID: {org_id}")
    print("=" * 60)
    
    # 测试不同的 API 端点
    endpoints = [
        ("方法1: /accounts/{account_id}/members", 
         f"https://chatgpt.com/backend-api/accounts/{account_id}/members", "GET"),
        
        ("方法2: /accounts/{account_id}/users", 
         f"https://chatgpt.com/backend-api/accounts/{account_id}/users", "GET"),
        
        ("方法3: /organizations/{org_id}/members", 
         f"https://chatgpt.com/backend-api/organizations/{org_id}/members", "GET"),
        
        ("方法4: /organizations/{org_id}/users", 
         f"https://chatgpt.com/backend-api/organizations/{org_id}/users", "GET"),
        
        ("方法5: /admin/accounts/{account_id}/members", 
         f"https://chatgpt.com/backend-api/admin/accounts/{account_id}/members", "GET"),
        
        ("方法6: /accounts/{account_id}/team/members", 
         f"https://chatgpt.com/backend-api/accounts/{account_id}/team/members", "GET"),
        
        ("方法7: /workspace/members", 
         f"https://chatgpt.com/backend-api/workspace/members", "GET"),
        
        ("方法8: /accounts/{account_id}/workspace/members", 
         f"https://chatgpt.com/backend-api/accounts/{account_id}/workspace/members", "GET"),
    ]
    
    results = []
    for name, url, method in endpoints:
        result = test_api_endpoint(name, url, access_token, account_id, method)
        results.append((name, result))
    
    # 总结
    print("\n" + "=" * 60)
    print("📋 测试总结")
    print("=" * 60)
    
    success_count = 0
    for name, result in results:
        status = "✅ 成功" if result['success'] else f"❌ 失败 ({result.get('status_code', 'N/A')})"
        print(f"{status} - {name}")
        if result['success']:
            success_count += 1
    
    print(f"\n成功: {success_count}/{len(results)}")
    print("=" * 60)


if __name__ == '__main__':
    main()

