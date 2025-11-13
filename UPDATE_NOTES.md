# 更新说明 - Token过期检测 & 防误触保护

## 🎯 更新内容

### 1. Token过期智能检测（5次401后标记）

#### 数据库改动
- 在 `teams` 表中添加了两个新字段：
  - `token_error_count`: 记录401错误次数
  - `token_status`: Token状态（'active' 或 'expired'）

#### 工作原理
1. 每次API调用返回401时，错误计数+1
2. 当错误计数达到5次时，自动标记为 `expired`
3. 当API调用成功或更新Token时，自动重置计数为0

#### 前端显示
- Team卡片上会显示Token状态：
  - `⚠️ 错误1/5` ~ `⚠️ 错误4/5`: 橙色警告标记
  - `⚠️ Token已过期`: 红色错误标记（达到5次后）
- 邀请失败时会显示友好提示：
  ```
  ⚠️ Token已过期
  
  Token已过期，请更新该Team的Token
  
  请在Teams列表中找到对应的Team，点击"🔄 更新Token"按钮更新Token后重试
  ```

### 2. 邀请按钮防误触保护

#### 改进的功能
1. **管理员自动邀请** (`adminInviteAuto`)
   - ✅ 添加全局标志 `isAdminInviting` 防止重复提交
   - ✅ 按钮禁用 + 文本变更为"邀请中..."
   - ✅ 使用 `finally` 确保状态恢复

2. **手动踢人** (`manualKickMember`)
   - ✅ 添加全局标志 `isKicking` 防止重复提交
   - ✅ 按钮禁用 + 文本变更为"踢出中..."
   - ✅ 使用 `finally` 确保状态恢复

3. **成员管理弹窗邀请** (`inviteMember`)
   - ✅ 已有防护，现在添加了Token过期提示

#### 用户体验改进
- 点击按钮后立即禁用，防止重复点击
- 显示加载状态（"邀请中..."、"踢出中..."）
- 操作完成后自动恢复按钮状态
- 如果在处理中再次点击，会提示"正在处理中，请稍候..."

## 📝 技术细节

### 数据库迁移
系统会自动检测并添加新字段，无需手动迁移：
```python
try:
    cursor.execute('ALTER TABLE teams ADD COLUMN token_error_count INTEGER DEFAULT 0')
except sqlite3.OperationalError:
    pass  # 字段已存在
```

### API改动
`invite_to_team()` 函数新增 `team_id` 参数：
```python
def invite_to_team(access_token, account_id, email, team_id=None):
    # 成功时重置错误计数
    if team_id:
        Team.reset_token_error(team_id)
    
    # 401时增加错误计数
    elif response.status_code == 401:
        if team_id:
            status = Team.increment_token_error(team_id)
            if status and status['token_status'] == 'expired':
                return {"error_code": "TOKEN_EXPIRED", ...}
```

### 新增数据库方法
- `Team.increment_token_error(team_id)`: 增加错误计数
- `Team.reset_token_error(team_id)`: 重置错误计数
- `Team.get_token_status(team_id)`: 获取Token状态

## 🚀 部署说明

1. 停止当前运行的服务
2. 更新代码
3. 重启服务（数据库会自动迁移）
4. 清除浏览器缓存以加载新的前端代码

## ✅ 测试建议

1. **Token过期检测测试**：
   - 使用一个过期的Token
   - 尝试邀请5次
   - 观察Team卡片上的错误计数变化
   - 第5次后应显示"Token已过期"

2. **防误触测试**：
   - 快速连续点击"发送邀请"按钮
   - 应该只发送一次请求
   - 按钮应显示"邀请中..."并被禁用

3. **Token更新测试**：
   - 更新一个有错误计数的Team的Token
   - 错误计数应重置为0
   - 状态应变回"active"

## 📋 文件变更清单

- ✅ `database.py`: 添加Token状态字段和相关方法
- ✅ `app_new.py`: 修改invite_to_team函数，添加401检测
- ✅ `templates/admin.html`: 添加防误触保护和Token状态显示
- ✅ `templates/admin_new.html`: 添加防误触保护和Token状态显示

## 🎨 UI改进

### Token状态标记
- 🟢 正常：无标记
- 🟠 警告：`⚠️ 错误X/5`（橙色背景）
- 🔴 过期：`⚠️ Token已过期`（红色背景）

### 按钮状态
- 正常：可点击，显示原始文本
- 处理中：禁用，显示"处理中..."
- 完成：自动恢复到正常状态
