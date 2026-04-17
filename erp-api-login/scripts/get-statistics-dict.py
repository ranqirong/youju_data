#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取 ERP 统计指标字典
用于查看可用的统计指标配置
"""

import sys
import os
import importlib.util

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
    print("ERP 统计指标字典查询工具")
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
    
    # 获取指标字典
    dict_data = client.get_statistics_dict()
    
    if dict_data:
        print("\n" + "="*70)
        print("✅ 指标字典获取成功！")
        print("="*70)
        
        data = dict_data.get('data', [])
        print(f"指标分类数量：{len(data)}")
        
        # 打印每个分类的详细信息
        for i, item in enumerate(data, 1):
            top_name = item.get('topName', '未知分类')
            select_items = item.get('selectItemVoList', [])
            print(f"\n{i}. {top_name} ({len(select_items)} 个指标)")
            
            # 打印前 5 个指标
            for j, metric in enumerate(select_items[:5], 1):
                code_name = metric.get('codeName', '未知')
                code = metric.get('code', 'N/A')
                has_child = "有子项" if metric.get('hasChild') else "无子项"
                print(f"   {j}. {code_name} [代码：{code}] [{has_child}]")
            
            if len(select_items) > 5:
                print(f"   ... 还有 {len(select_items) - 5} 个指标")
        
        print("\n" + "="*70)
        print("💡 提示：指标代码可用于自定义统计报表配置")
        print("="*70)

if __name__ == "__main__":
    main()
