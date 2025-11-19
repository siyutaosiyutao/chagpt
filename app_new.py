"""
ChatGPT Team 自动邀请系统 - 主应用
"""
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from curl_cffi import requests as cf_requests
import json
from functools import wraps
from database import init_db, Team, AccessKey, Invitation, AutoKickConfig, KickLog, LoginAttempt
from datetime import datetime, timedelta
import pytz
from config import *
from auto_kick_service import auto_kick_service

app = Flask(__name__)
app.secret_key = SECRET_KEY

# 初始化数据库
init_db()


def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({"error": "需要管理员权限"}), 403
        return f(*args, **kwargs)
    return decorated_function


def invite_to_team(access_token, account_id, email, team_id=None):
    """调用 ChatGPT API 邀请成员"""
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
        response = cf_requests.post(url, headers=headers, json=payload, impersonate="chrome110")
        
        if response.status_code in [200, 201]:
            data = response.json()
            invites = data.get('account_invites', [])
            # 成功时重置错误计数
            if team_id:
                Team.reset_token_error(team_id)
            if invites:
                return {"success": True, "invite_id": invites[0].get('id')}
            return {"success": True}
        elif response.status_code == 401:
            # 检测到401，增加错误计数
            if team_id:
                status = Team.increment_token_error(team_id)
                if status and status['token_status'] == 'expired':
                    return {
                        "success": False, 
                        "error": "Token已过期，请更新该Team的Token",
                        "error_code": "TOKEN_EXPIRED",
                        "status_code": 401
                    }
            return {"success": False, "error": response.text, "status_code": response.status_code}
        else:
            return {"success": False, "error": response.text, "status_code": response.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== 用户端路由 ====================

@app.route('/')
def index():
    """用户首页"""
    return render_template('user.html')


@app.route('/api/join', methods=['POST'])
def join_team():
    """用户加入 Team (新逻辑: 邀请码对应特定 Team)"""
    data = request.json
    email = data.get('email', '').strip()
    key_code = data.get('key_code', '').strip()

    if not email or not key_code:
        return jsonify({"success": False, "error": "请输入邮箱和访问密钥"}), 400

    # 验证密钥
    key_info = AccessKey.get_by_code(key_code)
    if not key_info:
        return jsonify({"success": False, "error": "无效的访问密钥"}), 400

    # 获取或分配 Team
    team = None
    assigned_team_id = key_info.get('team_id')

    if assigned_team_id:
        team = Team.get_by_id(assigned_team_id)
        if team:
            # 检查实际成员数
            members_result = get_team_members(team['access_token'], team['account_id'])
            if members_result['success']:
                members = members_result.get('members', [])
                non_owner_members = [m for m in members if m.get('role') != 'account-owner']
                if len(non_owner_members) >= 4:
                    # 已分配的 Team 已满,释放绑定,重新分配
                    AccessKey.assign_team(key_info['id'], None)
                    team = None
                    assigned_team_id = None
            else:
                # 无法获取成员列表,释放绑定
                AccessKey.assign_team(key_info['id'], None)
                team = None
                assigned_team_id = None
        else:
            # 已分配的 Team 不存在,释放绑定
            AccessKey.assign_team(key_info['id'], None)
            assigned_team_id = None

    if not team:
        available_teams = Team.get_available_teams()
        if not available_teams:
            return jsonify({"success": False, "error": "当前无可用 Team,请联系管理员"}), 400
        team = available_teams[0]
        AccessKey.assign_team(key_info['id'], team['id'])

    # 获取实际成员列表并检查
    members_result = get_team_members(team['access_token'], team['account_id'])
    if not members_result['success']:
        return jsonify({"success": False, "error": f"无法获取成员列表: {members_result.get('error')}"}), 500

    members = members_result.get('members', [])
    non_owner_members = [m for m in members if m.get('role') != 'account-owner']

    if len(non_owner_members) >= 4:
        return jsonify({"success": False, "error": "该 Team 已达到人数上限 (不含队长最多4人)"}), 400

    # 检查该邮箱是否已在 Team 中
    member_emails = [m.get('email') for m in members]
    if email in member_emails:
        return jsonify({"success": False, "error": f"该邮箱已在 {team['name']} 团队中"}), 400

    # 尝试邀请
    result = invite_to_team(
        team['access_token'],
        team['account_id'],
        email,
        team['id']
    )

    if result['success']:
        # 计算过期时间 (如果是临时邀请码) - 使用UTC时间
        temp_expire_at = None
        if key_info['is_temp'] and key_info['temp_hours'] > 0:
            now = datetime.utcnow()
            temp_expire_at = (now + timedelta(hours=key_info['temp_hours'])).strftime('%Y-%m-%d %H:%M:%S')

        # 记录邀请
        Invitation.create(
            team_id=team['id'],
            email=email,
            key_id=key_info['id'],
            invite_id=result.get('invite_id'),
            status='success',
            is_temp=key_info['is_temp'],
            temp_expire_at=temp_expire_at
        )

        # 邀请码使用一次后立即取消，防止重复使用
        AccessKey.cancel(key_info['id'])

        # 更新team的最后邀请时间（实现轮询）
        Team.update_last_invite(team['id'])

        message = f"🎉 成功加入 {team['name']} 团队！\n\n📧 请立即查收邮箱 {email} 的邀请邮件并确认加入。\n\n💡 提示：邮件可能在垃圾箱中，请注意查看。"

        if key_info['is_temp'] and key_info['temp_hours'] > 0:
            message += f"\n\n⏰ 注意：这是一个 {key_info['temp_hours']} 小时临时邀请，到期后如果管理员未确认，将自动踢出。"

        return jsonify({
            "success": True,
            "message": message,
            "team_name": team['name'],
            "email": email
        })
    else:
        # 邀请 API 返回失败，验证是否实际成功
        import time
        time.sleep(2)  # 等待 API 同步
        
        # 1. 检查是否在 pending 列表中
        pending_result = get_pending_invites(team['access_token'], team['account_id'])
        if pending_result['success']:
            pending_emails = [inv.get('email_address', '').lower() for inv in pending_result.get('invites', [])]
            if email.lower() in pending_emails:
                # 实际已成功（在 pending 列表中）
                temp_expire_at = None
                if key_info['is_temp'] and key_info['temp_hours'] > 0:
                    now = datetime.utcnow()
                    temp_expire_at = (now + timedelta(hours=key_info['temp_hours'])).strftime('%Y-%m-%d %H:%M:%S')
                
                # 先删除可能存在的failed记录
                Invitation.delete_by_email(team['id'], email)
                
                Invitation.create(
                    team_id=team['id'],
                    email=email,
                    key_id=key_info['id'],
                    invite_id=None,
                    status='success',
                    is_temp=key_info['is_temp'],
                    temp_expire_at=temp_expire_at
                )
                Team.update_last_invite(team['id'])
                
                message = f"🎉 成功加入 {team['name']} 团队！（验证确认）\n\n📧 请立即查收邮箱 {email} 的邀请邮件并确认加入。\n\n💡 提示：邮件可能在垃圾箱中，请注意查看。"
                if key_info['is_temp'] and key_info['temp_hours'] > 0:
                    message += f"\n\n⏰ 注意：这是一个 {key_info['temp_hours']} 小时临时邀请，到期后如果管理员未确认，将自动踢出。"
                
                return jsonify({
                    "success": True,
                    "message": message,
                    "team_name": team['name'],
                    "email": email,
                    "verified": True
                })
        
        # 2. 检查是否已在成员列表中
        members_result = get_team_members(team['access_token'], team['account_id'])
        if members_result['success']:
            member_emails = [m.get('email', '').lower() for m in members_result.get('members', [])]
            if email.lower() in member_emails:
                # 已经是成员了，先删除可能存在的failed记录
                Invitation.delete_by_email(team['id'], email)
                
                Invitation.create(
                    team_id=team['id'],
                    email=email,
                    key_id=key_info['id'],
                    status='success',
                    is_temp=False,
                    temp_expire_at=None
                )
                Team.update_last_invite(team['id'])
                
                return jsonify({
                    "success": True,
                    "message": f"✅ 您已是 {team['name']} 团队成员！",
                    "team_name": team['name'],
                    "email": email,
                    "already_member": True
                })
        
        # 3. 确实失败
        Invitation.create(
            team_id=team['id'],
            email=email,
            key_id=key_info['id'],
            status='failed'
        )

        return jsonify({
            "success": False,
            "error": f"邀请失败: {result.get('error', '未知错误')}"
        }), 500


# ==================== 管理员端路由 ====================

@app.route('/admin')
def admin_page():
    """管理员页面"""
    if not session.get('is_admin'):
        return render_template('admin_login.html')
    return render_template('admin_new.html')


@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """管理员登录 (带 fail2ban 防护)"""
    data = request.json
    password = data.get('password', '')
    ip_address = request.remote_addr

    # 检查 IP 是否被封禁
    if LoginAttempt.is_blocked(ip_address, max_attempts=5, minutes=30):
        return jsonify({
            "success": False,
            "error": "登录失败次数过多,请 30 分钟后再试"
        }), 429

    if password == ADMIN_PASSWORD:
        # 登录成功,记录
        LoginAttempt.record(ip_address, 'admin', success=True)
        session['is_admin'] = True
        return jsonify({"success": True})
    else:
        # 登录失败,记录
        LoginAttempt.record(ip_address, 'admin', success=False)

        # 获取剩余尝试次数
        failures = LoginAttempt.get_recent_failures(ip_address, minutes=30)
        remaining = 5 - failures

        if remaining > 0:
            return jsonify({
                "success": False,
                "error": f"密码错误,还剩 {remaining} 次尝试机会"
            }), 401
        else:
            return jsonify({
                "success": False,
                "error": "登录失败次数过多,已被封禁 30 分钟"
            }), 429


@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    """管理员登出"""
    session.pop('is_admin', None)
    return jsonify({"success": True})


@app.route('/api/admin/teams', methods=['GET'])
@admin_required
def get_teams():
    """获取所有 Teams (新逻辑: 显示成员数)"""
    teams = Team.get_all()

    # 为每个 Team 添加成员信息
    for team in teams:
        invitations = Invitation.get_by_team(team['id'])
        team['invitations'] = invitations
        team['member_count'] = len(set(inv['email'] for inv in invitations if inv['status'] == 'success'))
        team['available_slots'] = max(0, 4 - team['member_count'])

    return jsonify({"success": True, "teams": teams})


@app.route('/api/admin/teams', methods=['POST'])
@admin_required
def create_team():
    """创建新 Team（从 session JSON）- 支持自动识别并更新已存在的组织"""
    data = request.json

    # 解析 session JSON
    session_data = data.get('session_data')
    if isinstance(session_data, str):
        try:
            session_data = json.loads(session_data)
        except:
            return jsonify({"success": False, "error": "无效的 JSON 格式"}), 400

    name = data.get('name', '').strip()
    if not name:
        # 使用邮箱作为默认名称
        name = session_data.get('user', {}).get('email', 'Unknown Team')

    account_id = session_data.get('account', {}).get('id')
    access_token = session_data.get('accessToken')
    organization_id = session_data.get('account', {}).get('organizationId')
    email = session_data.get('user', {}).get('email')

    if not account_id or not access_token:
        return jsonify({"success": False, "error": "缺少必要的账户信息"}), 400

    try:
        # 检查是否已存在相同的 organization_id
        existing_team = None
        if organization_id:
            existing_team = Team.get_by_organization_id(organization_id)

        if existing_team:
            # 已存在,更新 Token 和其他信息
            Team.update_team_info(
                existing_team['id'],
                name=name,
                account_id=account_id,
                access_token=access_token,
                email=email
            )
            return jsonify({
                "success": True,
                "team_id": existing_team['id'],
                "message": f"检测到已存在的组织 (ID: {organization_id}),已自动更新 Token 和信息",
                "updated": True
            })
        else:
            # 不存在,创建新 Team
            team_id = Team.create(name, account_id, access_token, organization_id, email)
            return jsonify({
                "success": True,
                "team_id": team_id,
                "message": "Team 创建成功",
                "updated": False
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/teams/<int:team_id>', methods=['DELETE'])
@admin_required
def delete_team(team_id):
    """删除 Team"""
    try:
        Team.delete(team_id)
        return jsonify({"success": True, "message": "Team 删除成功"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/teams/delete-expired', methods=['POST'])
@admin_required
def delete_expired_teams():
    """批量删除所有token已过期的teams"""
    try:
        result = Team.delete_expired_teams()
        deleted_count = result['deleted_count']
        deleted_teams = result['deleted_teams']

        if deleted_count > 0:
            team_names = [team['name'] for team in deleted_teams]
            return jsonify({
                "success": True,
                "message": f"成功删除 {deleted_count} 个Token已过期的Team",
                "deleted_count": deleted_count,
                "deleted_teams": team_names
            })
        else:
            return jsonify({
                "success": True,
                "message": "没有Token已过期的Team需要删除",
                "deleted_count": 0
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/teams/<int:team_id>/token', methods=['PUT'])
@admin_required
def update_team_token(team_id):
    """更新 Team 的 Token"""
    data = request.json
    session_data = data.get('session_data')
    
    if isinstance(session_data, str):
        try:
            session_data = json.loads(session_data)
        except:
            return jsonify({"success": False, "error": "无效的 JSON 格式"}), 400
    
    access_token = session_data.get('accessToken')
    if not access_token:
        return jsonify({"success": False, "error": "缺少 accessToken"}), 400
    
    try:
        Team.update_token(team_id, access_token)
        return jsonify({"success": True, "message": "Token 更新成功"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/keys', methods=['GET'])
@admin_required
def get_all_keys():
    """获取所有邀请码"""
    try:
        keys = AccessKey.get_all()
        return jsonify({"success": True, "keys": keys})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/keys', methods=['POST'])
@admin_required
def create_invite_key():
    """创建新的邀请码 (不绑定特定 Team),支持批量生成"""
    data = request.json
    team_id_raw = data.get('team_id')
    team_id = None
    is_temp = data.get('is_temp', False)
    temp_hours = data.get('temp_hours', 24) if is_temp else 0
    count = data.get('count', 1)  # 批量生成数量,默认1个

    try:
        # 验证数量
        if not isinstance(count, int) or count < 1 or count > 100:
            return jsonify({"success": False, "error": "数量必须在 1-100 之间"}), 400

        if team_id_raw not in (None, '', 'null'):
            try:
                team_id = int(team_id_raw)
            except (ValueError, TypeError):
                return jsonify({"success": False, "error": "无效的 team_id"}), 400

            team = Team.get_by_id(team_id)
            if not team:
                return jsonify({"success": False, "error": "Team 不存在"}), 404

        # 批量生成邀请码
        results = []
        for _ in range(count):
            result = AccessKey.create(team_id=team_id, is_temp=is_temp, temp_hours=temp_hours)
            results.append(result)

        # 返回生成的邀请码列表
        return jsonify({
            "success": True,
            "count": count,
            "keys": results,  # 返回完整的key对象
            "message": f"成功生成 {count} 个邀请码" if count > 1 else "邀请码创建成功"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/keys/<int:key_id>', methods=['DELETE'])
@admin_required
def delete_invite_key(key_id):
    """删除邀请码"""
    try:
        AccessKey.delete(key_id)
        return jsonify({"success": True, "message": "邀请码删除成功"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/invitations', methods=['GET'])
@admin_required
def get_invitations():
    """获取所有邀请记录"""
    invitations = Invitation.get_all()
    return jsonify({"success": True, "invitations": invitations})


@app.route('/api/admin/invitations/<int:invitation_id>/confirm', methods=['POST'])
@admin_required
def confirm_invitation(invitation_id):
    """确认邀请 (取消自动踢出)"""
    try:
        Invitation.confirm(invitation_id)
        return jsonify({"success": True, "message": "已确认该邀请,不会自动踢出"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def get_team_members(access_token, account_id):
    """获取 Team 成员列表"""
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

    try:
        response = cf_requests.get(url, headers=headers, impersonate="chrome110")
        if response.status_code == 200:
            data = response.json()
            return {"success": True, "members": data.get('items', [])}
        else:
            return {"success": False, "error": response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_pending_invites(access_token, account_id):
    """获取待处理的邀请列表"""
    url = f"https://chatgpt.com/backend-api/accounts/{account_id}/invites"

    headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
        "authorization": f"Bearer {access_token}",
        "chatgpt-account-id": account_id,
        "origin": "https://chatgpt.com",
        "referer": "https://chatgpt.com/admin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    try:
        response = cf_requests.get(url, headers=headers, impersonate="chrome110")
        if response.status_code == 200:
            data = response.json()
            return {"success": True, "invites": data.get('items', [])}
        else:
            return {"success": False, "error": response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def kick_member(access_token, account_id, user_id):
    """踢出成员"""
    url = f"https://chatgpt.com/backend-api/accounts/{account_id}/users/{user_id}"

    headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
        "authorization": f"Bearer {access_token}",
        "chatgpt-account-id": account_id,
        "origin": "https://chatgpt.com",
        "referer": "https://chatgpt.com/admin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    try:
        response = cf_requests.delete(url, headers=headers, impersonate="chrome110")
        if response.status_code == 200:
            return {"success": True}
        else:
            return {"success": False, "error": response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.route('/api/admin/teams/<int:team_id>/members', methods=['GET'])
@admin_required
def get_members(team_id):
    """获取 Team 成员列表"""
    team = Team.get_by_id(team_id)
    if not team:
        return jsonify({"success": False, "error": "Team 不存在"}), 404

    result = get_team_members(team['access_token'], team['account_id'])

    # 为每个成员添加临时邀请信息
    if result['success']:
        for member in result['members']:
            invitation = Invitation.get_by_user_id(team_id, member['user_id'])
            if invitation:
                member['invitation_id'] = invitation['id']
                member['is_temp'] = invitation['is_temp']
                member['is_confirmed'] = invitation['is_confirmed']
                member['temp_expire_at'] = invitation['temp_expire_at']
            else:
                member['invitation_id'] = None
                member['is_temp'] = False
                member['is_confirmed'] = False
                member['temp_expire_at'] = None

    return jsonify(result)


@app.route('/api/admin/teams/<int:team_id>/members/<user_id>', methods=['DELETE'])
@admin_required
def kick_team_member(team_id, user_id):
    """踢出 Team 成员"""
    team = Team.get_by_id(team_id)
    if not team:
        return jsonify({"success": False, "error": "Team 不存在"}), 404

    # 获取成员信息
    members_result = get_team_members(team['access_token'], team['account_id'])
    if not members_result['success']:
        return jsonify({"success": False, "error": "无法获取成员列表"}), 500

    # 找到要踢的成员
    member = next((m for m in members_result['members'] if m['user_id'] == user_id), None)
    if not member:
        return jsonify({"success": False, "error": "成员不存在"}), 404

    # 执行踢人
    result = kick_member(team['access_token'], team['account_id'], user_id)

    if result['success']:
        # 从invitations表中删除记录，释放位置
        Invitation.delete_by_email(team_id, member.get('email', ''))

        # 记录日志
        KickLog.create(
            team_id=team_id,
            user_id=user_id,
            email=member.get('email', 'unknown'),
            reason='管理员手动踢出',
            success=True
        )
        return jsonify({"success": True, "message": "成员已踢出"})
    else:
        KickLog.create(
            team_id=team_id,
            user_id=user_id,
            email=member.get('email', 'unknown'),
            reason='管理员手动踢出',
            success=False,
            error_message=result.get('error')
        )
        return jsonify({"success": False, "error": result.get('error')}), 500


@app.route('/api/admin/teams/<int:team_id>/invite', methods=['POST'])
@admin_required
def admin_invite_member(team_id):
    """管理员直接邀请成员"""
    data = request.json
    email = data.get('email', '').strip()
    is_temp = data.get('is_temp', False)
    temp_hours = data.get('temp_hours', 24) if is_temp else 0

    if not email:
        return jsonify({"success": False, "error": "请输入邮箱"}), 400

    team = Team.get_by_id(team_id)
    if not team:
        return jsonify({"success": False, "error": "Team 不存在"}), 404

    # 检查 Team 人数是否已满 (检查邀请记录数)
    invited_emails = Invitation.get_all_emails_by_team(team_id)
    if len(invited_emails) >= 4:
        return jsonify({"success": False, "error": "该 Team 已达到人数上限 (4人)"}), 400

    # 检查该邮箱是否已被邀请
    if email in invited_emails:
        return jsonify({"success": False, "error": "该邮箱已被邀请过"}), 400

    # 执行邀请
    result = invite_to_team(team['access_token'], team['account_id'], email, team_id)

    if result['success']:
        # 计算过期时间 - 使用UTC时间
        temp_expire_at = None
        if is_temp and temp_hours > 0:
            now = datetime.utcnow()
            temp_expire_at = (now + timedelta(hours=temp_hours)).strftime('%Y-%m-%d %H:%M:%S')

        # 记录邀请
        Invitation.create(
            team_id=team_id,
            email=email,
            invite_id=result.get('invite_id'),
            status='success',
            is_temp=is_temp,
            temp_expire_at=temp_expire_at
        )

        # 更新team的最后邀请时间（实现轮询）
        Team.update_last_invite(team_id)

        return jsonify({
            "success": True,
            "message": f"已成功邀请 {email}",
            "invite_id": result.get('invite_id')
        })
    else:
        # 邀请 API 返回失败，验证是否实际成功
        import time
        time.sleep(2)  # 等待 API 同步
        
        # 1. 检查是否在 pending 列表中
        pending_result = get_pending_invites(team['access_token'], team['account_id'])
        if pending_result['success']:
            pending_emails = [inv.get('email_address', '').lower() for inv in pending_result.get('invites', [])]
            if email.lower() in pending_emails:
                # 实际已成功（在 pending 列表中），先删除可能存在的failed记录
                Invitation.delete_by_email(team_id, email)
                
                temp_expire_at = None
                if is_temp and temp_hours > 0:
                    now = datetime.utcnow()
                    temp_expire_at = (now + timedelta(hours=temp_hours)).strftime('%Y-%m-%d %H:%M:%S')
                
                Invitation.create(
                    team_id=team_id,
                    email=email,
                    status='success',
                    is_temp=is_temp,
                    temp_expire_at=temp_expire_at
                )
                Team.update_last_invite(team_id)
                
                return jsonify({
                    "success": True,
                    "message": f"已成功邀请 {email}（验证确认）",
                    "verified": True
                })
        
        # 2. 检查是否已在成员列表中
        members_result = get_team_members(team['access_token'], team['account_id'])
        if members_result['success']:
            member_emails = [m.get('email', '').lower() for m in members_result.get('members', [])]
            if email.lower() in member_emails:
                # 已经是成员了，先删除可能存在的failed记录
                Invitation.delete_by_email(team_id, email)
                
                Invitation.create(
                    team_id=team_id,
                    email=email,
                    status='success',
                    is_temp=is_temp,
                    temp_expire_at=None
                )
                Team.update_last_invite(team_id)
                
                return jsonify({
                    "success": True,
                    "message": f"{email} 已是团队成员",
                    "already_member": True
                })
        
        # 3. 确实失败
        Invitation.create(
            team_id=team_id,
            email=email,
            status='failed'
        )
        return jsonify({
            "success": False,
            "error": f"邀请失败: {result.get('error', '未知错误')}"
        }), 500


@app.route('/api/admin/teams/<int:team_id>/kick-by-email', methods=['POST'])
@admin_required
def kick_member_by_email(team_id):
    """通过邮箱踢出成员"""
    data = request.json
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({"success": False, "error": "请输入邮箱"}), 400

    team = Team.get_by_id(team_id)
    if not team:
        return jsonify({"success": False, "error": "Team 不存在"}), 404

    # 获取成员列表
    members_result = get_team_members(team['access_token'], team['account_id'])
    if not members_result['success']:
        return jsonify({"success": False, "error": "无法获取成员列表"}), 500

    # 查找匹配的成员
    member = next((m for m in members_result['members']
                   if m.get('email', '').lower() == email), None)

    if not member:
        # 未找到成员，可能已经离开或拒绝邀请，删除invitations记录释放位置
        deleted = Invitation.delete_by_email(team_id, email)
        if deleted:
            return jsonify({
                "success": True, 
                "message": f"未找到 {email}，但已从邀请记录中删除，释放位置"
            })
        else:
            return jsonify({"success": False, "error": f"未找到邮箱为 {email} 的成员或邀请记录"}), 404

    # 检查是否为所有者
    if member.get('role') == 'account-owner':
        return jsonify({"success": False, "error": "不能踢出团队所有者"}), 400

    user_id = member.get('user_id') or member.get('id')

    # 执行踢人
    result = kick_member(team['access_token'], team['account_id'], user_id)

    if result['success']:
        # 从invitations表中删除记录，释放位置
        Invitation.delete_by_email(team_id, email)

        # 记录日志
        KickLog.create(
            team_id=team_id,
            user_id=user_id,
            email=email,
            reason='管理员通过邮箱手动踢出',
            success=True
        )
        return jsonify({"success": True, "message": f"已成功踢出 {email}"})
    else:
        KickLog.create(
            team_id=team_id,
            user_id=user_id,
            email=email,
            reason='管理员通过邮箱手动踢出',
            success=False,
            error_message=result.get('error')
        )
        return jsonify({"success": False, "error": result.get('error')}), 500


@app.route('/api/admin/invite-auto', methods=['POST'])
@admin_required
def admin_invite_auto():
    """管理员邀请成员(自动分配Team)"""
    data = request.json
    email = data.get('email', '').strip()
    is_temp = data.get('is_temp', False)
    temp_hours = data.get('temp_hours', 24) if is_temp else 0

    if not email:
        return jsonify({"success": False, "error": "请输入邮箱"}), 400

    # 获取可用的Team
    available_teams = Team.get_available_teams()
    if not available_teams:
        return jsonify({"success": False, "error": "当前无可用 Team,请先添加 Team"}), 400

    team = available_teams[0]  # 选择第一个可用的Team

    # 检查该邮箱是否已被邀请到该Team
    invited_emails = Invitation.get_all_emails_by_team(team['id'])
    if email in invited_emails:
        return jsonify({"success": False, "error": f"该邮箱已在 {team['name']} 团队中"}), 400

    # 执行邀请
    result = invite_to_team(team['access_token'], team['account_id'], email, team['id'])

    if result['success']:
        # 计算过期时间 - 使用UTC时间
        temp_expire_at = None
        if is_temp and temp_hours > 0:
            now = datetime.utcnow()
            temp_expire_at = (now + timedelta(hours=temp_hours)).strftime('%Y-%m-%d %H:%M:%S')

        # 记录邀请
        Invitation.create(
            team_id=team['id'],
            email=email,
            invite_id=result.get('invite_id'),
            status='success',
            is_temp=is_temp,
            temp_expire_at=temp_expire_at
        )

        # 更新team的最后邀请时间（实现轮询）
        Team.update_last_invite(team['id'])

        return jsonify({
            "success": True,
            "message": f"已成功邀请 {email} 加入 {team['name']}",
            "team_name": team['name'],
            "invite_id": result.get('invite_id')
        })
    else:
        Invitation.create(
            team_id=team['id'],
            email=email,
            status='failed'
        )
        return jsonify({
            "success": False,
            "error": f"邀请失败: {result.get('error', '未知错误')}"
        }), 500


@app.route('/api/admin/kick-by-email-auto', methods=['POST'])
@admin_required
def kick_member_by_email_auto():
    """通过邮箱踢出成员(自动查找所有Team) - 优化版：优先从数据库查询"""
    data = request.json
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({"success": False, "error": "请输入邮箱"}), 400

    # 性能优化：先从邀请记录中查找该邮箱可能所在的Team
    candidate_team_ids = Invitation.get_teams_by_email(email)

    found_team = None
    found_member = None

    # 优先检查候选Team（有邀请记录的Team）
    if candidate_team_ids:
        for team_id in candidate_team_ids:
            team = Team.get_by_id(team_id)
            if not team:
                continue

            # 获取成员列表
            members_result = get_team_members(team['access_token'], team['account_id'])
            if not members_result['success']:
                continue

            # 查找匹配的成员
            member = next((m for m in members_result['members']
                           if m.get('email', '').lower() == email), None)

            if member:
                found_team = team
                found_member = member
                break

    # 如果候选Team中没找到，再遍历所有Team（兜底逻辑，处理手动添加的成员）
    if not found_team or not found_member:
        teams = Team.get_all()
        if not teams:
            return jsonify({"success": False, "error": "当前没有 Team"}), 404

        # 排除已检查过的Team
        checked_team_ids = set(candidate_team_ids)

        for team in teams:
            if team['id'] in checked_team_ids:
                continue

            # 获取成员列表
            members_result = get_team_members(team['access_token'], team['account_id'])
            if not members_result['success']:
                continue

            # 查找匹配的成员
            member = next((m for m in members_result['members']
                           if m.get('email', '').lower() == email), None)

            if member:
                found_team = team
                found_member = member
                break

    if not found_team or not found_member:
        # 未找到成员，可能已经离开或拒绝邀请，删除invitations记录释放位置
        deleted_count = 0
        teams = Team.get_all()
        for team in teams:
            deleted = Invitation.delete_by_email(team['id'], email)
            if deleted:
                deleted_count += 1

        if deleted_count > 0:
            return jsonify({
                "success": True,
                "message": f"未找到 {email}，但已从 {deleted_count} 个Team的邀请记录中删除，释放位置"
            })
        else:
            return jsonify({"success": False, "error": f"未找到邮箱为 {email} 的成员或邀请记录"}), 404

    # 检查是否为所有者
    if found_member.get('role') == 'account-owner':
        return jsonify({"success": False, "error": "不能踢出团队所有者"}), 400

    user_id = found_member.get('user_id') or found_member.get('id')

    # 执行踢人
    result = kick_member(found_team['access_token'], found_team['account_id'], user_id)

    if result['success']:
        # 从invitations表中删除记录，释放位置
        Invitation.delete_by_email(found_team['id'], email)

        # 记录日志
        KickLog.create(
            team_id=found_team['id'],
            user_id=user_id,
            email=email,
            reason='管理员通过邮箱手动踢出',
            success=True
        )
        return jsonify({
            "success": True,
            "message": f"已成功从 {found_team['name']} 踢出 {email}"
        })
    else:
        KickLog.create(
            team_id=found_team['id'],
            user_id=user_id,
            email=email,
            reason='管理员通过邮箱手动踢出',
            success=False,
            error_message=result.get('error')
        )
        return jsonify({"success": False, "error": result.get('error')}), 500


@app.route('/api/admin/auto-kick/config', methods=['GET'])
@admin_required
def get_auto_kick_config():
    """获取自动踢人配置"""
    config = AutoKickConfig.get()

    if config:
        # 转换为前端需要的格式
        start_time = config.get('start_time', '00:00')
        end_time = config.get('end_time', '23:59')

        # 提取小时
        start_hour = int(start_time.split(':')[0])
        end_hour = int(end_time.split(':')[0])

        config['check_interval'] = config.get('check_interval_min', 300)
        config['run_hours'] = f"{start_hour}-{end_hour}"

    return jsonify({"success": True, "config": config})


@app.route('/api/admin/auto-kick/config', methods=['POST', 'PUT'])
@admin_required
def update_auto_kick_config():
    """更新自动踢人配置"""
    data = request.json

    check_interval = data.get('check_interval', 300)
    run_hours = data.get('run_hours', '0-23')

    try:
        # 解析运行时间段
        if '-' in run_hours:
            start_hour, end_hour = map(int, run_hours.split('-'))
        else:
            start_hour, end_hour = 0, 23

        AutoKickConfig.update(
            enabled=data.get('enabled', True),
            check_interval_min=check_interval,
            check_interval_max=check_interval,
            start_time=f"{start_hour:02d}:00",
            end_time=f"{end_hour:02d}:59"
        )

        # 如果启用了自动检测,启动服务
        if data.get('enabled', True):
            auto_kick_service.start()
        else:
            auto_kick_service.stop()

        return jsonify({"success": True, "message": "配置更新成功"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/auto-kick/logs', methods=['GET'])
@admin_required
def get_kick_logs():
    """获取踢人日志"""
    limit = request.args.get('limit', 100, type=int)
    logs = KickLog.get_all(limit)
    return jsonify({"success": True, "logs": logs})


@app.route('/api/admin/auto-kick/check-now', methods=['POST'])
@admin_required
def check_now():
    """立即执行一次检测（优化版本）"""
    try:
        # 检查是否已有检测任务在运行
        if auto_kick_service.is_checking():
            return jsonify({
                "success": False,
                "error": "检测任务已在运行中，请稍后再试"
            }), 409
        
        # 使用 daemon 线程
        import threading
        thread = threading.Thread(
            target=auto_kick_service._check_and_kick,
            daemon=True
        )
        thread.start()
        
        return jsonify({
            "success": True,
            "message": "检测任务已启动"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/auto-kick/status', methods=['GET'])
@admin_required
def get_kick_status():
    """获取检测任务状态"""
    try:
        status = auto_kick_service.get_status()
        return jsonify({"success": True, "status": status})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/health')
def health():
    """健康检查"""
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    print(f"🚀 ChatGPT Team 自动邀请系统启动")
    print(f"📍 管理员后台: http://{HOST}:{PORT}/admin")
    print(f"📍 用户页面: http://{HOST}:{PORT}/")
    print(f"🔑 管理员密码: {ADMIN_PASSWORD}")
    print(f"⚠️  请在生产环境中修改管理员密码！")

    # 检查自动踢人配置,如果启用则启动服务
    config = AutoKickConfig.get()
    if config and config['enabled']:
        auto_kick_service.start()

    app.run(host=HOST, port=PORT, debug=DEBUG)
