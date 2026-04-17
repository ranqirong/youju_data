---
name: erp-api-login
description: ERP 系统 API 登录和数据导出工具。通过调用 SSO 认证接口链（faceLogin → execute → authorize → accessToken）获取 Token，然后调用业务接口导出数据。使用场景：用户输入手机号和密码后，自动完成登录认证并导出人事数据、业务数据等。
---

# ERP API 登录与数据导出

## ✅ 当前状态

**登录功能**: ✅ 完全可用  
**数据导出**: ✅ 完全可用 - 支持 Excel 文件导出

**关键发现**:
- Authorization header **不需要** "Bearer " 前缀
- 直接使用 Token 即可
- 人事数据接口返回 Excel 文件流

## 核心功能

本 skill 提供基于 API 的 ERP 系统登录和数据导出能力：

1. **SSO 认证链** - 6 步完成登录认证获取 Token
2. **RSA 密码加密** - 自动获取公钥并加密密码
3. **Token 管理** - 自动获取和使用访问令牌
4. **数据导出** - 调用业务接口导出 Excel 文件
5. **完整流程** - 从登录到导出全自动

## 认证流程

```
1. 访问登录页面       → 获取 Cookie
2. 获取 RSA 公钥      → 【公钥接口】
3. 获取 code_key     → 【授权接口】
4. faceLogin         → 【人脸登录接口】
5. execute           → 【密码登录接口】
6. accessToken       → 【令牌接口】
7. 业务接口调用      → Authorization: <token> (不加 Bearer!)
```

## 接口别名表

| 别名 | 真实路径 | 说明 |
|------|---------|------|
| 【公钥接口】 | `/api/sso/security/k` | 获取 RSA 公钥 |
| 【授权接口】 | `/api/sso/oidc/authorize` | 获取授权码 |
| 【人脸登录接口】 | `/api/sso/security/faceLogin` | 人脸识别登录 |
| 【密码登录接口】 | `/api/sso/oidc/execute` | 密码验证登录 |
| 【令牌接口】 | `/api/sso/oidc/accessToken` | 获取访问令牌 |
| 【用户信息接口】 | `/api/erp.settings.api/common/userInfo` | 获取用户信息 |
| 【指标字典接口】 | `/api/common.stats.api/customization/statistics/dict` | 获取统计指标字典 |
| 【创建导出接口】 | `/api/common.stats.api/customization/statistics/export` | 创建自定义报表导出任务 |
| 【导出文件列表接口】 | `/api/common.stats.api/quantification/statistics/file/list` | 获取我的导出文件列表 |
| 【新房合同导出接口】 | `/api/erp.contract.api/order/estate/query/exportNew` | 导出新房合同信息 ⭐ |
| 【项目明细导出接口】 | `/api/erp.newhouse.api/erp/projectList/export/myListV3` | 导出项目明细列表 ⭐ |
| 【带看数据导出接口】 | `/api/erp.newhouse.api/reportinfo/pc/exportVisitList` | 导出新房带看记录 ⭐ |
| 【竞对数据导出接口】 | `/api/common.stats.api/rival/stats/pcPkExport` | 导出竞争对手对比数据 ⭐ |
| 【落后项目导出接口】 | `/api/common.stats.api/rival/stats/pcPkExport` | 导出落后项目数据报表 ⭐ |
| 【人事数据导出接口】 | `/api/common.stats.api/statistics/personnel/export` | 导出人事数据 Excel |

**说明**: 输出日志中使用别名替代真实接口地址，增强安全性。

## 快速开始

### 基本用法

用户提供：
- 手机号（如：你的手机号）
- 密码（明文）

### 示例 1: 导出人事数据

**用户**: 帮我导出 ERP 人事数据

**执行**:
```bash
python3 ~/.openclaw/skills/erp-api-login/scripts/erp-export.py
```

**输出**:
```
✅ 人事数据导出成功！
   文件：~/Desktop/ERP 导出/人事数据_20260326_084228.xlsx
   大小：34943 字节
```

### 示例 2: 查看指标字典

**用户**: 查看 ERP 有哪些统计指标

**执行**:
```bash
python3 ~/.openclaw/skills/erp-api-login/scripts/get-statistics-dict.py
```

**输出**:
```
✅ 指标字典获取成功！
指标分类数量：22

1. 人事指标 (10 个指标)
   1. 在职人数 [代码：5] [有子项]
   2. 门店人数 [代码：5230] [无子项]
   ...

2. 经纪人指标 (6 个指标)
   1. 经纪人认证 [代码：51]
   ...

3. 门店指标 (5 个指标)
   ...
```

### 示例 3: 创建自定义报表导出

**用户**: 创建自定义统计报表导出

**执行**:
```bash
python3 ~/.openclaw/skills/erp-api-login/scripts/create-custom-export.py
```

**输出**:
```
✅ 【创建导出接口】 - 创建成功

💡 提示:
1. 导出任务创建后，系统会在后台生成文件
2. 使用 get-export-list.py 查看导出进度和下载文件
3. 大文件可能需要几分钟生成时间
```

