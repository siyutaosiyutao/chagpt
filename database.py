"""
数据库模型
"""
import sqlite3
import secrets
from datetime import datetime
from contextlib import contextmanager
from config import DATABASE_PATH, MAX_KEYS_PER_TEAM, KEY_LENGTH


@contextmanager
def get_db():
    """数据库连接上下文管理器"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """初始化数据库"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Teams 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                account_id TEXT NOT NULL,
                access_token TEXT NOT NULL,
                organization_id TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Access Keys 表 (重构: 每个邀请码对应一个 Team)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER,
                key_code TEXT NOT NULL UNIQUE,
                is_temp BOOLEAN DEFAULT 0,
                temp_hours INTEGER DEFAULT 0,
                is_cancelled BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE SET NULL
            )
        ''')
        
        # Invitations 表（记录所有邀请）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invitations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                key_id INTEGER,
                email TEXT NOT NULL,
                user_id TEXT,
                invite_id TEXT,
                status TEXT DEFAULT 'pending',
                is_temp BOOLEAN DEFAULT 0,
                temp_expire_at TIMESTAMP,
                is_confirmed BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE,
                FOREIGN KEY (key_id) REFERENCES access_keys (id) ON DELETE SET NULL
            )
        ''')

        # 自动检测配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auto_kick_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enabled BOOLEAN DEFAULT 0,
                check_interval_min INTEGER DEFAULT 90,
                check_interval_max INTEGER DEFAULT 120,
                start_time TEXT DEFAULT '09:00',
                end_time TEXT DEFAULT '22:00',
                timezone TEXT DEFAULT 'Asia/Shanghai',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 插入默认配置（如果不存在）
        cursor.execute('SELECT COUNT(*) FROM auto_kick_config')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO auto_kick_config (enabled, check_interval_min, check_interval_max, start_time, end_time)
                VALUES (0, 90, 120, '09:00', '22:00')
            ''')

        # 踢人日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kick_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                email TEXT NOT NULL,
                reason TEXT,
                success BOOLEAN DEFAULT 1,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE
            )
        ''')

        # 登录失败记录表 (fail2ban)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                username TEXT,
                success BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建索引加速查询
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_login_attempts_ip
            ON login_attempts(ip_address, created_at)
        ''')

        conn.commit()


class Team:
    @staticmethod
    def create(name, account_id, access_token, organization_id=None, email=None):
        """创建新 Team（不自动生成密钥,需要手动生成）"""
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO teams (name, account_id, access_token, organization_id, email)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, account_id, access_token, organization_id, email))
            team_id = cursor.lastrowid

            return team_id
    
    @staticmethod
    def get_all():
        """获取所有 Teams"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM teams ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_by_id(team_id):
        """根据 ID 获取 Team"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM teams WHERE id = ?', (team_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_by_organization_id(organization_id):
        """根据 organization_id 获取 Team"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM teams WHERE organization_id = ?', (organization_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def update_token(team_id, access_token):
        """更新 Team 的 access_token"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE teams
                SET access_token = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (access_token, team_id))

    @staticmethod
    def update_team_info(team_id, name=None, account_id=None, access_token=None, email=None):
        """更新 Team 的完整信息"""
        with get_db() as conn:
            cursor = conn.cursor()

            updates = []
            params = []

            if name is not None:
                updates.append('name = ?')
                params.append(name)
            if account_id is not None:
                updates.append('account_id = ?')
                params.append(account_id)
            if access_token is not None:
                updates.append('access_token = ?')
                params.append(access_token)
            if email is not None:
                updates.append('email = ?')
                params.append(email)

            if updates:
                updates.append('updated_at = CURRENT_TIMESTAMP')
                params.append(team_id)
                sql = f"UPDATE teams SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(sql, params)

    @staticmethod
    def delete(team_id):
        """删除 Team"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM teams WHERE id = ?', (team_id,))

    @staticmethod
    def get_available_teams():
        """获取所有未满员的 Team (按成员数从多到少排序,优先填满快满的 Team)"""
        teams = Team.get_all()
        available = []
        for team in teams:
            invitations = Invitation.get_by_team(team['id'])
            member_count = len({inv['email'] for inv in invitations if inv['status'] == 'success'})
            if member_count < 4:
                team_copy = dict(team)
                team_copy['member_count'] = member_count
                available.append(team_copy)

        available.sort(key=lambda item: (-item['member_count'], item['id']))
        return available


class AccessKey:
    @staticmethod
    def create(team_id=None, is_temp=False, temp_hours=0):
        """创建新的邀请码, team_id 可选 (将在使用时分配)"""
        key_code = secrets.token_urlsafe(KEY_LENGTH)
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO access_keys (team_id, key_code, is_temp, temp_hours)
                VALUES (?, ?, ?, ?)
            ''', (team_id, key_code, is_temp, temp_hours))
            return {
                'id': cursor.lastrowid,
                'key_code': key_code
            }

    @staticmethod
    def assign_team(key_id, team_id):
        """在邀请码首次使用时绑定 Team"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE access_keys
                SET team_id = ?
                WHERE id = ?
            ''', (team_id, key_id))

    @staticmethod
    def get_all():
        """获取所有密钥"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT ak.*,
                       t.name as team_name,
                       (SELECT COUNT(*) FROM invitations WHERE key_id = ak.id AND status = 'success') as usage_count
                FROM access_keys ak
                LEFT JOIN teams t ON ak.team_id = t.id
                WHERE ak.is_cancelled = 0
                ORDER BY ak.created_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_by_code(key_code):
        """根据密钥获取信息"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT ak.*,
                       (SELECT COUNT(*) FROM invitations WHERE key_id = ak.id) as usage_count
                FROM access_keys ak
                WHERE ak.key_code = ? AND ak.is_cancelled = 0
            ''', (key_code,))
            row = cursor.fetchone()
            return dict(row) if row else None



    @staticmethod
    def cancel(key_id):
        """取消邀请码"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE access_keys
                SET is_cancelled = 1
                WHERE id = ?
            ''', (key_id,))

    @staticmethod
    def delete(key_id):
        """删除邀请码"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM access_keys WHERE id = ?', (key_id,))


class Invitation:
    @staticmethod
    def create(team_id, email, key_id=None, user_id=None, invite_id=None,
               status='pending', is_temp=False, temp_expire_at=None):
        """创建邀请记录"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO invitations (team_id, key_id, email, user_id, invite_id,
                                        status, is_temp, temp_expire_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (team_id, key_id, email, user_id, invite_id, status, is_temp, temp_expire_at))
            return cursor.lastrowid

    @staticmethod
    def get_by_team(team_id):
        """获取 Team 的所有邀请"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM invitations
                WHERE team_id = ?
                ORDER BY created_at DESC
            ''', (team_id,))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_all():
        """获取所有邀请"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT i.*, t.name as team_name
                FROM invitations i
                JOIN teams t ON i.team_id = t.id
                ORDER BY i.created_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_all_emails_by_team(team_id):
        """获取 Team 的所有已邀请邮箱列表"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT email FROM invitations
                WHERE team_id = ? AND status = 'success'
            ''', (team_id,))
            return [row[0] for row in cursor.fetchall()]

    @staticmethod
    def get_temp_expired():
        """获取所有已过期的临时邀请"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM invitations
                WHERE is_temp = 1
                  AND is_confirmed = 0
                  AND temp_expire_at < datetime('now')
                ORDER BY temp_expire_at
            ''')
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def confirm(invitation_id):
        """确认邀请(管理员取消自动踢出)"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE invitations
                SET is_confirmed = 1
                WHERE id = ?
            ''', (invitation_id,))

    @staticmethod
    def update_user_id(invitation_id, user_id):
        """更新邀请的 user_id"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE invitations
                SET user_id = ?
                WHERE id = ?
            ''', (user_id, invitation_id,))


class AutoKickConfig:
    @staticmethod
    def get():
        """获取配置"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM auto_kick_config LIMIT 1')
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def update(enabled=None, check_interval_min=None, check_interval_max=None,
               start_time=None, end_time=None):
        """更新配置"""
        with get_db() as conn:
            cursor = conn.cursor()

            updates = []
            params = []

            if enabled is not None:
                updates.append('enabled = ?')
                params.append(enabled)
            if check_interval_min is not None:
                updates.append('check_interval_min = ?')
                params.append(check_interval_min)
            if check_interval_max is not None:
                updates.append('check_interval_max = ?')
                params.append(check_interval_max)
            if start_time is not None:
                updates.append('start_time = ?')
                params.append(start_time)
            if end_time is not None:
                updates.append('end_time = ?')
                params.append(end_time)

            if updates:
                updates.append('updated_at = CURRENT_TIMESTAMP')
                sql = f"UPDATE auto_kick_config SET {', '.join(updates)}"
                cursor.execute(sql, params)


class KickLog:
    @staticmethod
    def create(team_id, user_id, email, reason, success=True, error_message=None):
        """创建踢人日志"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO kick_logs (team_id, user_id, email, reason, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (team_id, user_id, email, reason, success, error_message))
            return cursor.lastrowid

    @staticmethod
    def get_all(limit=100):
        """获取所有踢人日志"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT k.*, t.name as team_name
                FROM kick_logs k
                JOIN teams t ON k.team_id = t.id
                ORDER BY k.created_at DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_by_team(team_id, limit=50):
        """获取指定 Team 的踢人日志"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM kick_logs
                WHERE team_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (team_id, limit))
            return [dict(row) for row in cursor.fetchall()]


class LoginAttempt:
    """登录尝试记录 (fail2ban)"""

    @staticmethod
    def record(ip_address, username=None, success=False):
        """记录登录尝试"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO login_attempts (ip_address, username, success)
                VALUES (?, ?, ?)
            ''', (ip_address, username, success))

    @staticmethod
    def get_recent_failures(ip_address, minutes=30):
        """获取最近 N 分钟内的失败次数"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM login_attempts
                WHERE ip_address = ?
                  AND success = 0
                  AND created_at > datetime('now', '-' || ? || ' minutes')
            ''', (ip_address, minutes))
            row = cursor.fetchone()
            return row[0] if row else 0

    @staticmethod
    def is_blocked(ip_address, max_attempts=5, minutes=30):
        """检查 IP 是否被封禁"""
        failures = LoginAttempt.get_recent_failures(ip_address, minutes)
        return failures >= max_attempts

    @staticmethod
    def cleanup_old_records(days=7):
        """清理旧记录"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM login_attempts
                WHERE created_at < datetime('now', '-' || ? || ' days')
            ''', (days,))
