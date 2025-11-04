#!/bin/bash

# ChatGPT Team 功能修复更新脚本
# 修复: Team轮询邀请 + 踢人后释放位置
# 此次更新保留所有现有数据，只添加一个新字段

set -e

echo "=========================================="
echo "🔧 ChatGPT Team 功能修复更新"
echo "=========================================="
echo ""
echo "本次修复内容:"
echo "  1. ✅ Team轮询邀请机制 - 自动切换team"
echo "  2. ✅ 邀请失败后team排到后面"
echo "  3. ✅ 踢人后释放位置 - 正确清理记录"
echo "  4. ✅ 修复API字段不一致问题"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_FILE="chatgpt_team.db"
BRANCH_NAME="claude/review-project-issues-011CUmsPFThjEMDHWtb9TsCD"

# 创建备份目录
mkdir -p ${BACKUP_DIR}

echo "📋 步骤 1/8: 检查当前环境"
echo "----------------------------------------"

if [ ! -f "app_new.py" ]; then
    echo -e "${RED}❌ 错误: 未找到 app_new.py${NC}"
    exit 1
fi

if [ ! -f "${DB_FILE}" ]; then
    echo -e "${RED}❌ 错误: 未找到数据库文件${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 环境检查通过${NC}"

echo ""
echo "📦 步骤 2/8: 备份数据库"
echo "----------------------------------------"

DB_BACKUP="${BACKUP_DIR}/chatgpt_team_${TIMESTAMP}.db"
cp ${DB_FILE} ${DB_BACKUP}
echo -e "${GREEN}✅ 数据库已备份到: ${DB_BACKUP}${NC}"

echo ""
echo "🔄 步骤 3/8: 停止服务"
echo "----------------------------------------"

# 停止systemd服务（如果存在）
if systemctl is-active --quiet chatgpt-team 2>/dev/null; then
    echo "🛑 停止 systemd 服务..."
    systemctl stop chatgpt-team
    echo -e "${GREEN}✅ systemd 服务已停止${NC}"
elif pgrep -f "app_new.py" > /dev/null; then
    echo "🛑 停止现有进程..."
    pkill -f "app_new.py" || true
    sleep 2
    echo -e "${GREEN}✅ 进程已停止${NC}"
else
    echo -e "${YELLOW}⚠️  未发现运行中的服务${NC}"
fi

echo ""
echo "📥 步骤 4/8: 拉取最新代码"
echo "----------------------------------------"

if [ ! -d ".git" ]; then
    echo -e "${RED}❌ 错误: 不是 git 仓库${NC}"
    exit 1
fi

# 检查当前分支
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "当前分支: ${CURRENT_BRANCH}"

# 方案1: 如果修复已合并到main，从main拉取
echo ""
echo "请选择更新方式:"
echo "  1) 从main分支拉取 (如果修复已合并到main)"
echo "  2) 从修复分支拉取: ${BRANCH_NAME}"
echo ""
read -p "请选择 [1/2] (默认: 2): " pull_choice
pull_choice=${pull_choice:-2}

if [ "$pull_choice" = "1" ]; then
    echo "🔄 从main分支拉取..."
    git fetch origin
    git checkout main
    git pull origin main
else
    echo "🔄 从修复分支拉取..."
    git fetch origin
    git checkout ${BRANCH_NAME} || git checkout -b ${BRANCH_NAME} origin/${BRANCH_NAME}
    git pull origin ${BRANCH_NAME}
fi

echo -e "${GREEN}✅ 代码更新完成${NC}"

echo ""
echo "📦 步骤 5/8: 更新依赖"
echo "----------------------------------------"

if [ -f "requirements_new.txt" ]; then
    echo "📦 安装 Python 依赖..."
    pip3 install -r requirements_new.txt --quiet
    echo -e "${GREEN}✅ 依赖安装完成${NC}"
else
    echo -e "${YELLOW}⚠️  未找到 requirements_new.txt${NC}"
fi

echo ""
echo "🗄️  步骤 6/8: 数据库迁移"
echo "----------------------------------------"

echo "检查数据库是否需要迁移..."

