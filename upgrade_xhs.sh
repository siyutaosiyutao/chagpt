#!/bin/bash

# 小红书自动发货功能 - 平滑升级脚本
# 本脚本用于在现有系统上增量部署XHS订单同步功能

echo "========================================"
echo "小红书自动发货功能 - 增量部署"
echo "========================================"
echo ""

# 检查是否在项目目录
if [ ! -f "app_new.py" ]; then
    echo "❌ 错误：请在项目根目录执行此脚本"
    exit 1
fi

echo "📦 步骤 1/5: 备份现有代码..."
timestamp=$(date +%Y%m%d_%H%M%S)
backup_dir="backup_${timestamp}"
mkdir -p "$backup_dir"
cp -r *.py templates static "$backup_dir/" 2>/dev/null
cp chatgpt_team.db "$backup_dir/" 2>/dev/null || echo "  数据库文件不存在，跳过备份"
echo "✅ 备份完成: $backup_dir"

echo ""
echo "📥 步骤 2/5: 拉取最新代码..."
git stash  # 暂存本地修改
git pull origin main
git stash pop 2>/dev/null  # 恢复本地修改（如果有）
echo "✅ 代码已更新"

echo ""
echo "📦 步骤 3/5: 安装新增依赖..."
pip3 install -r requirements_new.txt --upgrade
echo "✅ 依赖已安装"

echo ""
echo "🌐 步骤 4/5: 配置 Chrome 和 ChromeDriver..."

# 检查是否已安装 Chrome
if command -v google-chrome &> /dev/null || [ -f "/usr/bin/google-chrome" ]; then
    echo "✅ Chrome 已安装"
else
    echo "📥 安装 Chrome..."
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    sudo dpkg -i google-chrome-stable_current_amd64.deb 2>/dev/null
    sudo apt-get install -f -y
    rm google-chrome-stable_current_amd64.deb
    echo "✅ Chrome 安装完成"
fi

# 检查是否已安装 ChromeDriver
if command -v chromedriver &> /dev/null; then
    echo "✅ ChromeDriver 已安装"
else
    echo "📥 安装 ChromeDriver..."
    
    # 获取 Chrome 版本
    CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+')
    CHROME_MAJOR_VERSION=$(echo $CHROME_VERSION | cut -d'.' -f1)
    
    echo "  Chrome 版本: $CHROME_VERSION"
    echo "  主版本号: $CHROME_MAJOR_VERSION"
    
    # 下载对应版本的 ChromeDriver
    wget -q "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" -O chromedriver.zip 2>/dev/null
    
    if [ $? -ne 0 ]; then
        echo "  ⚠️  无法下载精确版本，尝试下载最新稳定版..."
        wget -q "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions.json" -O versions.json
        DRIVER_VERSION=$(python3 -c "import json; print(json.load(open('versions.json'))['channels']['Stable']['version'])")
        wget -q "https://storage.googleapis.com/chrome-for-testing-public/${DRIVER_VERSION}/linux64/chromedriver-linux64.zip" -O chromedriver.zip
        rm versions.json
    fi
    
    unzip -q chromedriver.zip
    sudo mv chromedriver-linux64/chromedriver /usr/local/bin/
    sudo chmod +x /usr/local/bin/chromedriver
    rm -rf chromedriver-linux64 chromedriver.zip
    echo "✅ ChromeDriver 安装完成"
fi

echo ""
echo "🗄️  步骤 5/5: 初始化新数据库表..."
python3 << EOF
from database import init_db
print("初始化数据库...")
init_db()
print("✅ 数据库表已创建")
EOF

echo ""
echo "========================================"
echo "✅ 升级完成！"
echo "========================================"
echo ""
echo "📋 下一步操作："
echo ""
echo "1. 重启服务："
echo "   sudo systemctl restart chatgpt-team"
echo ""
echo "2. 登录管理后台配置小红书功能："
echo "   - 访问: http://your-server:5002/admin"
echo "   - 进入「小红书订单同步」页面"
echo "   - 粘贴小红书 Cookie"
echo "   - 启用自动同步"
echo ""
echo "3. 查看服务日志："
echo "   sudo journalctl -u chatgpt-team -f"
echo ""
echo "⚠️  注意："
echo "   - 如未配置小红书功能，系统将以原有模式运行"
echo "   - 订单同步功能默认禁用，需手动启用"
echo "   - 现有邀请码功能不受影响"
echo ""
