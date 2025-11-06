#!/bin/bash

# 更新生产服务器代码

echo "🚀 开始更新生产服务器..."

ssh root@159.65.13.224 << 'ENDSSH'
cd /root/chagpt

echo "📥 拉取最新代码..."
git fetch origin
git checkout claude/review-project-issues-011CUmsPFThjEMDHWtb9TsCD
git pull origin claude/review-project-issues-011CUmsPFThjEMDHWtb9TsCD

echo "🔄 重启服务..."
sudo systemctl restart chatgpt-invite.service

echo "⏳ 等待服务启动..."
sleep 3

echo ""
echo "✅ 服务状态："
sudo systemctl status chatgpt-invite.service --no-pager -l | head -n 20

echo ""
echo "📊 最近的日志："
sudo journalctl -u chatgpt-invite.service -n 30 --no-pager

ENDSSH

echo ""
echo "✅ 更新完成！"
echo "🌐 访问: http://159.65.13.224:5002/admin"