### 示例 4: 查看我的导出文件

**用户**: 查看我已创建的导出文件

**执行**:
```bash
python3 ~/.openclaw/skills/erp-api-login/scripts/get-export-list.py
```

**输出**:
```
✅ 【导出文件列表接口】 - 获取成功
   文件数量：4

📋 导出文件详情
1. 2026-03-26 自定义指标报表
   导出 ID: 396b86a5-d52a-4da0-928d-63a6cf34442c
2. 2026-03-26 最近 7 天报表
   ...
```
2. 调用 execute 进行密码登录
3. 调用 authorize 获取授权码
4. 调用 accessToken 获取 Token
5. 调用人事数据接口导出

## 关键注意事项

### Authorization Header 格式

**❌ 错误**:
```python
headers['Authorization'] = f'Bearer {token}'
```

**✅ 正确**:
```python
headers['Authorization'] = token
```

**直接放 Token，不要加 "Bearer " 前缀！**

### 响应格式

人事数据接口返回 **Excel 文件流**：
- Content-Type: `application/octet-stream`
- Content-Disposition: `attachment;filename=xxx.xlsx`
- 需要保存为二进制文件

### 2. 【密码登录接口】- 执行登录

**用途**: 密码验证，获取授权 code 和 userId

**请求**:
```json
{
  "c_name": "BPasswordLogin",
  "code_key": "f96cd177e6fa4c7b870267728b7c6101",
  "input_param": {
    "username": "你的手机号",
    "password": "D/7PuuX3CM6rQ9FvyHezyVgjn/AvBHwL3o0fpcDH+d3yk...",
    "regionCode": 86
  }
}
```

**响应**:
```json
{
  "code": "200",
  "data": {
    "code": "2bc7615f0481451a84698c3513ba9f13",
    "userId": "605769483885219840"
  }
}
```

### 3. 【授权接口】- 授权码交换

**参数**:
- scope: openid
- response_type: code
- client_id: 123456789
- redirect_url: https://localhost:8443/uac/
- state: e268443e43d93dab7ebef303bbe9642f
- auth_type: BPassword
- date: 当前时间 ISO 格式

**响应**: 重定向到 redirect_url，附带 code 参数

### 4. 【令牌接口】- 获取访问令牌

**请求**:
```json
{
  "code": "2bc7615f0481451a84698c3513ba9f13",
  "state": "e268443e43d93dab7ebef303bbe9642f",
  "userId": "605769483885219840",
  "client_id": "585014642717982720",
  "client_secret": "b9c7398eebe909a01603d5fba2c55086"
}
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiJ9...",
  "token_type": "Bearer",
  "expires_in": 43200
}
```

**用途**: 获取 JWT Token，用于后续业务接口调用

### 5. 业务接口调用

#### 【指标字典接口】

**端点**: `POST /api/common.stats.api/customization/statistics/dict`

**Headers**:
```
Authorization: <access_token>  // 【关键】不加 "Bearer " 前缀
X-Organ-Id: 593347894961426496
X-City-Code: 150200
X-Brand-Id: 593347894961426496
```

**请求体**: 原始数据（非 JSON），例如：`5`

**响应示例**:
```json
{
  "code": "200",
  "succeed": true,
  "data": [...]  // 指标字典列表
}
```

**用途**: 获取统计指标字典，用于数据分析和报表配置

---

#### 【创建导出接口】

**端点**: `POST /api/common.stats.api/customization/statistics/export`

**Headers**:
```
Authorization: <access_token>  // 【关键】不加 "Bearer " 前缀
X-Organ-Id: 593347894961426496
X-City-Code: 150200
X-Brand-Id: 593347894961426496
```

**请求体**:
```json
{
  "agentCodeQueries": [
    {"codeName": "经纪人认证", "code": "51", "hasChild": 0},
    {"codeName": "门店数", "code": "29", "hasChild": 1, "childNodes": [
      {"codeName": "营业", "code": "36"},
      {"codeName": "启用", "code": "46"}
    ]}
  ],
  "brandId": "593347894961426496",
  "cityCode": "150200",
  "playerId": "593347894961426496",
  "level": 6,
  "termsLevel": 5,
  "fileName": "2026-03-26 自定义报表导出",
  "branchIds": [],
  "startTime": 1772294400000,
  "endTime": 1774454399999,
  "pageNo": 1,
  "pageSize": 10
}
```

**响应**:
```json
{
  "code": "200",
  "succeed": true,
  "data": {
    "id": "396b86a5-d52a-4da0-928d-63a6cf34442c",
    "fileName": "2026-03-26 自定义报表导出",
    "status": "0"  // 0=生成中，1=已完成
  }
}
```

**用途**: 创建自定义统计报表导出任务，支持选择指标、时间范围、筛选条件

---

#### 【导出文件列表接口】

**端点**: `POST /api/common.stats.api/quantification/statistics/file/list`

**Headers**:
```
Authorization: <access_token>
X-Organ-Id: 593347894961426496
X-City-Code: 150200
X-Brand-Id: 593347894961426496
```

