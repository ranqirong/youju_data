#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ERP 新房带看数据导出工具
导出新房带看记录列表
"""

import sys
import os
from datetime import datetime, timedelta
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
    
    parser = argparse.ArgumentParser(description='ERP 新房带看数据导出工具')
    
    parser.add_argument('--start-date', type=str, default=None,
                       help='带看开始日期 (YYYY-MM-DD)，默认 30 天前')
    parser.add_argument('--end-date', type=str, default=None,
                       help='带看结束日期 (YYYY-MM-DD)，默认为今天')
    parser.add_argument('--page-no', type=int, default=1,
                       help='页码')
    parser.add_argument('--page-size', type=int, default=100,
                       help='每页数量')
    parser.add_argument('--phone-flag', type=int, default=1, choices=[0, 1],
                       help='手机号显示标识 (1: 显示，0: 隐藏)')
    parser.add_argument('--output-dir', type=str, default='~/Desktop/ERP 导出',
                       help='输出目录')
    
    args = parser.parse_args()
    
    print('='*70)
    print('ERP 新房带看数据导出工具')
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
    
    # 确定日期范围
    if args.end_date:
        end_dt = datetime.strptime(args.end_date, '%Y-%m-%d')
    else:
        end_dt = datetime.now()
    
    if args.start_date:
        start_dt = datetime.strptime(args.start_date, '%Y-%m-%d')
    else:
        start_dt = end_dt - timedelta(days=30)
    
    # 转换为时间戳（毫秒）
    visit_start_tm = int(start_dt.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    visit_end_tm = int(end_dt.replace(hour=23, minute=59, second=59, microsecond=999999).timestamp() * 1000)
    
    print('带看时间范围:')
    print('  开始：{} ({})'.format(args.start_date or '30 天前', start_dt.strftime('%Y-%m-%d')))
    print('  结束：{} ({})'.format(args.end_date or '今天', end_dt.strftime('%Y-%m-%d')))
    print()
    
    # 导出带看数据
    result = client.export_visit_list(
        visit_start_tm=visit_start_tm,
        visit_end_tm=visit_end_tm,
        page_no=args.page_no,
        page_size=args.page_size,
        phone_flag=args.phone_flag,
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
    else:
        print()
        print('='*70)
        print('❌ 导出失败')
        print('='*70)
        if result:
            print('错误：{}'.format(result.get('error', '未知错误')))


if __name__ == '__main__':
    main()
