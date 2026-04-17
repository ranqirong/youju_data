#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ERP API 登录测试 - 基于用户描述的流程
"""
import requests
import json
import base64
import secrets
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

BASE_URL = "https://erp.yjzf.com"
PHONE = "15196639414"
PASSWORD = "ran091426"

session = requests.Session()
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=utf-8",
    "Origin": "https://erp.yjzf.com",
    "Referer": "https://erp.yjzf.com/login"
}

print("="*60)
print("ERP API 登录测试")
print("="*60)

# 第1步：获取Cookie
print("\n【第1步】GET /login - 获取Cookie")
try:
    r = session.get(f"{BASE_URL}/login", headers=headers, timeout=15)
    print(f"  状态码: {r.status_code}")
    print(f"  Cookie: {dict(session.cookies)}")
    if r.status_code in [502, 503, 504]:
        print("  ❌ 504 错误 - IP被限制")
        exit(1)
except Exception as e:
    print(f"  ❌ 失败: {e}")
    exit(1)

# 第2步：获取code_key
print("\n【第2步】GET /api/sso/oidc/authorize - 获取code_key")
state = secrets.token_urlsafe(16)
params = {
    "response_type": "code",
    "client_id": "OIDC_CLIENT_ID_YJZF",
    "redirect_uri": f"{BASE_URL}/callback",
    "state": state,
    "scope": "openid"
}
try:
    r = session.get(f"{BASE_URL}/api/sso/oidc/authorize", params=params, headers=headers, timeout=10)
    print(f"  状态码: {r.status_code}")
    if r.status_code in [502, 503, 504]:
        print("  ❌ 504 错误 - API接口被限制")
        exit(1)
    data = r.json()
    code_key = data.get("data", {}).get("code_key", "")
    print(f"  code_key: {code_key[:20] if code_key else '未获取'}...")
except Exception as e:
    print(f"  ❌ 失败: {e}")
    exit(1)

# 第3步：FaceLogin
print("\n【第3步】POST /api/sso/security/faceLogin - 手机号验证")
try:
    r = session.post(f"{BASE_URL}/api/sso/security/faceLogin", json={"phone": PHONE}, headers=headers, timeout=10)
    print(f"  状态码: {r.status_code}")
    if r.status_code in [502, 503, 504]:
        print("  ❌ 504 错误")
        exit(1)
    data = r.json()
    user_id = data.get("data", {}).get("userId", "")
    print(f"  userId: {user_id if user_id else '未获取'}")
except Exception as e:
    print(f"  ❌ 失败: {e}")
    exit(1)

# 第4步：获取RSA公钥并加密密码
print("\n【第4步】GET /api/sso/security/k - 获取RSA公钥")
try:
    r = session.get(f"{BASE_URL}/api/sso/security/k", headers=headers, timeout=10)
    print(f"  状态码: {r.status_code}")
    if r.status_code in [502, 503, 504]:
        print("  ❌ 504 错误")
        exit(1)
    key_data = r.json()
    rsa_key = key_data.get("data", {}).get("pubkey", "")
    print(f"  公钥获取: {'成功' if rsa_key else '失败'}")
    
    if rsa_key:
        # RSA加密密码
        try:
            pem = f"-----BEGIN PUBLIC KEY-----\n{rsa_key}\n-----END PUBLIC KEY-----"
            public_key = RSA.import_key(pem)
            cipher = PKCS1_v1_5.new(public_key)
            encrypted = cipher.encrypt(PASSWORD.encode())
            encrypted_b64 = base64.b64encode(encrypted).decode()
            print("  密码加密: 成功")
        except Exception as e:
            print(f"  加密失败: {e}")
            encrypted_b64 = PASSWORD
except Exception as e:
    print(f"  ❌ 失败: {e}")
    exit(1)

# 第5步：密码登录
print("\n【第5步】POST /api/sso/oidc/execute - 密码登录")
try:
    body = {
        "code_key": code_key,
        "password": encrypted_b64,
        "phone": PHONE
    }
    r = session.post(f"{BASE_URL}/api/sso/oidc/execute", json=body, headers=headers, timeout=10)
    print(f"  状态码: {r.status_code}")
    if r.status_code in [502, 503, 504]:
        print("  ❌ 504 错误")
        exit(1)
    data = r.json()
    auth_code = data.get("data", {}).get("code", "")
    print(f"  授权码: {auth_code[:20] if auth_code else '未获取'}...")
except Exception as e:
    print(f"  ❌ 失败: {e}")
    exit(1)

# 第6步：获取AccessToken
print("\n【第6步】POST /api/sso/oidc/accessToken - 获取Token")
try:
    body = {
        "code": auth_code,
        "userId": user_id,
        "clientid": "OIDC_CLIENT_ID_YJZF",
        "clientsecret": "OIDC_CLIENT_SECRET_YJZF"
    }
    r = session.post(f"{BASE_URL}/api/sso/oidc/accessToken", json=body, headers=headers, timeout=10)
    print(f"  状态码: {r.status_code}")
    if r.status_code in [502, 503, 504]:
        print("  ❌ 504 错误")
        exit(1)
    data = r.json()
    token = data.get("data", {}).get("access_token", "")
    if token:
        print(f"\n{'='*60}")
        print("🎉 登录成功！")
        print(f"Token: {token[:50]}...")
        print(f"{'='*60}")
    else:
        print("  ❌ 未获取到Token")
except Exception as e:
    print(f"  ❌ 失败: {e}")

print("\n" + "="*60)
print("测试完成")
print("="*60)
