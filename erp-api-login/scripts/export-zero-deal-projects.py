#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
0 成交项目明细统计工具
统计本月未有认购的项目明细，按区域组别、项目部层级分组
"""

import sys
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

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


def normalize_date(date_str):
    """标准化日期格式为 YYYY-MM-DD"""
    if not date_str:
        return ''
    formats = ['%Y/%m/%d', '%Y-%m-%d', '%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M:%S']
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str[:len(fmt.replace('%', '').replace(' ', ''))+fmt.count(' ')], fmt)
            return dt.strftime('%Y-%m-%d')
        except:
            continue
    if len(date_str) >= 10:
        return date_str[:10].replace('/', '-')
    return date_str


def get_month_range(date_str=None):
    """获取指定日期所在月的起止日期"""
    if date_str:
        try:
            dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
        except:
            dt = datetime.now()
    else:
        dt = datetime.now()
    
    month_start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if dt.month == 12:
        month_end = dt.replace(year=dt.year+1, month=1, day=1) - timedelta(seconds=1)
    else:
        month_end = dt.replace(month=dt.month+1, day=1) - timedelta(seconds=1)
    
    return month_start.strftime('%Y-%m-%d'), month_end.strftime('%Y-%m-%d')


def export_zero_deal_projects(sale_status=1, month=None, output_dir=None):
    """
    导出 0 成交项目明细
    
    Args:
        sale_status: 销售状态 (1: 在售)
        month: 统计月份 (YYYY-MM)
        output_dir: 输出目录
    """
    from datetime import datetime
    import zipfile
    import xml.etree.ElementTree as ET
    import re
    import pandas as pd
    
    print('='*80)
    print('0 成交项目明细统计')
    print('='*80)
    print()
    
    # 获取用户凭证
    phone, password = get_user_credentials()
    if not phone or not password:
        print('❌ 未找到 ERP 登录凭证')
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
    
    # 确定统计月份
    if month:
        month_str = month
    else:
        month_str = datetime.now().strftime('%Y-%m')
    
    month_start, month_end = get_month_range(month_str + '-01')
    
    print('统计月份：{}'.format(month_str))
    print('时间段：{} ~ {}'.format(month_start, month_end))
    print()
    
    # 步骤 1: 导出项目明细
    print('步骤 1: 导出项目明细...')
    project_result = client.export_project_list(
        sale_status=sale_status,
        page_size=1000,
        output_dir=output_dir
    )
    
    if not project_result or not project_result.get('success'):
        print('❌ 项目明细导出失败')
        return
    
    # 加载项目明细数据（Excel 格式）
    project_file = project_result.get('file')
    print('  项目明细文件：{}'.format(project_file))
    
    # 读取 Excel 文件
    projects = []
    try:
        import pandas as pd
        df = pd.read_excel(project_file)
        print('  读取项目：{} 个\n'.format(len(df)))
        
        # 转换为字典列表
        for _, row in df.iterrows():
            project = {}
            for col in df.columns:
                project[col] = row[col] if pd.notna(row[col]) else ''
            projects.append(project)
    except Exception as e:
        print('  ⚠️ 读取项目明细失败：{}'.format(e))
        return
    
    # 步骤 2: 导出本月新房合同数据
    print('步骤 2: 导出本月新房合同数据...')
    
    from datetime import datetime
    start_dt = datetime.strptime(month_start, '%Y-%m-%d')
    end_dt = datetime.strptime(month_end, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    
    query_start_ts = int(start_dt.timestamp() * 1000)
    query_end_ts = int(end_dt.timestamp() * 1000)
    
    contract_result = client.export_new_house_contracts(
        start_time=query_start_ts,
        end_time=query_end_ts,
        sign_tm_start=query_start_ts,
        sign_tm_end=query_end_ts,
        city_code='450100',
        organ_id='625864877560328320',
        output_dir=output_dir
    )
    
    if not contract_result or not contract_result.get('success'):
        print('❌ 合同数据导出失败')
        return
    
    # 步骤 3: 加载合同数据
    print('\n步骤 3: 分析合同数据...')
    
    contract_file = contract_result.get('file')
    
    # 字段名（无空格）
    F_DEPT_L1 = b'\xe9\xa1\xb9\xe7\x9b\xae\xe9\x83\xa8\xe5\xb1\x82\xe7\xba\xa71'.decode('utf-8')
    F_DEPT_L2 = b'\xe9\xa1\xb9\xe7\x9b\xae\xe9\x83\xa8\xe5\xb1\x82\xe7\xba\xa72'.decode('utf-8')
    F_BUILDING = '楼盘名称'
    
    ns = {'ss': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    
    projects_with_deals = set()  # 有成交的项目集合
    
    try:
        with zipfile.ZipFile(contract_file, 'r') as z:
            sheet_file = 'xl/worksheets/sheet2.xml'
            if sheet_file in z.namelist():
                xml_content = z.read(sheet_file)
                xml_content = re.sub(b'<ss:autoFilter[^>]*/>', b'', xml_content)
                
                root = ET.fromstring(xml_content)
                rows = root.findall('.//ss:row', ns)
                
                if rows:
                    # 读取表头
                    headers = []
                    header_row = rows[0]
                    header_cells = header_row.findall('ss:c', ns)
                    for cell in header_cells:
                        text = ''
                        t_elem = cell.find('ss:is/ss:t', ns)
                        if t_elem is not None and t_elem.text:
                            text = t_elem.text
                        else:
                            v_elem = cell.find('ss:v', ns)
                            if v_elem is not None and v_elem.text:
                                text = v_elem.text
                        headers.append(text)
                    
                    # 找到楼盘名称列
                    building_idx = headers.index(F_BUILDING) if F_BUILDING in headers else -1
                    
                    if building_idx >= 0:
                        # 读取数据，收集有成交的楼盘
                        for row in rows[1:]:
                            cells = row.findall('ss:c', ns)
                            if building_idx < len(cells):
                                cell = cells[building_idx]
                                val = ''
                                v_elem = cell.find('ss:v', ns)
                                if v_elem is not None and v_elem.text:
                                    val = v_elem.text
                                else:
                                    t_elem = cell.find('ss:is/ss:t', ns)
                                    if t_elem is not None and t_elem.text:
                                        val = t_elem.text
                                
                                if val:
                                    projects_with_deals.add(val)
        
        print('  本月有成交的项目：{} 个'.format(len(projects_with_deals)))
    except Exception as e:
        print('  ⚠️ 读取合同数据失败：{}'.format(e))
    
    print()
    
    # 步骤 4: 筛选 0 成交项目
    print('步骤 4: 筛选 0 成交项目...')
    
    # 显示项目明细的列名（调试用）
    if projects:
        print('  项目明细列名：{}'.format(list(projects[0].keys())[:10]))
    
    zero_deal_projects = []
    
    for project in projects:
        # 尝试多种字段名
        project_name = project.get('projectName', '') or project.get('楼盘名称', '') or project.get('项目名称', '')
        
        # 检查是否在成交项目中
        if project_name and project_name not in projects_with_deals:
            # 提取需要的字段（根据实际 Excel 列名）
            zero_deal_projects.append({
                '区域': project.get('所在区域', '') or project.get('区域', '') or project.get('行政区', ''),
                '项目部层级 2': project.get('项目经理', '').split('/')[0] if project.get('项目经理', '') else '',  # 从项目经理提取
                '项目部层级 1': project.get('驻场', '').split('/')[0] if project.get('驻场', '') else '',  # 从驻场提取
                '楼盘名称': project_name,
                '项目地址': '',
                '销售状态': project.get('售卖状态', '') or project.get('销售状态', '') or project.get('状态', ''),
                '物业类型': project.get('物业类型', '') or project.get('类型', ''),
                '上架时间': project.get('认领时间', '') or project.get('上架时间', '') or project.get('时间', ''),
            })
    
    print('  0 成交项目：{} 个'.format(len(zero_deal_projects)))
    print()
    
    # 步骤 5: 去重（同一楼盘多个物业类型只算 1 个）
    print('步骤 5: 去重处理（同一楼盘只计算 1 次）...')
    
    unique_buildings = set()
    unique_projects = []
    
    for proj in zero_deal_projects:
        building = proj['楼盘名称']
        if building not in unique_buildings:
            unique_buildings.add(building)
            unique_projects.append(proj)
    
    print('  去重后项目：{} 个'.format(len(unique_projects)))
    print()
    
    # 步骤 6: 导出结果
    print('步骤 6: 导出结果...')
    
    output_dir = Path(output_dir or '~/Desktop/ERP 导出').expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / '0 成交项目明细_{}_{}.xlsx'.format(month_str.replace('-', ''), timestamp)
    
    try:
        df = pd.DataFrame(unique_projects)
        # 选择需要的列
        columns = ['区域', '项目部层级 2', '项目部层级 1', '楼盘名称', '项目地址', '销售状态', '物业类型', '上架时间']
        df = df[[c for c in columns if c in df.columns]]
        df.to_excel(output_file, index=False)
        
        print('  ✅ 导出成功：{}'.format(output_file))
        print('  记录数：{}'.format(len(unique_projects)))
    except Exception as e:
        print('  ❌ 导出失败：{}'.format(e))
        return
    
    print()
    
    # 步骤 7: 统计汇总
    print('步骤 7: 统计汇总...')
    print()
    
    # 按区域统计
    region_stats = defaultdict(list)
    for proj in unique_projects:
        region = proj.get('区域', '未知')
        region_stats[region].append(proj)
    
    print('按区域统计:')
    for region, projs in sorted(region_stats.items()):
        print('  {}: {} 个项目'.format(region, len(projs)))
    
    print()
    
    # 按项目部层级 2 统计
    dept_l2_stats = defaultdict(list)
    for proj in unique_projects:
        dept_l2 = proj.get('项目部层级 2', '未知')
        dept_l2_stats[dept_l2].append(proj)
    
    print('按项目部层级 2 统计:')
    for dept_l2, projs in sorted(dept_l2_stats.items()):
        print('  {}: {} 个项目'.format(dept_l2, len(projs)))
    
    print()
    print('='*80)
    print('✅ 完成!')
    print('='*80)
    print()
    print('📊 统计摘要:')
    print('  统计月份：{}'.format(month_str))
    print('  总项目数：{}'.format(len(projects)))
    print('  有成交项目：{} 个'.format(len(projects_with_deals)))
    print('  0 成交项目：{} 个'.format(len(unique_projects)))
    print()
    print('📁 输出文件：{}'.format(output_file))
    print()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='0 成交项目明细统计工具')
    
    parser.add_argument('--sale-status', type=int, default=1,
                       choices=[1, 2, 3, 4],
                       help='销售状态 (1: 在售，2: 待售，3: 售罄，4: 停售)')
    parser.add_argument('--month', type=str, default=None,
                       help='统计月份 (YYYY-MM)，默认为当前月')
    parser.add_argument('--output-dir', type=str, default='~/Desktop/ERP 导出',
                       help='输出目录')
    
    args = parser.parse_args()
    
    export_zero_deal_projects(
        sale_status=args.sale_status,
        month=args.month,
        output_dir=args.output_dir
    )


if __name__ == '__main__':
    main()
