# ERP API 接口完整列表

## 认证接口 (SSO)

### 1. FaceLogin - 人脸登录初始化

**端点**: `POST /api/sso/security/faceLogin`

**描述**: 初始化登录流程，获取 code_key

**请求**:
```json
{
  "phone": "你的手机号"
}
```

**响应示例**:
```json
{
  "code": "200",
  "msg": "success",
  "succeed": true,
  "data": {
    "code_key": "f96cd177e6fa4c7b870267728b7c6101"
  }
}
```

**用途**: 第一步，获取 code_key 用于密码加密登录

---

### 2. Execute - 执行登录

**端点**: `POST /api/sso/oidc/execute`

**描述**: 使用密码进行登录验证

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

**响应示例**:
```json
{
  "code": "200",
  "msg": "success",
  "succeed": true,
  "data": {
    "code": "2bc7615f0481451a84698c3513ba9f13",
    "userId": "605769483885219840"
  }
}
```

**用途**: 第二步，密码验证，获取授权 code 和 userId

---

### 3. Authorize - 授权码交换

**端点**: `GET /api/sso/oidc/authorize`

**描述**: OAuth2 授权码交换

**参数**:
| 参数 | 必填 | 说明 |
|------|------|------|
| scope | 是 | openid |
| response_type | 是 | code |
| client_id | 是 | 123456789 |
| redirect_url | 是 | https://localhost:8443/uac/ |
| state | 是 | 随机字符串 |
| auth_type | 是 | BPassword |
| date | 是 | ISO 时间戳 |

**响应**: 302 重定向到 redirect_url，附带 code 参数

**用途**: 第三步，获取授权码

---

### 4. AccessToken - 获取访问令牌

**端点**: `POST /api/sso/oidc/accessToken`

**描述**: 使用授权码换取 access_token

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

**响应示例**:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiJ9...",
  "token_type": "Bearer",
  "expires_in": 43200,
  "refresh_token": "..."
}
```

**用途**: 第四步，获取 JWT Token 用于业务接口调用

---

## 业务接口

### 5. 用户邀请信息

**端点**: `POST /api/erp.settings.api/common/userInvitationInfo`

**描述**: 获取用户邀请信息

**Headers**:
```
Authorization: Bearer <access_token>
```

**请求**:
```json
{
  "code": "pc"
}
```

**用途**: 获取用户信息

---

### 6. 人事数据导出

**端点**: `POST /api/common.stats.api/statistics/personnel/export`

**描述**: 导出人事统计数据

**Headers**:
```
Authorization: Bearer <access_token>
X-Organ-Id: 593347894961426496
X-City-Code: 150200
X-Brand-Id: 593347894961426496
```

**请求参数**:
```json
{
  "affiliationType": [],
  "businessDept": [],
  "brandLogo": [],
  "pageNo": 1,
  "pageSize": 10,
  "brandId": "593347894961426496",
  "branchIds": [
    "642829776165806208",
    "639247450081075328",
    "638814273034264704",
    "1268294145817239680",
    "841850590733852800",
    "642830532998602880",
    "640664673391747200",
    "593372592860440704",
    "704402577401847936",
    "626501095205662848",
    "613943426964025472",
    "620691405108441216",
    "1432098607051362432",
    "1451405568469160064",
    "1451407158483669120",
    "650088671590490240",
    "752245813734285440",
    "761846012047794304",
    "824359355936989312",
    "638817112007647360",
    "640663043099336832",
    "635549166858170496",
    "721999515701747840",
    "654660257723195520",
    "638815522236407936",
    "622868403243217024",
    "644993931555643520",
    "654664837647310976",
    "625866348750205056",
    "625864877560328320",
    "624416730724200576",
    "635548171130400896",
    "975839798682247296",
    "945146468365557888",
    "942533285809283200",
    "918333673141756032",
    "625865500666130560",
    "608133917234483328",
    "763296507056627840",
    "638814915786186880",
    "640663306921058432",
    "746167369556566144",
    "1224512835693109376",
    "1184678111533654144",
    "1066071935162835072",
    "654659435517976704",
    "805527508834640000",
    "1125944275136471168",
    "611648535252748416"
  ]
}
```

**响应示例**:
```json
{
  "code": "200",
  "succeed": true,
  "data": {
    "records": [
      {
        "createDate": "2019-10-21",
        "type": "直营",
        "city": "南宁",
        "cityManager": "陈奕霏",
        "totalEmployees": 6475,
        "storeEmployees": 6250,
        "platformEmployees": 195,
        "monthJoin": 656,
        "monthLeave": 277
      }
    ],
    "total": 100,
    "pageNo": 1,
    "pageSize": 10
  }
}
```

**用途**: 导出人事统计数据

---

## 通用 Headers

所有接口都需要以下基础 Headers：

```python
{
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

业务接口额外需要：
```python
{
    'Authorization': 'Bearer <access_token>',
    'X-Organ-Id': '<organ_id>',
    'X-City-Code': '<city_code>',
    'X-Brand-Id': '<brand_id>',
    'Referer': 'https://erp.yjzf.com/count_all/overview_list'
}
```

---

## Cookie 管理

登录过程中会自动设置以下 Cookie：

- `gdxidpyhxdE` - 设备指纹
- `__snaker__id` - 会话 ID
- `SECKEY_ABVK` - 安全密钥
- `BMAP_SECKEY` - 百度地图密钥
- `pcDeviceCode` - PC 设备码
- `Hm_lvt_5aac2aca85a2a77ebe6d025d1b7950cc` - 统计
- `acw_tc` - 阿里云 WAF

使用 requests.Session() 会自动管理 Cookie。

---

## 错误码

| 错误码 | 说明 | 处理方式 |
|--------|------|---------|
| 200 | 成功 | - |
| 401 | 未授权 | 重新登录 |
| 403 | 权限不足 | 检查权限 |
| 404 | 接口不存在 | 检查路径 |
| 500 | 服务器错误 | 稍后重试 |

---

## 认证流程图

```
用户输入手机号和密码
        ↓
   1. faceLogin
   获取 code_key
        ↓
   2. execute
   密码验证，获取 code 和 userId
        ↓
   3. authorize
   OAuth2 授权
        ↓
   4. accessToken
   获取 access_token
        ↓
   5. 业务接口调用
   使用 Token 访问数据
```

---

## 密码加密

密码使用 RSA 公钥加密，步骤：

1. 从登录页面获取公钥
2. 使用 PKCS1_v1_5 填充
3. RSA 加密
4. Base64 编码

**Python 示例**:
```python
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import base64

public_key = RSA.import_key(open('public.pem').read())
cipher = PKCS1_v1_5.new(public_key)
encrypted = cipher.encrypt(password.encode('utf-8'))
encoded = base64.b64encode(encrypted).decode('utf-8')
```

---

## Token 说明

**格式**: JWT (JSON Web Token)

**有效期**: 43200 秒 (12 小时)

**结构**:
```
Header.Payload.Signature
```

**Payload 内容**:
```json
{
  "dt": "pc_web",
  "tt": "1",
  "sub": "605769483885219840",
  "UNonce": "82f60258-0a76-4cb3-be4f-0343e6cc5d2f",
  "ct": "111.198.227.119",
  "role": "585014642717982720",
  "iss": "yjzf.com",
  "exp": 1774489557,
  "iat": 1774446357,
  "jti": "1d78d33b-ce1c-4067-94f0-2cde05ea2139"
}
```

**注意事项**:
- Token 过期后需要重新登录
- 不要泄露 Token
- 每次请求都需要携带 Authorization header
