"""
自动检测踢人服务
"""
import time
import random
import threading
from datetime import datetime
from curl_cffi import requests as cf_requests
from database import Team, Invitation, AutoKickConfig, KickLog
import pytz


class AutoKickService:
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        """启动自动检测服务"""
        if self.running:
            print("⚠️  自动检测服务已在运行中")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print("✅ 自动检测踢人服务已启动")
    
    def stop(self):
        """停止自动检测服务"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("🛑 自动检测踢人服务已停止")
    
    def _run_loop(self):
        """主循环"""
        while self.running:
            try:
                config = AutoKickConfig.get()
                
                if not config or not config['enabled']:
                    # 如果未启用,每 60 秒检查一次配置
                    time.sleep(60)
                    continue
                
                # 检查是否在运行时间内
                if not self._is_in_running_time(config):
                    # 不在运行时间内,等待 60 秒后再检查
                    time.sleep(60)
                    continue
                
                # 执行检测
                self._check_and_kick()
                
                # 随机等待时间
                interval = random.randint(
                    config['check_interval_min'],
                    config['check_interval_max']
                )
                print(f"⏰ 下次检测将在 {interval} 秒后进行")
                time.sleep(interval)
                
            except Exception as e:
                print(f"❌ 自动检测服务出错: {str(e)}")
                # 出错后等待 5 分钟
                time.sleep(300)
    
    def _is_in_running_time(self, config):
        """检查是否在运行时间内"""
        try:
            # 获取北京时间
            tz = pytz.timezone(config.get('timezone', 'Asia/Shanghai'))
            now = datetime.now(tz)
            current_time = now.strftime('%H:%M')
            
            start_time = config['start_time']
            end_time = config['end_time']
            
            # 简单的时间比较
            if start_time <= end_time:
                # 正常情况: 09:00 - 22:00
                return start_time <= current_time <= end_time
            else:
                # 跨天情况: 22:00 - 09:00
                return current_time >= start_time or current_time <= end_time
        except Exception as e:
            print(f"⚠️  时间检查出错: {str(e)}")
            return True  # 出错时默认允许运行
    
    def _check_and_kick(self):
        """检查并踢出非法成员和过期临时成员"""
        print(f"\n{'='*60}")
        print(f"🔍 开始检测非法成员 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        # 1. 检查过期的临时邀请
        self._check_temp_invitations()

        # 2. 检查所有 Team 的非法成员
        teams = Team.get_all()

        for team in teams:
            try:
                self._check_team(team)
            except Exception as e:
                print(f"❌ 检测 Team {team['name']} 时出错: {str(e)}")

        print(f"{'='*60}")
        print(f"✅ 检测完成")
        print(f"{'='*60}\n")
    
    def _check_temp_invitations(self):
        """检查并踢出过期的临时邀请成员"""
        print(f"\n🕐 检查过期的临时邀请...")

        expired_invitations = Invitation.get_temp_expired()

        if not expired_invitations:
            print(f"   ✅ 没有过期的临时邀请")
            return

        print(f"   发现 {len(expired_invitations)} 个过期的临时邀请")

        for invitation in expired_invitations:
            team = Team.get_by_id(invitation['team_id'])
            if not team:
                continue

            email = invitation['email']
            print(f"   ⏰ {email} 的临时邀请已过期,准备踢出")

            # 获取成员列表,找到对应的 user_id
            members = self._get_team_members(team['access_token'], team['account_id'])
            if not members:
                continue

            member = next((m for m in members if m.get('email', '').lower() == email.lower()), None)
            if member:
                user_id = member.get('id', '')
                self._kick_member(team, user_id, email, "临时邀请已过期")

    def _check_team(self, team):
        """检查单个 Team"""
        team_id = team['id']
        team_name = team['name']
        account_id = team['account_id']
        access_token = team['access_token']

        print(f"\n📋 检测 Team: {team_name}")

        # 1. 获取所有已邀请的邮箱 (从 invitations 表)
        invited_emails = set(email.lower() for email in Invitation.get_all_emails_by_team(team_id))

        # 添加 Team 所有者邮箱
        if team['email']:
            invited_emails.add(team['email'].lower())

        print(f"   已邀请邮箱数: {len(invited_emails)}")

        # 2. 获取当前 Team 成员
        members = self._get_team_members(access_token, account_id)

        if not members:
            print(f"   ⚠️  无法获取成员列表")
            return

        print(f"   当前成员数: {len(members)}")

        # 3. 检查每个成员
        for member in members:
            member_email = member.get('email', '').lower()
            member_role = member.get('role', '')
            member_user_id = member.get('id', '')

            # 跳过所有者
            if member_role == 'account-owner':
                print(f"   ✅ {member_email} (所有者,跳过)")
                continue

            # 检查是否在邀请列表中
            if member_email in invited_emails:
                print(f"   ✅ {member_email} (合法成员)")
            else:
                # 非法成员,踢出
                print(f"   ⚠️  {member_email} (非法成员,准备踢出)")
                self._kick_member(team, member_user_id, member_email, "未经邀请的成员")
    
    def _get_team_members(self, access_token, account_id):
        """获取 Team 成员列表"""
        url = f"https://chatgpt.com/backend-api/accounts/{account_id}/users"
        
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
        
        try:
            response = cf_requests.get(url, headers=headers, impersonate="chrome110", timeout=10)

            if response.status_code == 200:
                data = response.json()
                # 统一使用account_users字段，与app_new.py保持一致
                return data.get('account_users', [])
            elif response.status_code == 429:
                print(f"   ⚠️  请求过于频繁,等待 5 分钟")
                time.sleep(300)
                return None
            else:
                print(f"   ❌ 获取成员列表失败: {response.status_code}")
                return None
        except Exception as e:
            print(f"   ❌ 获取成员列表出错: {str(e)}")
            return None
    
    def _kick_member(self, team, user_id, email, reason):
        """踢出成员"""
        team_id = team['id']
        account_id = team['account_id']
        access_token = team['access_token']
        
        url = f"https://chatgpt.com/backend-api/accounts/{account_id}/users/{user_id}"
        
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
        
        try:
            response = cf_requests.delete(url, headers=headers, impersonate="chrome110", timeout=10)

            if response.status_code == 200:
                # 从invitations表中删除记录，释放位置
                Invitation.delete_by_email(team_id, email)

                print(f"   ✅ 成功踢出: {email}")
                KickLog.create(team_id, user_id, email, reason, success=True)
            else:
                error_msg = f"状态码: {response.status_code}"
                print(f"   ❌ 踢出失败: {email} - {error_msg}")
                KickLog.create(team_id, user_id, email, reason, success=False, error_message=error_msg)
        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ 踢出出错: {email} - {error_msg}")
            KickLog.create(team_id, user_id, email, reason, success=False, error_message=error_msg)


# 全局服务实例
auto_kick_service = AutoKickService()

