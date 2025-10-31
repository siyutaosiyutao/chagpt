#!/bin/bash

# ChatGPT Team 自动邀请系统 - 一键部署脚本

set -e

echo "🚀 ChatGPT Team 自动邀请系统 - 一键部署"
echo "=========================================="

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  请使用 root 用户或 sudo 运行此脚本"
    exit 1
fi

# 1. 安装依赖
echo ""
echo "📦 步骤 1/6: 安装系统依赖..."
if command -v apt-get &> /dev/null; then
    apt-get update
    apt-get install -y python3 python3-pip
elif command -v yum &> /dev/null; then
    yum install -y python3 python3-pip
else
    echo "❌ 不支持的操作系统"
    exit 1
fi

# 2. 创建项目目录
echo ""
echo "📁 步骤 2/6: 创建项目目录..."
PROJECT_DIR="/opt/chatgpt-team"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# 3. 安装 Python 依赖
echo ""
echo "🐍 步骤 3/6: 安装 Python 依赖..."
pip3 install flask==3.0.0 curl-cffi==0.6.2

# 4. 配置防火墙
echo ""
echo "🔥 步骤 4/6: 配置防火墙..."
if command -v ufw &> /dev/null; then
    ufw allow 5002/tcp
    ufw reload
elif command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=5002/tcp
    firewall-cmd --reload
fi

# 5. 创建 Systemd 服务
echo ""
echo "⚙️  步骤 5/6: 创建系统服务..."
cat > /etc/systemd/system/chatgpt-team.service << 'EOF'
[Unit]
Description=ChatGPT Team Auto Invite Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/chatgpt-team
Environment="ADMIN_PASSWORD=Qq3142016904"
Environment="PORT=5002"
ExecStart=/usr/bin/python3 /opt/chatgpt-team/app_new.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 6. 启动服务
echo ""
echo "🎯 步骤 6/6: 启动服务..."
systemctl daemon-reload
systemctl enable chatgpt-team
systemctl start chatgpt-team

# 等待服务启动
sleep 3

# 检查服务状态
if systemctl is-active --quiet chatgpt-team; then
    echo ""
    echo "=========================================="
    echo "✅ 部署成功！"
    echo "=========================================="
    echo ""
    echo "📍 访问地址："
    echo "   用户页面: http://$(hostname -I | awk '{print $1}'):5002/"
    echo "   管理后台: http://$(hostname -I | awk '{print $1}'):5002/admin"
    echo ""
    echo "🔑 管理员密码: Qq3142016904"
    echo ""
    echo "📊 常用命令："
    echo "   查看状态: systemctl status chatgpt-team"
    echo "   查看日志: journalctl -u chatgpt-team -f"
    echo "   重启服务: systemctl restart chatgpt-team"
    echo "   停止服务: systemctl stop chatgpt-team"
    echo ""
    echo "⚠️  注意："
    echo "   1. 请确保云服务器安全组已开放 5002 端口"
    echo "   2. 建议配置 Nginx 反向代理和 HTTPS"
    echo "   3. 定期备份数据库文件: /opt/chatgpt-team/chatgpt_team.db"
    echo ""
else
    echo ""
    echo "❌ 服务启动失败，请查看日志："
    echo "   journalctl -u chatgpt-team -n 50"
    exit 1
fi
