"""
测试组织ID识别和自动更新功能
"""
from database import Team

print("=" * 60)
print("测试组织ID识别功能")
print("=" * 60)

# 1. 查看当前所有 Teams
teams = Team.get_all()
print(f"\n当前 Teams 数量: {len(teams)}")
for team in teams:
    print(f"  - {team['name']}")
    print(f"    ID: {team['id']}")
    print(f"    Organization ID: {team['organization_id']}")
    print(f"    Email: {team['email']}")
    print(f"    Account ID: {team['account_id']}")
    print()

# 2. 测试根据 organization_id 查找
if teams:
    test_org_id = teams[0]['organization_id']
    print(f"测试查找 Organization ID: {test_org_id}")
    
    found_team = Team.get_by_organization_id(test_org_id)
    if found_team:
        print(f"✅ 找到 Team: {found_team['name']}")
    else:
        print(f"❌ 未找到")
    print()

# 3. 测试更新 Team 信息
if teams:
    test_team_id = teams[0]['id']
    print(f"测试更新 Team ID: {test_team_id}")
    
    Team.update_team_info(
        test_team_id,
        name="测试更新名称",
        access_token="new_test_token_12345"
    )
    
    updated_team = Team.get_by_id(test_team_id)
    print(f"✅ 更新后的名称: {updated_team['name']}")
    print(f"✅ 更新后的 Token: {updated_team['access_token'][:20]}...")
    print()
    
    # 恢复原名称
    Team.update_team_info(test_team_id, name=teams[0]['name'])
    print(f"✅ 已恢复原名称")

print(f"\n{'=' * 60}")
print(f"✅ 测试完成!")
print(f"{'=' * 60}")

print(f"\n💡 使用说明:")
print(f"1. 当你上传相同 organization_id 的 Session JSON 时")
print(f"2. 系统会自动识别并更新已存在的 Team")
print(f"3. 而不是创建新的 Team")
print(f"4. 这样可以避免重复,并自动更新过期的 Token")

