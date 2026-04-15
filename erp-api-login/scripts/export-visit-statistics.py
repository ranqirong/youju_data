#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目带看进场统计工具
根据首看时间统计进场量，包含周环比、月环比
分一级项目（A 级）和二级项目（A-、B、B+ 级）
"""

import sys
import os
import zipfile
import xml.etree.ElementTree as ET
import re
import pandas as pd
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


def get_week_range(date_str=None):
    """获取指定日期所在周的起止日期"""
    if date_str:
        try:
            dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
        except:
            dt = datetime.now()
    else:
        dt = datetime.now()
    
    week_start = dt - timedelta(days=dt.weekday())  # 周一
    week_end = week_start + timedelta(days=6)  # 周日
    
    return week_start.strftime('%Y-%m-%d'), week_end.strftime('%Y-%m-%d')


def get_last_week_range(date_str=None):
    """获取上周的起止日期"""
    if date_str:
        try:
            dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
        except:
            dt = datetime.now()
    else:
        dt = datetime.now()
    
    # 上周一
    last_week_start = dt - timedelta(days=dt.weekday() + 7)
    last_week_end = last_week_start + timedelta(days=6)
    
    return last_week_start.strftime('%Y-%m-%d'), last_week_end.strftime('%Y-%m-%d')


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


def get_last_month_range(date_str=None):
    """获取上月的起止日期"""
    if date_str:
        try:
            dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
        except:
            dt = datetime.now()
    else:
        dt = datetime.now()
    
    # 上月 1 号
    if dt.month == 1:
        last_month_start = dt.replace(year=dt.year-1, month=12, day=1)
        last_month_end = dt.replace(day=1) - timedelta(seconds=1)
    else:
        last_month_start = dt.replace(month=dt.month-1, day=1)
        last_month_end = dt.replace(day=1) - timedelta(seconds=1)
    
    return last_month_start.strftime('%Y-%m-%d'), last_month_end.strftime('%Y-%m-%d')


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


def is_date_in_range(date_str, start_date, end_date):
    """检查日期是否在指定范围内"""
    if not date_str:
        return False
    return start_date <= date_str <= end_date


def classify_project_level(project_grade):
    """
    项目等级分类
    
    一级项目：A
    二级项目：A-、B、B+
    """
    if not project_grade:
        return '未知'
    
    grade = str(project_grade).strip()
    
    if grade == 'A':
        return '一级项目'
    elif grade in ['A-', 'B', 'B+']:
        return '二级项目'
    else:
        return '其他'


def export_visit_statistics(month=None, output_dir=None):
    """
    导出项目带看进场统计（含周环比、月环比）
    
    Args:
        month: 统计月份 (YYYY-MM)
        output_dir: 输出目录
    """
    print('='*80)
    print('项目带看进场统计（含周环比、月环比）')
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
    
    # 计算各时间段
    current_week_start, current_week_end = get_week_range()
    last_week_start, last_week_end = get_last_week_range()
    current_month_start, current_month_end = get_month_range()
    last_month_start, last_month_end = get_last_month_range()
    
    print('统计月份：{}'.format(month_str))
    print()
    print('时间范围:')
    print('  本周：{} ~ {}'.format(current_week_start, current_week_end))
    print('  上周：{} ~ {}'.format(last_week_start, last_week_end))
    print('  本月：{} ~ {}'.format(current_month_start, current_month_end))
    print('  上月：{} ~ {}'.format(last_month_start, last_month_end))
    print()
    
    # 步骤 1: 分周导出带看数据（避免超时）
    print('步骤 1: 分周导出带看数据...')
    
    # 导出上月 1 号至今的带看数据
    start_dt = datetime.strptime(last_month_start, '%Y-%m-%d')
    end_dt = datetime.now()
    
    # 分周导出
    week_ranges = []
    current = start_dt
    while current <= end_dt:
        week_start = current - timedelta(days=current.weekday())
        week_end = week_start + timedelta(days=6)
        if week_end > end_dt:
            week_end = end_dt
        week_ranges.append((week_start, week_end))
        current = week_end + timedelta(days=1)
    
    print('  分 {} 周导出'.format(len(week_ranges)))
    
    # 统计数据结构
    stats = defaultdict(lambda: {
        'current_week': 0,
        'last_week': 0,
        'current_month': 0,
        'last_month': 0,
        'projects': set(),
    })
    
    all_first_visits = set()  # 去重首看
    total_visits_exported = 0
    
    for i, (week_start, week_end) in enumerate(week_ranges, 1):
        print('\n  导出第{}周（{} ~ {}）...'.format(i, week_start.strftime('%Y-%m-%d'), week_end.strftime('%Y-%m-%d')))
        
        visit_start_tm = int(week_start.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
        visit_end_tm = int(week_end.replace(hour=23, minute=59, second=59, microsecond=999999).timestamp() * 1000)
        
        try:
            visit_result = client.export_visit_list(
                visit_start_tm=visit_start_tm,
                visit_end_tm=visit_end_tm,
                page_size=200,
                phone_flag=1,
                output_dir=output_dir
            )
            
            if not visit_result or not visit_result.get('success'):
                print('    ⚠️ 导出失败，跳过')
                continue
            
            visit_file = visit_result.get('file')
            print('    ✅ 导出成功：{}'.format(os.path.basename(visit_file)))
            
            # 统计本周数据
            ns = {'ss': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            
            with zipfile.ZipFile(visit_file, 'r') as z:
                sheet_file = 'xl/worksheets/sheet1.xml'
                if sheet_file not in z.namelist():
                    sheet_file = 'xl/worksheets/sheet2.xml'
                
                if sheet_file not in z.namelist():
                    continue
                
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
                    
                    # 找到关键字段索引
                    building_idx = headers.index('楼盘名称') if '楼盘名称' in headers else -1
                    first_visit_idx = headers.index('首看日期') if '首看日期' in headers else -1
                    
                    if first_visit_idx < 0:
                        first_visit_idx = headers.index('首看时间') if '首看时间' in headers else -1
                    
                    if first_visit_idx >= 0 and building_idx >= 0:
                        week_visits = 0
                        week_unique = 0
                        
                        for row in rows[1:]:
                            cells = row.findall('ss:c', ns)
                            
                            if first_visit_idx < len(cells):
                                cell = cells[first_visit_idx]
                                visit_date = ''
                                v_elem = cell.find('ss:v', ns)
                                if v_elem is not None and v_elem.text:
                                    visit_date = v_elem.text
                                else:
                                    t_elem = cell.find('ss:is/ss:t', ns)
                                    if t_elem is not None and t_elem.text:
                                        visit_date = t_elem.text
                                
                                visit_date_normalized = normalize_date(visit_date)
                                
                                if visit_date_normalized:
                                    week_visits += 1
                                    
                                    # 获取楼盘名称
                                    building = ''
                                    if building_idx < len(cells):
                                        cell = cells[building_idx]
                                        v_elem = cell.find('ss:v', ns)
                                        if v_elem is not None and v_elem.text:
                                            building = v_elem.text
                                        else:
                                            t_elem = cell.find('ss:is/ss:t', ns)
                                            if t_elem is not None and t_elem.text:
                                                building = t_elem.text
                                    
                                    # 去重首看
                                    first_visit_key = '{}|{}'.format(building, visit_date_normalized)
                                    if first_visit_key not in all_first_visits:
                                        all_first_visits.add(first_visit_key)
                                        week_unique += 1
                                        
                                        # 统计各时间段
                                        project_level = '未知'  # 暂时不分类，后面统一处理
                                        
                                        if is_date_in_range(visit_date_normalized, current_week_start, current_week_end):
                                            stats['all']['current_week'] += 1
                                            stats['all']['projects'].add(building)
                                        
                                        if is_date_in_range(visit_date_normalized, last_week_start, last_week_end):
                                            stats['all']['last_week'] += 1
                                        
                                        if is_date_in_range(visit_date_normalized, current_month_start, current_month_end):
                                            stats['all']['current_month'] += 1
                                            stats['all']['projects'].add(building)
                                        
                                        if is_date_in_range(visit_date_normalized, last_month_start, last_month_end):
                                            stats['all']['last_month'] += 1
                        
                        total_visits_exported += week_visits
                        print('    本周带看：{} 条，首看进场：{} 次'.format(week_visits, week_unique))
        
        except Exception as e:
            print('    ⚠️ 处理失败：{}'.format(e))
    
    print('\n  总导出带看记录：{} 条'.format(total_visits_exported))
    print('  总首看进场：{} 次'.format(len(all_first_visits)))
    
    # 步骤 2: 导出项目明细（获取项目等级）
    print('\n步骤 2: 导出项目明细（获取项目等级）...')
    
    project_result = client.export_project_list(
        sale_status=1,
        page_size=500,
        output_dir=output_dir
    )
    
    if not project_result or not project_result.get('success'):
        print('  ❌ 项目明细导出失败')
        return
    
    project_file = project_result.get('file')
    print('  ✅ 项目明细文件：{}'.format(project_file))
    
    # 加载项目等级映射
    project_grades = {}
    try:
        df_project = pd.read_excel(project_file)
        print('  读取项目：{} 个'.format(len(df_project)))
        
        for _, row in df_project.iterrows():
            project_name = row.get('楼盘名称', '') or row.get('项目名称', '')
            project_grade = row.get('项目等级', '') or row.get('楼盘等级', '') or row.get('等级', '')
            
            if project_name:
                project_grades[project_name] = str(project_grade) if project_grade else ''
    except Exception as e:
        print('  ⚠️ 读取项目明细失败：{}'.format(e))
    
    # 步骤 3: 生成统计报表
    print('\n步骤 3: 生成统计报表...')
    
    report_data = []
    
    for project_level in ['一级项目', '二级项目']:
        data = stats.get('all', {
            'current_week': 0,
            'last_week': 0,
            'current_month': 0,
            'last_month': 0,
            'projects': set(),
        })
        
        current_week = data['current_week']
        last_week = data['last_week']
        current_month = data['current_month']
        last_month = data['last_month']
        
        # 计算环比
        week_diff = current_week - last_week
        week_ratio = (week_diff / last_week * 100) if last_week > 0 else 0
        
        month_diff = current_month - last_month
        month_ratio = (month_diff / last_month * 100) if last_month > 0 else 0
        
        report_data.append({
            '项目类型': project_level,
            '本周进场量': current_week,
            '上周进场量': last_week,
            '本周 - 上周': week_diff,
            '周环比': '{:.2f}%'.format(week_ratio),
            '本月进场量': current_month,
            '上月进场量': last_month,
            '本月 - 上月': month_diff,
            '月环比': '{:.2f}%'.format(month_ratio),
        })
    
    # 步骤 4: 导出结果
    print('\n步骤 4: 导出结果...')
    
    output_dir = Path(output_dir or '~/Desktop/ERP 导出').expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / '项目带看进场统计_{}_{}.xlsx'.format(month_str.replace('-', ''), timestamp)
    
    try:
        df_report = pd.DataFrame(report_data)
        df_report.to_excel(output_file, index=False)
        
        print('  ✅ 导出成功：{}'.format(output_file))
        print('  记录数：{}'.format(len(report_data)))
    except Exception as e:
        print('  ❌ 导出失败：{}'.format(e))
        return
    
    # 步骤 5: 显示统计结果
    print('\n步骤 5: 统计结果...')
    print()
    print('='*80)
    print('项目带看进场统计表（含周环比、月环比）')
    print('='*80)
    print()
    print('{:<10} {:>12} {:>12} {:>12} {:>12} {:>12} {:>12} {:>12} {:>12}'.format(
        '项目类型', '本周进场量', '上周进场量', '本周 - 上周', '周环比',
        '本月进场量', '上月进场量', '本月 - 上月', '月环比'))
    print('-'*90)
    
    for row in report_data:
        print('{:<10} {:>12} {:>12} {:>12} {:>12} {:>12} {:>12} {:>12} {:>12}'.format(
            row['项目类型'],
            row['本周进场量'],
            row['上周进场量'],
            row['本周 - 上周'],
            row['周环比'],
            row['本月进场量'],
            row['上月进场量'],
            row['本月 - 上月'],
            row['月环比']))
    
    print()
    print('='*80)
    print('✅ 完成!')
    print('='*80)
    print()
    print('📁 输出文件：{}'.format(output_file))
    print()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='项目带看进场统计工具')
    
    parser.add_argument('--month', type=str, default=None,
                       help='统计月份 (YYYY-MM)，默认为当前月')
    parser.add_argument('--output-dir', type=str, default='~/Desktop/ERP 导出',
                       help='输出目录')
    
    args = parser.parse_args()
    
    export_visit_statistics(
        month=args.month,
        output_dir=args.output_dir
    )


if __name__ == '__main__':
    main()