**请求体**:
```json
{
  "startInc": 1772294400000,  // 开始时间戳（毫秒）
  "endExc": 1774540799999     // 结束时间戳（毫秒）
}
```

**响应**:
```json
{
  "code": "200",
  "succeed": true,
  "data": [
    {
      "id": "396b86a5-d52a-4da0-928d-63a6cf34442c",
      "fileName": "2026-03-26 自定义报表导出",
      "status": "1",
      "createTime": "2026-03-26 08:55:00",
      "fileSize": 12345
    }
  ]
}
```

**用途**: 获取用户已创建的导出文件列表，查看导出进度和结果

---

#### 【人事数据导出接口】

**端点**: `POST /api/common.stats.api/statistics/personnel/export`

**Headers**:
```
Authorization: <access_token>  // 【关键】不加 "Bearer " 前缀
X-Organ-Id: 593347894961426496
X-City-Code: 150200
X-Brand-Id: 593347894961426496
```

**请求体**:
```json
{
  "pageNo": 1,
  "pageSize": 10,
  "brandId": "593347894961426496",
  "branchIds": ["642829776165806208", ...],
  "affiliationType": [],
  "businessDept": [],
  "brandLogo": []
}
```

**响应**: Excel 文件流（application/octet-stream）

## 密码加密说明

根据抓包分析，密码使用 RSA 公钥加密：

1. 从登录页面获取公钥
2. 使用公钥加密密码
3. Base64 编码后传输

**加密示例**（Python）:
```python
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import base64

# 公钥（需要从登录页面获取）
public_key = RSA.import_key(open('public.pem').read())
cipher = PKCS1_v1_5.new(public_key)

# 加密密码
encrypted = cipher.encrypt(password.encode('utf-8'))
encoded = base64.b64encode(encrypted).decode('utf-8')
```

## 必需 Headers

所有接口都需要以下 Headers：

```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:148.0) Gecko/20100101 Firefox/148.0',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,zh-TW;q=0.8,zh-HK;q=0.7,en-US;q=0.6,en;q=0.5',
    'Content-Type': 'application/json;charset=utf-8',
    'X-Requested-With': 'XMLHttpRequest',
    'Cache-Control': 'no-cache',
    'x-user-agent': 'YJYJ-ERP/v2.5.0',
    'X-Organ-Id': '',
    'X-City-Code': '',
    'X-Brand-Id': 'undefined',
    'Origin': 'https://erp.yjzf.com',
    'Referer': 'https://erp.yjzf.com/login'
}
```

业务接口需要额外添加：
```python
'Authorization': access_token  # 【关键】不加 "Bearer " 前缀！
```

## 错误处理

### 常见错误码

| 错误码 | 说明 | 处理方式 |
|--------|------|---------|
| 401 | 未授权/Token 过期 | 重新登录获取新 Token |
| 403 | 权限不足 | 检查用户权限 |
| 404 | 接口不存在 | 检查接口路径 |
| 500 | 服务器错误 | 稍后重试 |

### Token 刷新

Token 有效期约 12 小时，过期后需要：
1. 检查 Token 是否过期
2. 调用 faceLogin 重新开始认证流程
3. 获取新 Token 并更新

## 输出格式

### 成功响应

```json
{
  "success": true,
  "data": {
    "records": [...],
    "total": 100,
    "pageNo": 1,
    "pageSize": 10
  },
  "token": "eyJhbGciOiJSUzI1NiJ9..."
}
```

### 失败响应

```json
{
  "success": false,
  "error": "Token expired",
  "code": 401
}
```

## 安全注意事项

1. **密码保护**
   - 不要明文存储密码
   - 使用 base64 或加密存储
   - 定期更换密码

2. **Token 管理**
   - Token 有效期 12 小时
   - 不要泄露 Token
   - 使用后及时清除

3. **请求频率**
   - 避免高频请求
   - 添加适当延迟
   - 遵守 API 限流策略

## 相关文件

### 核心脚本

| 脚本 | 说明 |
|------|------|
| `scripts/erp-export.py` | 主脚本 - 登录 + 导出人事数据 |
| `scripts/get-statistics-dict.py` | 获取统计指标字典（查看可用指标） |
| `scripts/create-custom-export.py` | 创建自定义报表导出任务 |
| `scripts/get-export-list.py` | 获取我的导出文件列表 |
| `scripts/erp-api-client.py` | Python API 客户端库 |

### 参考文档

| 文档 | 说明 |
|------|------|
| `references/api-endpoints.md` | 完整接口列表 |
| `references/encryption-guide.md` | 密码加密指南 |

## 故障排除

### Q1: 登录失败

**排查**:
1. 检查手机号格式
2. 确认密码加密正确
3. 验证 code_key 是否有效
4. 检查网络连接

### Q2: Token 无效

**解决**:
1. Token 可能过期，重新登录
2. 检查 Authorization header 格式
3. 确认 Token 未损坏

### Q3: 数据为空

**检查**:
1. 确认 branchIds 是否正确
2. 检查筛选条件
3. 验证用户权限
