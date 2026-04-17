#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建自定义统计报表导出
支持选择指标、时间范围、筛选条件等
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
    print("ERP 自定义报表导出工具")
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
    
    # 示例 1: 使用默认配置创建导出
    print("\n" + "="*70)
    print("示例 1: 使用默认配置创建导出")
    print("="*70)
    result1 = client.create_custom_export()
    
    # 示例 2: 自定义时间范围
    print("\n" + "="*70)
    print("示例 2: 自定义时间范围（最近 7 天）")
    print("="*70)
    start_time = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
    end_time = int(datetime.now().timestamp() * 1000)
    file_name = datetime.now().strftime('%Y-%m-%d') + "最近 7 天报表"
    
    result2 = client.create_custom_export(
        start_time=start_time,
        end_time=end_time,
        file_name=file_name
    )
    
    # 示例 3: 自定义指标
    print("\n" + "="*70)
    print("示例 3: 自定义指标（在职人数 + 门店数）")
    print("="*70)
    custom_metrics = [
        {"codeName": "在职人数", "topCodeName": "人事指标", "code": "5", "hasChild": 1, "percentDisplay": 0, "childNodes": [
            {"codeName": "合计", "topCodeName": "在职人数", "code": "5", "percentDisplay": 0},
            {"codeName": "直营", "topCodeName": "在职人数", "code": "5_2", "percentDisplay": 0}
        ]},
        {"codeName": "门店数", "topCodeName": "门店指标", "code": "29", "hasChild": 1, "childNodes": [
            {"codeName": "营业", "topCodeName": "门店数", "code": "36", "percentDisplay": 0}
        ]}
    ]
    
    result3 = client.create_custom_export(
        agent_code_queries=custom_metrics,
        file_name=datetime.now().strftime('%Y-%m-%d') + "自定义指标报表"
    )
    
    print("\n" + "="*70)
    print("✅ 自定义报表导出任务创建完成！")
    print("="*70)
    print("\n💡 提示:")
    print("1. 导出任务创建后，系统会在后台生成文件")
    print("2. 使用 get-export-list.py 查看导出进度和下载文件")
    print("3. 大文件可能需要几分钟生成时间")

if __name__ == "__main__":
    main()
