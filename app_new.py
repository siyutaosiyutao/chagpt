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


def invite_to_team(access_token, account_id, email):
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
        # 设置10秒超时，邀请请求可能稍慢
        response = cf_requests.post(url, headers=headers, json=payload, impersonate="chrome110", timeout=10)

        if response.status_code in [200, 201]:
            data = response.json()
            invites = data.get('account_invites', [])
            if invites:
                return {"success": True, "invite_id": invites[0].get('id')}
            return {"success": True}
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

    # 获取所有可用team进行轮询
    available_teams = Team.get_available_teams()
    if not available_teams:
        return jsonify({"success": False, "error": "当前无可用 Team,请联系管理员"}), 400

    # 如果有已分配的team且可用，优先尝试它（按id比较，不是对象引用）
    if team:
        assigned_team_index = next((i for i, t in enumerate(available_teams) if t['id'] == team['id']), None)
        if assigned_team_index is not None:
            # 把已分配的team放到最前面
            assigned_team = available_teams.pop(assigned_team_index)
            available_teams.insert(0, assigned_team)

    last_error = None

    for try_team in available_teams:
        # 获取实际成员列表并检查
        members_result = get_team_members(try_team['access_token'], try_team['account_id'])
        if not members_result['success']:
            last_error = f"无法获取成员列表: {members_result.get('error')}"
            continue  # 尝试下一个team

        members = members_result.get('members', [])
        non_owner_members = [m for m in members if m.get('role') != 'account-owner']

        if len(non_owner_members) >= 4:
            last_error = "该 Team 已达到人数上限"
            continue  # 尝试下一个team

        # 检查该邮箱是否已在 Team 中（邮箱不区分大小写）
        member_emails_lower = [m.get('email', '').lower() for m in members]
        if email.lower() in member_emails_lower:
            last_error = f"该邮箱已在 {try_team['name']} 团队中"
            continue  # 尝试下一个team

        # 尝试邀请
        result = invite_to_team(
            try_team['access_token'],
            try_team['account_id'],
            email
        )

        if result['success']:
            # 邀请成功！
            # 计算过期时间 (如果是临时邀请码)
            temp_expire_at = None
            if key_info['is_temp'] and key_info['temp_hours'] > 0:
                beijing_tz = pytz.timezone('Asia/Shanghai')
                now = datetime.now(beijing_tz)
                temp_expire_at = (now + timedelta(hours=key_info['temp_hours'])).strftime('%Y-%m-%d %H:%M:%S')

            # 记录邀请
            Invitation.create(
                team_id=try_team['id'],
                email=email,
                key_id=key_info['id'],
                invite_id=result.get('invite_id'),
                status='success',
                is_temp=key_info['is_temp'],
                temp_expire_at=temp_expire_at
            )

            # 更新team的最后邀请时间（实现轮询）
            Team.update_last_invite(try_team['id'])

            # 更新邀请码绑定的team
            AccessKey.assign_team(key_info['id'], try_team['id'])

            message = f"成功加入 {try_team['name']} 团队！请立即查收邮箱 {email} 的邀请邮件并确认加入。提示：邮件可能在垃圾箱中。"

            if key_info['is_temp'] and key_info['temp_hours'] > 0:
                message += f" 注意：这是 {key_info['temp_hours']} 小时临时邀请，到期后如果管理员未确认将自动踢出。"

            return jsonify({
                "success": True,
                "message": message,
                "team_name": try_team['name'],
                "email": email
            })
        else:
            # 这个team邀请失败，记录错误，继续尝试下一个
            last_error = result.get('error', '未知错误')
            Invitation.create(
                team_id=try_team['id'],
                email=email,
                key_id=key_info['id'],
                status='failed'
            )
            continue  # 尝试下一个team

    # 所有team都尝试失败了
    return jsonify({
        "success": False,
        "error": f"所有 Team 邀请均失败，最后错误: {last_error}"
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
    """获取所有 Teams (快速模式: 只显示基本信息，不检测token)"""
    # 添加skip_token_check参数，允许跳过token检测
    skip_token_check = request.args.get('skip_token_check', 'true').lower() == 'true'

    teams = Team.get_all()

    # 为每个 Team 添加成员信息
    for team in teams:
        invitations = Invitation.get_by_team(team['id'])
        team['invitations'] = invitations
        team['member_count'] = len(set(inv['email'] for inv in invitations if inv['status'] == 'success'))
        team['available_slots'] = max(0, 4 - team['member_count'])

        if skip_token_check:
            # 快速模式：不检测token，设置为未知状态
            team['token_valid'] = None
            team['token_status'] = 'unknown'
            team['status_type'] = 'unknown'
            team['actual_member_count'] = None
        else:
            # 完整模式：检测token是否有效（可能很慢）
            token_check = get_team_members(team['access_token'], team['account_id'])
            if token_check['success']:
                team['token_valid'] = True
                team['token_status'] = 'active'
                team['status_type'] = 'success'
                # 获取实际成员数
                actual_members = token_check.get('members', [])
                team['actual_member_count'] = len([m for m in actual_members if m.get('role') != 'account-owner'])
            else:
                team['token_valid'] = False
                team['token_status'] = token_check.get('status', 'error')  # unauthorized/banned/rate_limited/error
                team['status_type'] = token_check.get('status', 'error')
                team['token_error'] = token_check.get('error', '未知错误')
                team['status_code'] = token_check.get('status_code', 0)
                team['actual_member_count'] = 0

    return jsonify({"success": True, "teams": teams})


@app.route('/api/admin/teams/<int:team_id>/check-token', methods=['GET'])
@admin_required
def check_team_token(team_id):
    """检测单个Team的token状态（按需检测）"""
    team = Team.get_by_id(team_id)
    if not team:
        return jsonify({"success": False, "error": "Team 不存在"}), 404

    # 检测token是否有效
    token_check = get_team_members(team['access_token'], team['account_id'])

    if token_check['success']:
        actual_members = token_check.get('members', [])
        return jsonify({
            "success": True,
            "token_valid": True,
            "token_status": "active",
            "status_type": "success",
            "actual_member_count": len([m for m in actual_members if m.get('role') != 'account-owner'])
        })
    else:
        return jsonify({
            "success": True,
            "token_valid": False,
            "token_status": token_check.get('status', 'error'),
            "status_type": token_check.get('status', 'error'),
            "token_error": token_check.get('error', '未知错误'),
            "status_code": token_check.get('status_code', 0),
            "actual_member_count": 0
        })


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
    """获取 Team 成员列表（简化版：只区分有效/失效）"""
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
        # 设置5秒超时，避免卡住整个请求
        response = cf_requests.get(url, headers=headers, impersonate="chrome110", timeout=5)

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "members": data.get('account_users', []),
                "status_code": 200,
                "status": "active"
            }
        else:
            # 所有非200状态码都视为Token失效
            return {
                "success": False,
                "error": "Token已失效",
                "status_code": response.status_code,
                "status": "invalid"
            }
    except Exception as e:
        return {
            "success": False,
            "error": "Token已失效",
            "status_code": 0,
            "status": "invalid"
        }


def kick_member(access_token, account_id, user_id):
    """踢出成员（增强版：详细错误处理）"""
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
        # 设置10秒超时
        response = cf_requests.delete(url, headers=headers, impersonate="chrome110", timeout=10)

        if response.status_code == 200:
            return {"success": True, "status_code": 200}
        elif response.status_code == 401:
            return {"success": False, "error": "Token已失效", "status_code": 401, "status": "unauthorized"}
        elif response.status_code == 403:
            return {"success": False, "error": "账号已被封禁或无权限", "status_code": 403, "status": "banned"}
        elif response.status_code == 404:
            return {"success": False, "error": "成员不存在", "status_code": 404, "status": "not_found"}
        elif response.status_code == 429:
            return {"success": False, "error": "请求过于频繁", "status_code": 429, "status": "rate_limited"}
        else:
            return {
                "success": False,
                "error": f"未知错误 (HTTP {response.status_code})",
                "status_code": response.status_code,
                "detail": response.text
            }
    except Exception as e:
        return {"success": False, "error": f"网络错误: {str(e)}", "status_code": 0}


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
            # 安全获取user_id
            user_id = member.get('user_id') or member.get('id')
            invitation = Invitation.get_by_user_id(team_id, user_id) if user_id else None

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

            # 确保member有user_id字段（统一字段名）
            if 'user_id' not in member and 'id' in member:
                member['user_id'] = member['id']

    return jsonify(result)


@app.route('/api/admin/teams/<int:team_id>/members/<user_id>', methods=['DELETE'])
@admin_required
def kick_team_member(team_id, user_id):
    """踢出 Team 成员（标记删除，由自动踢人服务处理）"""
    team = Team.get_by_id(team_id)
    if not team:
        return jsonify({"success": False, "error": "Team 不存在"}), 404

    # 从invitations表查找该user_id的记录
    invitation = Invitation.get_by_user_id(team_id, user_id)
    if not invitation:
        return jsonify({"success": False, "error": "该成员不在邀请列表中"}), 404

    email = invitation['email']

    # 从invitations表中删除记录（标记删除）
    Invitation.delete_by_user_id(team_id, user_id)

    # 记录日志
    KickLog.create(
        team_id=team_id,
        user_id=user_id,
        email=email,
        reason='管理员标记删除，等待自动踢出',
        success=True
    )

    message = f"已从邀请列表中移除 {email}，自动踢人服务将在下次检测时踢出该成员"
    return jsonify({"success": True, "message": message})


@app.route('/api/admin/teams/<int:team_id>/invite', methods=['POST'])
@admin_required
def admin_invite_member(team_id):
    """管理员直接邀请成员"""
    data = request.json
    email = data.get('email', '').strip().lower()  # 统一转为小写
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

    # 检查该邮箱是否已被邀请（大小写不敏感）
    invited_emails_lower = [e.lower() for e in invited_emails]
    if email in invited_emails_lower:
        return jsonify({"success": False, "error": "该邮箱已被邀请过"}), 400

    # 执行邀请
    result = invite_to_team(team['access_token'], team['account_id'], email)

    if result['success']:
        # 计算过期时间
        temp_expire_at = None
        if is_temp and temp_hours > 0:
            beijing_tz = pytz.timezone('Asia/Shanghai')
            now = datetime.now(beijing_tz)
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

    # 从invitations表查找该email的记录
    invitation = Invitation.get_by_team_and_email(team_id, email)
    if not invitation:
        return jsonify({"success": False, "error": f"邮箱 {email} 不在邀请列表中"}), 404

    user_id = invitation.get('user_id', '')

    # 从invitations表中删除记录（标记删除）
    Invitation.delete_by_email(team_id, email)

    # 记录日志
    KickLog.create(
        team_id=team_id,
        user_id=user_id,
        email=email,
        reason='管理员标记删除，等待自动踢出',
        success=True
    )

    message = f"已从邀请列表中移除 {email}，自动踢人服务将在下次检测时踢出该成员"
    return jsonify({"success": True, "message": message})


@app.route('/api/admin/invite-auto', methods=['POST'])
@admin_required
def admin_invite_auto():
    """管理员邀请成员(自动分配Team，失败自动重试下一个)"""
    data = request.json
    email = data.get('email', '').strip().lower()  # 统一转为小写
    is_temp = data.get('is_temp', False)
    temp_hours = data.get('temp_hours', 24) if is_temp else 0

    if not email:
        return jsonify({"success": False, "error": "请输入邮箱"}), 400

    # 获取所有可用的Team
    available_teams = Team.get_available_teams()
    if not available_teams:
        return jsonify({"success": False, "error": "当前无可用 Team,请先添加 Team"}), 400

    # 轮询所有可用team直到成功
    last_error = None

    for team in available_teams:
        # 检查该邮箱是否已被邀请到该Team（大小写不敏感）
        invited_emails = Invitation.get_all_emails_by_team(team['id'])
        invited_emails_lower = [e.lower() for e in invited_emails]
        if email in invited_emails_lower:
            last_error = f"该邮箱已在 {team['name']} 团队中"
            continue  # 尝试下一个team

        # 执行邀请
        result = invite_to_team(team['access_token'], team['account_id'], email)

        if result['success']:
            # 邀请成功！
            # 计算过期时间
            temp_expire_at = None
            if is_temp and temp_hours > 0:
                beijing_tz = pytz.timezone('Asia/Shanghai')
                now = datetime.now(beijing_tz)
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
            # 这个team邀请失败，记录错误，继续尝试下一个
            last_error = result.get('error', '未知错误')
            Invitation.create(
                team_id=team['id'],
                email=email,
                status='failed'
            )
            continue  # 尝试下一个team

    # 所有team都尝试失败了
    return jsonify({
        "success": False,
        "error": f"所有 Team 邀请均失败，最后错误: {last_error}"
    }), 500


@app.route('/api/admin/kick-by-email-auto', methods=['POST'])
@admin_required
def kick_member_by_email_auto():
    """通过邮箱踢出成员(自动查找所有Team)"""
    data = request.json
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({"success": False, "error": "请输入邮箱"}), 400

    # 获取所有Team
    teams = Team.get_all()
    if not teams:
        return jsonify({"success": False, "error": "当前没有 Team"}), 404

    # 遍历所有Team，在invitations表中查找该邮箱
    found_team = None
    found_invitation = None

    for team in teams:
        invitation = Invitation.get_by_team_and_email(team['id'], email)
        if invitation:
            found_team = team
            found_invitation = invitation
            break

    if not found_team or not found_invitation:
        return jsonify({"success": False, "error": f"邮箱 {email} 不在任何Team的邀请列表中"}), 404

    user_id = found_invitation.get('user_id', '')

    # 从invitations表中删除记录（标记删除）
    Invitation.delete_by_email(found_team['id'], email)

    # 记录日志
    KickLog.create(
        team_id=found_team['id'],
        user_id=user_id,
        email=email,
        reason='管理员标记删除，等待自动踢出',
        success=True
    )

    message = f"已从 {found_team['name']} 的邀请列表中移除 {email}，自动踢人服务将在下次检测时踢出该成员"
    return jsonify({"success": True, "message": message})


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
    """立即执行一次检测"""
    try:
        # 在新线程中执行检测
        import threading
        thread = threading.Thread(target=auto_kick_service._check_and_kick)
        thread.start()
        return jsonify({"success": True, "message": "检测任务已启动"})
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
