# 快速部署指南 - 小红书自动发货功能

## 🚀 5分钟快速部署

### 1. 备份现有系统

```bash
cd /path/to/chagpt
cp chatgpt_team.db chatgpt_team.db.backup.$(date +%Y%m%d)
```

### 2. 拉取最新代码

```bash
git pull origin main
```

### 3. 运行升级脚本

```bash
chmod +x upgrade_xhs.sh
./upgrade_xhs.sh
```

### 4. 重启服务

```bash
sudo systemctl restart chatgpt-team
```

### 5. 配置小红书

1. 访问管理后台：`http://your-server:5002/admin`
2. 滚动到「🛍️ 小红书订单同步」section
3. 按照以下步骤配置：

#### 获取 Cookie

1. 登录小红书千帆后台：https://ark.xiaohongshu.com
2. 按 `F12` 打开开发者工具
3. 切换到 **Network** 标签
4. 访问订单页面：https://ark.xiaohongshu.com/app-order/order/query
5. 找到任意请求，查看 **Request Headers**
6. 复制完整的 `Cookie` 字符串

#### 转换为 JSON 格式

方式 1：使用在线工具转换  
方式 2：手动格式化（推荐简化版）

```json
{
  "key1": "value1",
  "key2": "value2"
}
```

#### 在管理后台配置

1. 粘贴 Cookie（JSON 格式）
2. 设置同步间隔：`6` 小时
3. 勾选「启用自动订单同步」
4. 点击「💾 保存配置」
5. 点击「🔄 立即同步」测试

### 6. 验证部署

```bash
# 查看服务日志
sudo journalctl -u chatgpt-team -f

# 查看同步状态
# 访问管理后台查看「同步状态」卡片

# 测试订单号邀请
# 访问用户页面，输入邮箱和订单号
```

---

## 📋 部署检查清单

- [ ] 数据库已备份
- [ ] 代码已更新（git pull）
- [ ] 依赖已安装（selenium, apscheduler）
- [ ] Chrome 和 ChromeDriver 已安装
- [ ] 服务已重启
- [ ] 小红书 Cookie 已配置
- [ ] 自动同步已启用
- [ ] 手动同步测试成功
- [ ] 订单号邀请测试成功

---

## 🔧 常见问题

### Q: ChromeDriver 版本不匹配

```bash
# 查看 Chrome 版本
google-chrome --version

# 下载对应版本
# https://googlechromelabs.github.io/chrome-for-testing/
```

### Q: Cookie 过期

重新登录小红书千帆，获取新 Cookie，在管理后台更新。

### Q: 订单未提取

1. 检查 Cookie 是否有效
2. 增加同步滚动次数（修改代码）
3. 手动触发多次同步

---

## 🎯 使用流程

### 管理员

1. **首次配置**：配置 Cookie → 启用同步 → 手动测试
2. **日常使用**：查看同步状态 → 查看订单列表
3. **维护**：定期更新 Cookie（约30天）

### 用户

1. 在小红书下单
2. 获得订单号（如 P779156135993499601）
3. 访问网站输入邮箱 + 订单号
4. 收到 ChatGPT Team 邀请邮件
5. 确认加入

---

## 📊 监控指标

在管理后台「🛍️ 小红书订单同步」查看：

- **同步状态**：已启用 / 未启用 / 同步中
- **最后同步**：同步时间
- **订单统计**：总计 / 未使用 / 已使用
- **今日新增**：今天提取的订单数
- **错误信息**：如果同步失败，显示错误原因

---

## 🔒 安全提示

- ⚠️ Cookie 包含敏感信息，请妥善保管
- ⚠️ 建议使用 HTTPS
- ⚠️ 定期更新 Cookie
- ⚠️ 同步间隔建议 ≥ 6 小时

---

## 📞 获取支持

如遇问题，请查看：

1. 服务日志：`sudo journalctl -u chatgpt-team -n 100`
2. 详细文档：`XHS_UPGRADE_GUIDE.md`
3. 实施报告：查看 walkthrough artifact

---

**部署完成！享受自动发货带来的便利！** 🎉
