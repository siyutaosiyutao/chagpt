#!/bin/bash
# 快速诊断服务状态

echo "=========================================="
echo "1. 检查服务状态"
echo "=========================================="
# 使用ps检查进程
ps aux | grep "python.*app_new.py" | grep -v grep

echo ""
echo "=========================================="
echo "2. 检查端口监听"
echo "=========================================="
netstat -tlnp | grep 5002 || ss -tlnp | grep 5002

echo ""
echo "=========================================="
echo "3. 测试API端点（快速测试）"
echo "=========================================="
curl -s -o /dev/null -w "HTTP Status: %{http_code}\nTime: %{time_total}s\n" \
  --max-time 10 \
  http://127.0.0.1:5002/health

echo ""
echo "=========================================="
echo "4. 测试admin/teams端点（可能慢）"
echo "=========================================="
echo "开始测试... (最多等待30秒)"
timeout 30 curl -s -o /dev/null -w "HTTP Status: %{http_code}\nTime: %{time_total}s\n" \
  http://127.0.0.1:5002/api/admin/teams

echo ""
echo "=========================================="
echo "5. 查看最近的日志（如果是systemd服务）"
echo "=========================================="
if command -v journalctl &> /dev/null; then
    journalctl -u chatgpt-team -n 20 --no-pager
else
    echo "journalctl 不可用，请手动查看日志"
fi

echo ""
echo "=========================================="
echo "诊断完成"
echo "=========================================="
