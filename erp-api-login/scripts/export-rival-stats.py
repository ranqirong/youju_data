#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ERP 竞对数据导出工具
导出竞争对手对比数据
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
    
    parser = argparse.ArgumentParser(description='ERP 竞对数据导出工具')
    
    parser.add_argument('--summary-type', type=int, default=1, choices=[1, 2],
                       help='统计类型 (1: 按项目，2: 按区域)')
    parser.add_argument('--start-date', type=str, default=None,
                       help='开始日期 (YYYY-MM-DD)，默认 30 天前')
    parser.add_argument('--end-date', type=str, default=None,
                       help='结束日期 (YYYY-MM-DD)，默认为今天')
    parser.add_argument('--dept-ids', type=str, nargs='*',
                       default=['625864877560328320'],
                       help='部门 ID 列表')
    parser.add_argument('--rival-ids', type=str, nargs='*',
                       help='竞对公司 ID 列表')
    parser.add_argument('--file-name', type=str, default='竞对数据导出',
                       help='导出文件名')
    parser.add_argument('--output-dir', type=str, default='~/Desktop/ERP 导出',
                       help='输出目录')
    
    args = parser.parse_args()
    
    print('='*70)
    print('ERP 竞对数据导出工具')
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
    start_inclusive = int(start_dt.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    end_exclusive = int((end_dt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    
    print('统计时间范围:')
    print('  开始：{} ({})'.format(args.start_date or '30 天前', start_dt.strftime('%Y-%m-%d')))
    print('  结束：{} ({})'.format(args.end_date or '今天', end_dt.strftime('%Y-%m-%d')))
    print()
    
    # 导出竞对数据
    print('步骤 1: 创建导出任务...')
    
    result = client.export_rival_stats(
        summary_type=args.summary_type,
        dept_ids=args.dept_ids,
        rival_ids=args.rival_ids,
        start_inclusive=start_inclusive,
        end_exclusive=end_exclusive,
        file_name=args.file_name,
        output_dir=args.output_dir
    )
    
    if not result or not result.get('success'):
        print('❌ 导出任务创建失败')
        return
    
    print()
    
    # 等待几秒后获取文件列表
    print('步骤 2: 获取导出文件列表...')
    print('  （等待导出完成）')
    
    import time
    time.sleep(3)
    
    file_list_result = client.get_export_file_list(
        start_time=start_inclusive,
        end_time=end_exclusive,
        output_dir=args.output_dir
    )
    
    if file_list_result and file_list_result.get('success'):
        files = file_list_result.get('files', [])
        
        # 查找最新的竞对数据文件
        rival_files = [f for f in files if '竞对' in f.get('fileName', '') or 'rival' in f.get('fileName', '').lower()]
        
        if rival_files:
            latest_file = sorted(rival_files, key=lambda x: x.get('createTime', ''), reverse=True)[0]
            
            print()
            print('='*70)
            print('✅ 导出完成!')
            print('='*70)
            print()
            print('📊 导出文件信息:')
            print('  文件名：{}'.format(latest_file.get('fileName', '未知')))
            print('  创建时间：{}'.format(latest_file.get('createTime', '未知')))
            print('  状态：{}'.format(latest_file.get('status', '未知')))
            print('  大小：{} 字节'.format(latest_file.get('fileSize', '未知')))
            print()
            print('💡 提示：请登录 ERP 系统下载文件，或查看 ~/Desktop/ERP 导出/ 目录')
        else:
            print()
            print('⚠️ 未找到竞对数据文件，请稍后在 ERP 系统中查看')
    else:
        print('⚠️ 获取文件列表失败')
    
    print()


if __name__ == '__main__':
    main()
