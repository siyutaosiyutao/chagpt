"""
测试邀请功能
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

def invite_to_team(access_token, account_id, email):
    """邀请成员加入团队"""
    url = f"https://chatgpt.com/backend-api/accounts/{account_id}/invites"
    
    headers = {
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
    
    payload = {
        "email_addresses": [email],
        "role": "standard-user",
        "resend_emails": False
    }
    
    try:
        print(f"🔍 正在邀请 {email} 加入团队...")
        print(f"📍 URL: {url}")
        print(f"📦 Payload: {json.dumps(payload, indent=2)}")
        
        response = cf_requests.post(url, headers=headers, json=payload, impersonate="chrome110")
        
        print(f"\n📊 状态码: {response.status_code}")
        print(f"📄 响应内容:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        
        if response.status_code in [200, 201]:
            data = response.json()
            invites = data.get('account_invites', [])
            if invites:
                invite_id = invites[0].get('id')
                print(f"\n✅ 邀请成功!")
                print(f"   邀请 ID: {invite_id}")
                print(f"   邮箱: {email}")
                return {"success": True, "invite_id": invite_id, "data": data}
            return {"success": True, "data": data}
        else:
            print(f"\n❌ 邀请失败!")
            return {"success": False, "error": response.text, "status_code": response.status_code}
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        return {"success": False, "error": str(e)}


def main():
    """主函数"""
    access_token = SESSION_DATA['accessToken']
    account_id = SESSION_DATA['account']['id']
    email_to_invite = "91239123@siyu.my"
    
    print("=" * 60)
    print("🚀 ChatGPT Team 邀请测试")
    print("=" * 60)
    print(f"📧 当前账户: {SESSION_DATA['user']['email']}")
    print(f"🆔 Account ID: {account_id}")
    print(f"👤 邀请邮箱: {email_to_invite}")
    print("=" * 60)
    print()
    
    result = invite_to_team(access_token, account_id, email_to_invite)
    
    print("\n" + "=" * 60)
    if result['success']:
        print("✅ 邀请已发送成功!")
        print("📧 请检查邮箱 91239123@siyu.my 查收邀请邮件")
    else:
        print("❌ 邀请发送失败")
        print(f"   错误信息: {result.get('error')}")
    print("=" * 60)


if __name__ == '__main__':
    main()

