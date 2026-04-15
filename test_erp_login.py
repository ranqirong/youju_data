#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 ERP API 登录 - 使用已有代码"""
import sys
sys.path.insert(0, '/root/.openclaw/erp-api-login/scripts')

from erp_export import ERPAPIClient, get_user_credentials

print("="*70)
print("ERP API 登录测试")
print("="*70)

# 获取凭证
phone, password = get_user_credentials()
if not phone or not password:
    print("❌ 未找到凭证")
    sys.exit(1)

print(f"账号: {phone}")
print(f"密码: {'*' * len(password)}")

# 创建客户端并登录
client = ERPAPIClient(phone, password)
success = client.login()

if success:
    print("\n" + "="*70)
    print("🎉 登录成功！")
    print(f"Token: {client.token[:50]}...")
    print("="*70)
else:
    print("\n" + "="*70)
    print("❌ 登录失败")
    print("="*70)
    sys.exit(1)
