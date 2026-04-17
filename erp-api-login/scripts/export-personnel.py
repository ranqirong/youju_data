#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ERP 人事数据导出工具
导出人事数据 Excel 文件
"""

import sys
import os
from pathlib import Path

# 添加脚本目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# 导入 ERP API 客户端
try:
    import importlib.util
    erp_export_path = os.path.join(script_dir, 'erp-export.py')
    spec = importlib.util.spec_from_file_location("erp_export", erp_export_path)
    erp_export = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(erp_export)
    ERPAPIClient = erp_export.ERPAPIClient
    get_user_credentials = erp_export.get_user_credentials
except Exception as e:
    print('❌ 无法加载 ERP API 客户端：{}'.format(e))
    sys.exit(1)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ERP 人事数据导出工具')
    
    parser.add_argument('--brand-id', type=str, default='625864877560328320',
                       help='品牌 ID')
    parser.add_argument('--branch-ids', type=str, nargs='*',
                       help='分支机构 ID 列表')
    parser.add_argument('--output-dir', type=str, default='~/Desktop/ERP 导出',
                       help='输出目录')
    
    args = parser.parse_args()
    
    print('='*70)
    print('ERP 人事数据导出工具')
    print('='*70)
    print()
    
    # 获取用户凭证
    phone, password = get_user_credentials()
    if not phone or not password:
        print('❌ 未找到 ERP 登录凭证')
        print('   请运行：python3 setup-credentials.py')
        return
    
    print('使用账号：{}'.format(phone))
    
    # 登录
    client = ERPAPIClient(phone=phone, password=password)
    
    if not client.login():
        print('❌ 登录失败')
        return
    
    user_info = client.get_user_info()
    if not user_info:
        print('❌ 用户信息获取失败')
        return
    
    print('✅ 用户：{}'.format(user_info.get('userName', phone)))
    print()
    
    # 导出人事数据
    print('导出人事数据...')
    
    result = client.export_personnel_data(
        brand_id=args.brand_id,
        branch_ids=args.branch_ids,
        output_dir=args.output_dir
    )
    
    if result and result.get('success'):
        print()
        print('='*70)
        print('✅ 导出完成!')
        print('='*70)
        print()
        print('📁 输出文件：{}'.format(result.get('file')))
        print('📊 数据大小：{:,} 字节'.format(result.get('size', 0)))
        print()
    else:
        print()
        print('='*70)
        print('❌ 导出失败')
        print('='*70)
        if result:
            print('错误：{}'.format(result.get('error', '未知错误')))


if __name__ == '__main__':
    main()
