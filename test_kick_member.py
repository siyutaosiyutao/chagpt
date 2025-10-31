"""
测试 ChatGPT Team 踢人功能
"""
from curl_cffi import requests as cf_requests
import json

# 你提供的 session 数据
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
    "authProvider": "openai",
    "rumViewTags": {
        "light_account": {
            "fetched": False
        }
    }
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


def get_team_members(access_token, account_id):
    """获取团队成员列表"""
    url = f"https://chatgpt.com/backend-api/accounts/{account_id}/members"
    headers = get_headers(access_token, account_id)
    
    try:
        print(f"🔍 正在获取团队成员列表...")
        print(f"📍 URL: {url}")
        response = cf_requests.get(url, headers=headers, impersonate="chrome110")
        
        print(f"📊 状态码: {response.status_code}")
        print(f"📄 响应内容:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": response.text, "status_code": response.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_pending_invites(access_token, account_id):
    """获取待处理的邀请列表"""
    url = f"https://chatgpt.com/backend-api/accounts/{account_id}/invites"
    headers = get_headers(access_token, account_id)
    
    try:
        print(f"\n🔍 正在获取待处理邀请列表...")
        print(f"📍 URL: {url}")
        response = cf_requests.get(url, headers=headers, impersonate="chrome110")
        
        print(f"📊 状态码: {response.status_code}")
        print(f"📄 响应内容:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": response.text, "status_code": response.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}


def remove_member(access_token, account_id, user_id):
    """移除团队成员 - 方法1: DELETE"""
    url = f"https://chatgpt.com/backend-api/accounts/{account_id}/members/{user_id}"
    headers = get_headers(access_token, account_id)
    
    try:
        print(f"\n🔍 尝试移除成员 (DELETE 方法)...")
        print(f"📍 URL: {url}")
        response = cf_requests.delete(url, headers=headers, impersonate="chrome110")
        
        print(f"📊 状态码: {response.status_code}")
        print(f"📄 响应内容: {response.text}")
        
        if response.status_code in [200, 204]:
            return {"success": True}
        else:
            return {"success": False, "error": response.text, "status_code": response.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}


def revoke_invite(access_token, account_id, invite_id):
    """撤销邀请"""
    url = f"https://chatgpt.com/backend-api/accounts/{account_id}/invites/{invite_id}"
    headers = get_headers(access_token, account_id)
    
    try:
        print(f"\n🔍 尝试撤销邀请...")
        print(f"📍 URL: {url}")
        response = cf_requests.delete(url, headers=headers, impersonate="chrome110")
        
        print(f"📊 状态码: {response.status_code}")
        print(f"📄 响应内容: {response.text}")
        
        if response.status_code in [200, 204]:
            return {"success": True}
        else:
            return {"success": False, "error": response.text, "status_code": response.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    """主函数"""
    access_token = SESSION_DATA['accessToken']
    account_id = SESSION_DATA['account']['id']
    
    print("=" * 60)
    print("🚀 ChatGPT Team 踢人功能测试")
    print("=" * 60)
    print(f"📧 账户邮箱: {SESSION_DATA['user']['email']}")
    print(f"🆔 Account ID: {account_id}")
    print(f"🏢 Organization ID: {SESSION_DATA['account']['organizationId']}")
    print(f"📦 计划类型: {SESSION_DATA['account']['planType']}")
    print("=" * 60)
    
    # 1. 获取团队成员列表
    print("\n【步骤 1】获取团队成员列表")
    members_result = get_team_members(access_token, account_id)
    
    if not members_result['success']:
        print(f"❌ 获取成员列表失败: {members_result.get('error')}")
    
    # 2. 获取待处理邀请
    print("\n【步骤 2】获取待处理邀请列表")
    invites_result = get_pending_invites(access_token, account_id)
    
    if not invites_result['success']:
        print(f"❌ 获取邀请列表失败: {invites_result.get('error')}")
    
    # 3. 测试结论
    print("\n" + "=" * 60)
    print("📋 测试结论:")
    print("=" * 60)
    
    if members_result['success']:
        print("✅ 可以获取团队成员列表")
        members = members_result['data'].get('members', [])
        print(f"   当前团队成员数: {len(members)}")
        
        if members:
            print("\n   成员列表:")
            for idx, member in enumerate(members, 1):
                print(f"   {idx}. {member.get('email', 'N/A')} (ID: {member.get('user_id', 'N/A')})")
    else:
        print("❌ 无法获取团队成员列表")
    
    if invites_result['success']:
        print("\n✅ 可以获取待处理邀请列表")
        invites = invites_result['data'].get('account_invites', [])
        print(f"   当前待处理邀请数: {len(invites)}")
        
        if invites:
            print("\n   邀请列表:")
            for idx, invite in enumerate(invites, 1):
                print(f"   {idx}. {invite.get('email_address', 'N/A')} (ID: {invite.get('id', 'N/A')})")
    else:
        print("❌ 无法获取待处理邀请列表")
    
    print("\n" + "=" * 60)
    print("💡 提示:")
    print("   - 如果能获取成员列表,说明 token 有读取权限")
    print("   - 要测试踢人功能,需要提供具体的 user_id")
    print("   - 要测试撤销邀请,需要提供具体的 invite_id")
    print("=" * 60)


if __name__ == '__main__':
    main()

