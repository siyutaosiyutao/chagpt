# 🔍 组织ID自动识别功能说明

## 功能介绍

当你的 ChatGPT Team Token 过期后,重新上传 Session JSON 时,系统会自动识别是否为已存在的组织,并自动更新 Token,而不是创建重复的 Team。

## 工作原理

### 1. 组织ID识别

每个 ChatGPT Team 都有一个唯一的 `organization_id`,例如:
```
org-OeQksFELsYDNPdsfjqrWp89q
```

系统会在你上传 Session JSON 时自动提取这个 ID。

### 2. 自动判断

上传 Session JSON 时,系统会:

1. **提取组织ID**: 从 Session JSON 中提取 `organization_id`
2. **查找数据库**: 检查数据库中是否已存在相同的 `organization_id`
3. **智能处理**:
   - ✅ **如果已存在**: 自动更新该 Team 的 Token 和其他信息
   - ✅ **如果不存在**: 创建新的 Team

### 3. 自动更新内容

当检测到已存在的组织时,会自动更新:
- ✅ Team 名称 (如果你修改了)
- ✅ Access Token (最重要!)
- ✅ Account ID
- ✅ 邮箱地址

**不会更新:**
- ❌ 访问密钥 (保持不变,已分发的密钥继续有效)
- ❌ 邀请记录 (保持不变)
- ❌ Organization ID (不可变)

## 使用场景

### 场景 1: Token 过期

```
问题: 你的 ChatGPT Team Token 过期了,无法继续邀请成员

解决方案:
1. 重新登录 ChatGPT
2. 访问 https://chatgpt.com/api/auth/session
3. 复制新的 Session JSON
4. 在管理后台粘贴并提交
5. ✅ 系统自动识别并更新 Token
6. ✅ 之前分发的密钥继续有效
```

### 场景 2: 更新账户信息

```
问题: 你修改了 Team 名称或邮箱

解决方案:
1. 重新获取 Session JSON
2. 在管理后台粘贴并提交
3. ✅ 系统自动更新所有信息
```

### 场景 3: 避免重复创建

```
问题: 不小心多次上传同一个 Team 的 Session JSON

解决方案:
✅ 系统自动识别,不会创建重复的 Team
✅ 只会更新已存在的 Team
```

## 操作步骤

### 步骤 1: 获取新的 Session JSON

1. 登录 ChatGPT: https://chatgpt.com
2. 访问 Session API: https://chatgpt.com/api/auth/session
3. 复制整个 JSON 内容

### 步骤 2: 上传到管理后台

1. 访问管理后台: http://你的域名:5002/admin
2. 找到"➕ 添加新 Team"卡片
3. 粘贴 Session JSON
4. (可选) 修改 Team 名称
5. 点击"创建 Team"

### 步骤 3: 查看结果

系统会显示两种结果之一:

**情况 A: 新 Team**
```
✅ Team 创建成功！
```

**情况 B: 已存在的 Team (自动更新)**
```
✅ 检测到已存在的组织 (ID: org-xxxxx),已自动更新 Token 和信息
```

## 技术细节

### Session JSON 结构

系统会从 Session JSON 中提取以下信息:

```json
{
  "user": {
    "email": "your@email.com"
  },
  "account": {
    "id": "76e2e022-3d0c-4c83-94f9-2f96d3d7e6e2",
    "organizationId": "org-OeQksFELsYDNPdsfjqrWp89q"
  },
  "accessToken": "eyJhbGciOiJSUzI1NiIs..."
}
```

### 数据库查询逻辑

```python
# 1. 提取 organization_id
organization_id = session_data['account']['organizationId']

# 2. 查找是否已存在
existing_team = Team.get_by_organization_id(organization_id)

# 3. 判断处理
if existing_team:
    # 更新已存在的 Team
    Team.update_team_info(existing_team['id'], ...)
else:
    # 创建新 Team
    Team.create(...)
```

### API 响应格式

**新建 Team:**
```json
{
  "success": true,
  "team_id": 1,
  "message": "Team 创建成功",
  "updated": false
}
```

**更新已存在的 Team:**
```json
{
  "success": true,
  "team_id": 1,
  "message": "检测到已存在的组织 (ID: org-xxxxx),已自动更新 Token 和信息",
  "updated": true
}
```

## 常见问题

### Q1: 如何知道 Token 是否过期?

**A**: 出现以下情况说明 Token 可能过期:
- 邀请成员时返回 401 错误
- 自动检测踢人功能失败
- 管理后台显示 Token 错误

### Q2: 更新 Token 后,之前的密钥还能用吗?

**A**: ✅ 可以!
- 访问密钥存储在数据库中,不受 Token 更新影响
- 用户使用密钥时,会使用最新的 Token 进行邀请
- 所以更新 Token 后,所有密钥继续有效

### Q3: 如果我有多个 Team 怎么办?

**A**: 
- 每个 Team 都有唯一的 `organization_id`
- 系统会分别识别和管理
- 不会混淆

### Q4: 可以手动更新 Token 吗?

**A**: 可以,有两种方式:
1. **推荐**: 重新上传 Session JSON (自动识别)
2. **手动**: 在 Teams 列表中点击"更新 Token"按钮

### Q5: 如果 organization_id 为空怎么办?

**A**: 
- 系统会正常创建 Team
- 但无法自动识别重复
- 建议使用有 organization_id 的账户

## 优势

### ✅ 避免重复

- 不会创建重复的 Team
- 数据库保持整洁

### ✅ 无缝更新

- Token 过期后,一键更新
- 不需要手动操作

### ✅ 密钥持续有效

- 更新 Token 不影响已分发的密钥
- 用户体验不受影响

### ✅ 自动化管理

- 减少人工操作
- 降低出错概率

## 注意事项

### ⚠️ 重要提示

1. **定期检查 Token**: 建议每周检查一次 Token 是否有效
2. **及时更新**: Token 过期后尽快更新,避免影响用户
3. **备份数据**: 定期备份数据库,防止数据丢失
4. **监控日志**: 查看自动检测日志,及时发现问题

### 🔒 安全建议

1. **保护 Session JSON**: 不要泄露给他人
2. **定期更换密码**: 提高账户安全性
3. **启用 2FA**: 如果 ChatGPT 支持,建议启用两步验证

## 更新日志

### v1.0.0 (2025-10-31)
- ✅ 初始版本
- ✅ 支持组织ID自动识别
- ✅ 支持自动更新 Token
- ✅ 支持前端提示信息

## 相关功能

- [自动踢人功能](./自动踢人功能说明.md)
- [访问密钥管理](./README.md)

## 支持

如有问题,请:
1. 查看服务器日志
2. 检查 Session JSON 格式
3. 确认 organization_id 是否存在

