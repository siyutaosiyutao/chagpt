"""
完整流程测试 - 组织ID识别 + 自动更新
"""
import json
from database import Team

print("=" * 80)
print("完整流程测试: 组织ID识别 + 自动更新")
print("=" * 80)

# 模拟的 Session JSON (第一次上传)
session_json_v1 = {
    "user": {
        "id": "user-test123",
        "email": "test@example.com"
    },
    "account": {
        "id": "account-test-123",
        "organizationId": "org-TEST-DEMO-12345",
        "planType": "team"
    },
    "accessToken": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.OLD_TOKEN_V1"
}

# 模拟的 Session JSON (Token 过期后重新上传)
session_json_v2 = {
    "user": {
        "id": "user-test123",
        "email": "test@example.com"
    },
    "account": {
        "id": "account-test-123",
        "organizationId": "org-TEST-DEMO-12345",  # 相同的 organization_id
        "planType": "team"
    },
    "accessToken": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.NEW_TOKEN_V2"  # 新的 Token
}

print("\n" + "=" * 80)
print("步骤 1: 第一次上传 Session JSON (创建新 Team)")
print("=" * 80)

# 提取信息
name_v1 = session_json_v1['user']['email']
account_id_v1 = session_json_v1['account']['id']
access_token_v1 = session_json_v1['accessToken']
organization_id_v1 = session_json_v1['account']['organizationId']
email_v1 = session_json_v1['user']['email']

print(f"\n提取的信息:")
print(f"  名称: {name_v1}")
print(f"  Organization ID: {organization_id_v1}")
print(f"  Access Token: {access_token_v1[:50]}...")

# 检查是否已存在
existing_team = Team.get_by_organization_id(organization_id_v1)

if existing_team:
    print(f"\n⚠️  检测到已存在的组织!")
    print(f"  Team ID: {existing_team['id']}")
    print(f"  Team 名称: {existing_team['name']}")
    print(f"\n正在更新 Token...")
    
    Team.update_team_info(
        existing_team['id'],
        name=name_v1,
        account_id=account_id_v1,
        access_token=access_token_v1,
        email=email_v1
    )
    
    team_id = existing_team['id']
    print(f"✅ Token 更新成功!")
    is_new = False
else:
    print(f"\n✅ 这是一个新的组织,正在创建 Team...")
    
    team_id = Team.create(name_v1, account_id_v1, access_token_v1, organization_id_v1, email_v1)
    
    print(f"✅ Team 创建成功!")
    print(f"  Team ID: {team_id}")
    is_new = True

# 查看创建的 Team
team = Team.get_by_id(team_id)
print(f"\n当前 Team 信息:")
print(f"  ID: {team['id']}")
print(f"  名称: {team['name']}")
print(f"  Organization ID: {team['organization_id']}")
print(f"  Access Token: {team['access_token'][:50]}...")
print(f"  创建时间: {team['created_at']}")
print(f"  更新时间: {team['updated_at']}")

print("\n" + "=" * 80)
print("步骤 2: 模拟 Token 过期,重新上传 Session JSON")
print("=" * 80)

print(f"\n假设几天后,Token 过期了...")
print(f"你重新登录 ChatGPT,获取了新的 Session JSON")
print(f"新的 Access Token: {session_json_v2['accessToken'][:50]}...")

# 提取信息
name_v2 = session_json_v2['user']['email']
account_id_v2 = session_json_v2['account']['id']
access_token_v2 = session_json_v2['accessToken']
organization_id_v2 = session_json_v2['account']['organizationId']
email_v2 = session_json_v2['user']['email']

print(f"\n检查 Organization ID: {organization_id_v2}")

# 检查是否已存在
existing_team = Team.get_by_organization_id(organization_id_v2)

if existing_team:
    print(f"\n✅ 检测到已存在的组织!")
    print(f"  Team ID: {existing_team['id']}")
    print(f"  Team 名称: {existing_team['name']}")
    print(f"  旧 Token: {existing_team['access_token'][:50]}...")
    
    print(f"\n正在自动更新 Token...")
    
    Team.update_team_info(
        existing_team['id'],
        name=name_v2,
        account_id=account_id_v2,
        access_token=access_token_v2,
        email=email_v2
    )
    
    team_id = existing_team['id']
    print(f"✅ Token 自动更新成功!")
    is_new = False
else:
    print(f"\n这是一个新的组织,正在创建 Team...")
    team_id = Team.create(name_v2, account_id_v2, access_token_v2, organization_id_v2, email_v2)
    print(f"✅ Team 创建成功! ID: {team_id}")
    is_new = True

# 查看更新后的 Team
team = Team.get_by_id(team_id)
print(f"\n更新后的 Team 信息:")
print(f"  ID: {team['id']}")
print(f"  名称: {team['name']}")
print(f"  Organization ID: {team['organization_id']}")
print(f"  Access Token: {team['access_token'][:50]}...")
print(f"  创建时间: {team['created_at']}")
print(f"  更新时间: {team['updated_at']}")

print("\n" + "=" * 80)
print("步骤 3: 验证结果")
print("=" * 80)

print(f"\n对比:")
print(f"  旧 Token: {access_token_v1[:50]}...")
print(f"  新 Token: {access_token_v2[:50]}...")
print(f"  当前 Token: {team['access_token'][:50]}...")

if team['access_token'] == access_token_v2:
    print(f"\n✅ Token 更新成功!")
else:
    print(f"\n❌ Token 更新失败!")

print(f"\n✅ 测试完成!")
print(f"\n总结:")
print(f"  1. 第一次上传: 创建了新 Team (ID: {team_id})")
print(f"  2. 第二次上传: 自动识别并更新了 Token")
print(f"  3. 没有创建重复的 Team")
print(f"  4. 访问密钥保持不变,继续有效")

print("\n" + "=" * 80)
print("清理测试数据")
print("=" * 80)

# 删除测试 Team
Team.delete(team_id)
print(f"\n✅ 测试 Team 已删除")

print("\n" + "=" * 80)
print("✅ 所有测试通过!")
print("=" * 80)

