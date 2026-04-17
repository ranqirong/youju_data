#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ERP 项目明细导出工具
导出新房项目明细列表
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

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
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ERP 项目明细导出工具')
    
    parser.add_argument('--sale-status', type=int, default=1,
                       choices=[1, 2, 3, 4],
                       help='销售状态 (1: 在售，2: 待售，3: 售罄，4: 停售)')
    parser.add_argument('--page-no', type=int, default=1,
                       help='页码')
    parser.add_argument('--page-size', type=int, default=100,
                       help='每页数量')
    parser.add_argument('--proxy-id', type=str, default='625864877560328320',
                       help='代理 ID')
    parser.add_argument('--buz-id', type=int, default=1,
                       help='业务 ID')
    parser.add_argument('--output-dir', type=str, default='~/Desktop/ERP 导出',
                       help='输出目录')
    parser.add_argument('--project-manager-dept', type=str, nargs='*',
                       help='项目部经理部门 ID 列表')
    parser.add_argument('--onsite-dept', type=str, nargs='*',
                       help='驻场部门 ID 列表')
    parser.add_argument('--district-codes', type=str, nargs='*',
                       help='区域代码列表')
    
    args = parser.parse_args()
    
    print('='*70)
    print('ERP 项目明细导出工具')
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
    
    # 导出项目明细
    result = client.export_project_list(
        sale_status=args.sale_status,
        project_manager_dept_list=args.project_manager_dept,
        onsite_dept_list=args.onsite_dept,
        page_no=args.page_no,
        page_size=args.page_size,
        proxy_id=args.proxy_id,
        buz_id=args.buz_id,
        district_codes=args.district_codes,
        output_dir=args.output_dir
    )
    
    if result and result.get('success'):
        print()
        print('='*70)
        print('✅ 导出完成!')
        print('='*70)
        print()
        print('📊 数据摘要:')
        print('   记录数：{}'.format(result.get('records', 0)))
        print('   总数：{}'.format(result.get('total', 0)))
        print()
        print('📁 输出文件：{}'.format(result.get('file')))
        
        # 显示前 5 条记录
        data = result.get('data', {})
        records = data.get('records', [])
        
        if records:
            print()
            print('前 5 条记录预览:')
            for i, record in enumerate(records[:5], 1):
                print()
                print('  记录{}:'.format(i))
                # 显示关键字段
                for key in ['projectName', 'projectAddress', 'saleStatus', 'projectManager']:
                    if key in record:
                        print('    {}: {}'.format(key, record[key]))
    else:
        print()
        print('='*70)
        print('❌ 导出失败')
        print('='*70)
        if result:
            print('错误：{}'.format(result.get('error', '未知错误')))


if __name__ == '__main__':
    main()