# 检查last_invite_at字段是否存在
HAS_NEW_FIELD=$(python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('chatgpt_team.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(teams)")
columns = [col[1] for col in cursor.fetchall()]
print('1' if 'last_invite_at' in columns else '0')
conn.close()
EOF
)

if [ "$HAS_NEW_FIELD" = "0" ]; then
    echo "需要添加新字段..."
    if [ -f "migrate_add_last_invite_at.py" ]; then
        echo "🔄 运行数据库迁移脚本..."
        python3 migrate_add_last_invite_at.py
        echo -e "${GREEN}✅ 数据库迁移完成${NC}"
    else
        echo -e "${RED}❌ 错误: 未找到迁移脚本 migrate_add_last_invite_at.py${NC}"
        echo "手动添加字段..."
        python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('chatgpt_team.db')
cursor = conn.cursor()
cursor.execute("ALTER TABLE teams ADD COLUMN last_invite_at TIMESTAMP")
conn.commit()
conn.close()
print("✅ 手动添加字段成功")
EOF
    fi
else
    echo -e "${GREEN}✅ 数据库结构已是最新${NC}"
fi

echo ""
echo "🔍 步骤 7/8: 验证数据完整性"
echo "----------------------------------------"

python3 << 'EOF'
import sqlite3

conn = sqlite3.connect('chatgpt_team.db')
cursor = conn.cursor()

# 检查teams表
cursor.execute("SELECT COUNT(*) FROM teams")
team_count = cursor.fetchone()[0]
print(f"✅ Teams 数量: {team_count}")

# 检查invitations表
cursor.execute("SELECT COUNT(*) FROM invitations WHERE status='success'")
invitation_count = cursor.fetchone()[0]
print(f"✅ 成功邀请数: {invitation_count}")

# 检查access_keys表
cursor.execute("SELECT COUNT(*) FROM access_keys WHERE is_cancelled=0")
key_count = cursor.fetchone()[0]
print(f"✅ 有效邀请码: {key_count}")

# 验证新字段
cursor.execute("PRAGMA table_info(teams)")
columns = [col[1] for col in cursor.fetchall()]
if 'last_invite_at' in columns:
    print(f"✅ 新字段 last_invite_at 已添加")
else:
    print(f"❌ 警告: 新字段未添加成功")

conn.close()
EOF

echo ""
echo "🚀 步骤 8/8: 启动服务"
echo "----------------------------------------"

# 检查是否使用systemd
if [ -f "/etc/systemd/system/chatgpt-team.service" ]; then
    echo "🚀 使用 systemd 启动服务..."
    systemctl daemon-reload
    systemctl start chatgpt-team
    sleep 3

    if systemctl is-active --quiet chatgpt-team; then
        echo -e "${GREEN}✅ 服务启动成功!${NC}"
        echo ""
        echo "📊 查看服务状态:"
        systemctl status chatgpt-team --no-pager -l
    else
        echo -e "${RED}❌ 服务启动失败${NC}"
        echo "查看日志: journalctl -u chatgpt-team -n 50"
        exit 1
    fi
else
    echo "🚀 使用 nohup 启动服务..."
    nohup python3 app_new.py > app.log 2>&1 &
    sleep 3

    if pgrep -f "app_new.py" > /dev/null; then
        echo -e "${GREEN}✅ 服务启动成功!${NC}"
        echo "进程 ID: $(pgrep -f app_new.py)"
        echo "查看日志: tail -f app.log"
    else
        echo -e "${RED}❌ 服务启动失败${NC}"
        echo "查看日志: tail -f app.log"
        exit 1
    fi
fi

echo ""
echo "=========================================="
echo -e "${GREEN}🎉 更新完成!${NC}"
echo "=========================================="
echo ""
echo "✅ 修复内容已应用:"
echo "   1. Team轮询邀请 - 按最后使用时间自动切换"
echo "   2. 邀请失败处理 - 失败team自动排到后面"
echo "   3. 踢人后释放位置 - 正确从数据库删除记录"
echo "   4. API字段修复 - 统一使用account_users"
echo ""
echo "📚 备份文件:"
echo "   数据库备份: ${DB_BACKUP}"
echo ""
echo "⚠️  重要提示:"
echo "   - 所有现有数据都已保留"
echo "   - 仅添加了 last_invite_at 字段"
echo "   - Team轮询功能已自动启用"
echo "   - 踢人后现在会正确释放位置"
echo ""
echo "🔗 访问地址:"
if systemctl is-active --quiet chatgpt-team 2>/dev/null; then
    echo "   http://$(hostname -I | awk '{print $1}'):5002/admin"
else
    echo "   http://$(hostname -I | awk '{print $1}'):5002/admin"
fi
echo ""
