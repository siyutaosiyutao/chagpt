#!/usr/bin/env python3
"""
测试 API 端点是否正常工作
"""
import sys
import requests
import time

# 测试管理员API
def test_admin_teams():
    print("=" * 60)
    print("🧪 测试 /api/admin/teams 端点")
    print("=" * 60)

    # 注意：这个测试需要在服务器上运行，并且需要管理员session
    url = "http://127.0.0.1:5002/api/admin/teams"

    try:
        print(f"\n📡 发送请求到: {url}")
        start_time = time.time()

        # 设置较长的超时时间
        response = requests.get(url, timeout=30)

        elapsed = time.time() - start_time
        print(f"⏱️  响应时间: {elapsed:.2f}秒")
        print(f"📊 HTTP状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ 响应成功")
            print(f"📋 返回数据结构: {list(data.keys())}")

            if 'teams' in data:
                print(f"🔢 Teams数量: {len(data['teams'])}")

                # 显示每个team的基本信息
                for i, team in enumerate(data['teams'][:5], 1):  # 只显示前5个
                    print(f"\n  Team {i}: {team.get('name', 'Unknown')}")
                    print(f"    - ID: {team.get('id')}")
                    print(f"    - Token有效: {team.get('token_valid', 'unknown')}")
                    print(f"    - 成员数: {team.get('member_count', 0)}/4")

                if len(data['teams']) > 5:
                    print(f"\n  ... 还有 {len(data['teams']) - 5} 个teams")

        elif response.status_code == 401:
            print(f"⚠️  认证失败: 需要管理员登录")
            print(f"💡 提示: 这个测试需要在浏览器登录管理员后获取cookie")

        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"响应内容: {response.text[:500]}")

    except requests.exceptions.Timeout:
        print(f"❌ 请求超时 (>30秒)")
        print(f"💡 可能原因:")
        print(f"   1. 某个team的token检测卡住了")
        print(f"   2. 网络连接问题")
        print(f"   3. ChatGPT API响应缓慢")

    except requests.exceptions.ConnectionError as e:
        print(f"❌ 连接失败: {e}")
        print(f"💡 检查服务是否正在运行: systemctl status chatgpt-team")

    except Exception as e:
        print(f"❌ 未知错误: {e}")


# 测试数据库直接查询
def test_database_direct():
    print("\n" + "=" * 60)
    print("🗄️  测试数据库直接查询")
    print("=" * 60)

    try:
        # 添加项目路径
        sys.path.insert(0, '/opt/chatgpt-team')
        from database import Team, Invitation

        print("\n📊 从数据库获取Teams...")
        teams = Team.get_all()
        print(f"✅ Teams数量: {len(teams)}")

        for i, team in enumerate(teams[:5], 1):
            invitations = Invitation.get_by_team(team['id'])
            success_count = len([inv for inv in invitations if inv['status'] == 'success'])
            print(f"\n  Team {i}: {team['name']}")
            print(f"    - ID: {team['id']}")
            print(f"    - Account ID: {team['account_id'][:20]}...")
            print(f"    - 成功邀请数: {success_count}")
            print(f"    - 最后邀请时间: {team.get('last_invite_at', 'None')}")

        if len(teams) > 5:
            print(f"\n  ... 还有 {len(teams) - 5} 个teams")

        return True

    except Exception as e:
        print(f"❌ 数据库查询失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    # 先测试数据库
    if test_database_direct():
        print("\n" + "=" * 60)
        print("✅ 数据库查询正常")
        print("=" * 60)

    print("\n")

    # 再测试API
    test_admin_teams()

    print("\n" + "=" * 60)
    print("🏁 测试完成")
    print("=" * 60)
