#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取我的导出文件列表
查看已创建的导出任务和文件
"""

import sys
import os
import importlib.util
from datetime import datetime, timedelta

# 加载 erp_export 模块
script_dir = os.path.dirname(os.path.abspath(__file__))
erp_export_path = os.path.join(script_dir, 'erp-export.py')

spec = importlib.util.spec_from_file_location("erp_export", erp_export_path)
erp_export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(erp_export)

ERPAPIClient = erp_export.ERPAPIClient
DEFAULT_CONFIG = erp_export.DEFAULT_CONFIG
get_user_credentials = erp_export.get_user_credentials

def main():
    print("="*70)
    print("ERP 导出文件列表查询工具")
    print("="*70)
    
    # 【安全检查】获取用户凭证
    phone, password = get_user_credentials()
    
    if not phone or not password:
        print("\n" + "="*70)
        print("❌ 错误：未找到 ERP 登录凭证")
        print("="*70)
        print("\n💡 请配置凭证后重试:")
        print("   1. 编辑：~/.openclaw/workspace/configs/erp-credentials.env")
        print("   2. 添加:")
        print("      ERP_USERNAME=你的手机号")
        print("      ERP_PASSWORD=你的密码")
        print("="*70)
        return
    
    # 创建客户端
    print(f"\n使用账号：{phone}")
    client = ERPAPIClient(
        phone=phone,
        password=password
    )
    
    # 登录
    if not client.login():
        print("\n❌ 登录失败")
        return
    
    # 获取用户信息
    print("\n获取用户信息...")
    user_info = client.get_user_info()
    if user_info:
        print(f"✅ 用户：{user_info.get('userName')}")
        if user_info.get('organName'):
            print(f"   组织：{user_info.get('organName')}")
    
    # 查询最近 30 天的导出文件
    print("\n" + "="*70)
    print("查询最近 30 天的导出文件")
    print("="*70)
    result = client.get_export_file_list()
    
    if result and (result.get('succeed') or result.get('code') == '200'):
        data = result.get('data', [])
        
        # data 可能是列表或包含 records 的对象
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            records = data.get('records', [])
        else:
            records = []
        
        if records:
            print("\n" + "="*70)
            print("📋 导出文件详情")
            print("="*70)
            
            for i, file in enumerate(records, 1):
                print(f"\n{i}. {file.get('fileName', '未知文件')}")
                print(f"   状态：{file.get('status', 'N/A')}")
                print(f"   创建时间：{file.get('createTime', 'N/A')}")
                print(f"   文件大小：{file.get('fileSize', 'N/A')} 字节")
                print(f"   导出 ID: {file.get('id', 'N/A')}")
        else:
            print("\n⚠️ 没有找到导出文件")
    
    print("\n" + "="*70)
    print("💡 提示:")
    print("1. 状态为 '1' 表示导出完成，可以下载")
    print("2. 状态为 '0' 表示正在生成中")
    print("3. 使用 create-custom-export.py 创建新的导出任务")
    print("="*70)

if __name__ == "__main__":
    main()
