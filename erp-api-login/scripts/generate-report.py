#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ERP 新房合同数据导出与报表生成工具
支持：
1. 按日期范围导出新房合同数据
2. 生成每日数据报表（使用指定日期导出的数据）
3. 生成每周数据报表（按指定周时间段导出后生成）
"""

import sys
import os
import zipfile
import xml.etree.ElementTree as ET
import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# 添加脚本目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# ============== 字段名定义（无空格）==============
F_DATE = '日期'
F_DEPT_L1 = b'\xe9\xa1\xb9\xe7\x9b\xae\xe9\x83\xa8\xe5\xb1\x82\xe7\xba\xa71'.decode('utf-8')
F_DEPT_L2 = b'\xe9\xa1\xb9\xe7\x9b\xae\xe9\x83\xa8\xe5\xb1\x82\xe7\xba\xa72'.decode('utf-8')
F_CHANNEL_L1 = b'\xe6\xb8\xa0\xe9\x81\x93\xe9\x83\xa8\xe5\xb1\x82\xe7\xba\xa71'.decode('utf-8')
F_CHANNEL_L2 = b'\xe6\xb8\xa0\xe9\x81\x93\xe9\x83\xa8\xe5\xb1\x82\xe7\xba\xa72'.decode('utf-8')
F_AUTH_CHANNEL_L1 = b'\xe6\x8e\x88\xe6\x9d\x83\xe6\xb8\xa0\xe9\x81\x93\xe9\x83\xa8\xe5\xb1\x82\xe7\xba\xa71'.decode('utf-8')
F_AUTH_CHANNEL_L2 = b'\xe6\x8e\x88\xe6\x9d\x83\xe6\xb8\xa0\xe9\x81\x93\xe9\x83\xa8\xe5\xb1\x82\xe7\xba\xa72'.decode('utf-8')
F_BUILDING = '楼盘名称'
F_SUBSCRIBE_UNITS = '认购套数'
F_SUBSCRIBE_AMT = '认购业绩'
F_SIGN_UNITS = '签约套数'
F_SIGN_AMT = '签约业绩'
F_STATUS = '合同状态'
F_WEEK = '周'

# ============== ERP API 客户端 ==============

try:
    import importlib.util
    erp_export_path = os.path.join(script_dir, 'erp-export.py')
    spec = importlib.util.spec_from_file_location("erp_export", erp_export_path)
    erp_export = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(erp_export)
    ERPAPIClient = erp_export.ERPAPIClient
    get_user_credentials = erp_export.get_user_credentials
    HAS_ERP_CLIENT = True
except Exception as e:
    print('⚠️ 无法加载 ERP API 客户端：{}'.format(e))
    HAS_ERP_CLIENT = False


def normalize_date(date_str):
    """标准化日期格式为 YYYY-MM-DD"""
    if not date_str:
        return ''
    
    # 尝试多种格式
    formats = [
        '%Y/%m/%d',
        '%Y-%m-%d',
        '%Y/%m/%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str[:len(fmt.replace('%', '').replace(' ', ''))+fmt.count(' ')], fmt)
            return dt.strftime('%Y-%m-%d')
        except:
            continue
    
    if len(date_str) >= 10:
        return date_str[:10].replace('/', '-')
    
    return date_str


def get_week_range(date_str=None):
    """根据日期计算所在周的起止日期"""
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


def export_new_house_contracts(start_date, end_date, output_dir=None):
    """
    导出指定日期范围的新房合同数据
    
    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        output_dir: 输出目录
    
    Returns:
        导出的文件路径，失败返回 None
    """
    if not HAS_ERP_CLIENT:
        print('❌ ERP API 客户端不可用')
        return None
    
    phone, password = get_user_credentials()
    if not phone or not password:
        print('❌ 未找到 ERP 登录凭证')
        return None
    
    print('使用账号：{}'.format(phone))
    
    client = ERPAPIClient(phone=phone, password=password)
    
    if not client.login():
        print('❌ 登录失败')
        return None
    
    user_info = client.get_user_info()
    if not user_info:
        print('❌ 用户信息获取失败')
        return None
    
    print('✅ 用户：{}'.format(user_info.get('userName', phone)))
    
    # 转换日期为时间戳
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    end_dt = end_dt.replace(hour=23, minute=59, second=59)
    
    # 查询日期范围时间戳（毫秒）
    query_start_time = int(start_dt.timestamp() * 1000)
    query_end_time = int(end_dt.timestamp() * 1000)
    
    # 签约时间范围时间戳（毫秒）- 与查询日期范围相同
    sign_tm_start = query_start_time
    sign_tm_end = query_end_time
    
    print('\n导出新房合同数据...')
    print('  时间段：{} ~ {}'.format(start_date, end_date))
    print('  查询日期范围：[{}, {}]'.format(query_start_time, query_end_time))
    print('  签约时间范围：[{}, {}]'.format(sign_tm_start, sign_tm_end))
    
    result = client.export_new_house_contracts(
        start_time=query_start_time,
        end_time=query_end_time,
        sign_tm_start=sign_tm_start,
        sign_tm_end=sign_tm_end,
        city_code='450100',
        organ_id='625864877560328320',
        output_dir=output_dir
    )
    
    if result and result.get('success'):
        return result.get('file')
    else:
        return None


def load_excel_records(file_path):
    """
    加载 Excel 文件中的合同明细数据
    
    Args:
        file_path: Excel 文件路径
    
    Returns:
        记录列表
    """
    ns = {'ss': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    
    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            sheet_file = 'xl/worksheets/sheet2.xml'
            if sheet_file not in z.namelist():
                print('❌ 未找到合同明细 sheet')
                return []
            
            xml_content = z.read(sheet_file)
            xml_content = re.sub(b'<ss:autoFilter[^>]*/>', b'', xml_content)
            
            root = ET.fromstring(xml_content)
            rows = root.findall('.//ss:row', ns)
            
            if not rows:
                return []
            
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
            
            # 读取数据
            records = []
            for row in rows[1:]:
                cells = row.findall('ss:c', ns)
                values = []
                for cell in cells:
                    val = ''
                    v_elem = cell.find('ss:v', ns)
                    if v_elem is not None and v_elem.text:
                        val = v_elem.text
                    else:
                        t_elem = cell.find('ss:is/ss:t', ns)
                        if t_elem is not None and t_elem.text:
                            val = t_elem.text
                    values.append(val)
                
                if values and any(values):
                    record = {}
                    for i, val in enumerate(values):
                        if i < len(headers) and headers[i]:
                            field_name = headers[i].replace(' ', '')
                            record[field_name] = val
                    records.append(record)
            
            return records
    
    except Exception as e:
        print('❌ 读取 Excel 失败：{}'.format(e))
        return []


def generate_daily_report(records, output_file, date_filter=None):
    """
    生成每日数据报表
    
    Args:
        records: 合同记录列表
        output_file: 输出文件路径
        date_filter: 日期过滤（可选）
    """
    print('\n生成每日数据报表...')
    
    daily_data = []
    
    for record in records:
        # 日期过滤
        date_raw = record.get('签约日期', '') or record.get('认购日期', '') or ''
        date_normalized = normalize_date(date_raw)
        
        if date_filter and date_normalized != date_filter:
            continue
        
        sign_total = float(record.get('签约总价', 0) or 0)
        sub_total = float(record.get('认购总价', 0) or 0)
        
        if sign_total > 0:
            status = '签约'
            subscribe_units, subscribe_amount = 0, 0
            sign_units, sign_amt = 1, sign_total
        elif sub_total > 0:
            status = '认购'
            subscribe_units, subscribe_amount = 1, sub_total
            sign_units, sign_amt = 0, 0
        else:
            status = ''
            subscribe_units, subscribe_amount = 0, 0
            sign_units, sign_amt = 0, 0
        
        daily_data.append({
            F_DATE: date_normalized,
            F_DEPT_L2: record.get(F_DEPT_L2, ''),
            F_CHANNEL_L2: record.get(F_CHANNEL_L2, ''),
            F_AUTH_CHANNEL_L2: record.get(F_AUTH_CHANNEL_L2, ''),
            F_DEPT_L1: record.get(F_DEPT_L1, ''),
            F_CHANNEL_L1: record.get(F_CHANNEL_L1, ''),
            F_AUTH_CHANNEL_L1: record.get(F_AUTH_CHANNEL_L1, ''),
            F_BUILDING: record.get(F_BUILDING, ''),
            F_SUBSCRIBE_UNITS: subscribe_units,
            F_SUBSCRIBE_AMT: subscribe_amount,
            F_SIGN_UNITS: sign_units,
            F_SIGN_AMT: sign_amt,
            F_STATUS: status
        })
    
    # 导出 Excel
    try:
        import pandas as pd
        df = pd.DataFrame(daily_data)
        df.columns = [col.replace(' ', '') for col in df.columns]
        df.to_excel(output_file, index=False)
        print('  ✅ 每日数据：{} ({} 条记录)'.format(output_file, len(daily_data)))
        return True
    except Exception as e:
        print('  ❌ 导出失败：{}'.format(e))
        return False


def generate_weekly_report(records, output_file, week_start, week_end):
    """
    生成每周数据报表
    
    Args:
        records: 合同记录列表
        output_file: 输出文件路径
        week_start: 周开始日期 (YYYY-MM-DD)
        week_end: 周结束日期 (YYYY-MM-DD)
    """
    print('\n生成每周数据报表...')
    print('  时间段：{} ~ {}'.format(week_start, week_end))
    
    # 按项目部层级 2 和层级 1 分组
    weekly_agg = defaultdict(lambda: {
        'subscribeUnits': 0, 'subscribeAmount': 0,
        'signUnits': 0, 'signAmount': 0,
        'cancelUnits': 0, 'cancelAmount': 0,
    })
    
    for record in records:
        date_raw = record.get('签约日期', '') or record.get('认购日期', '') or ''
        date_normalized = normalize_date(date_raw)
        
        # 过滤本周数据
        if date_normalized and (date_normalized < week_start or date_normalized > week_end):
            continue
        
        # 获取基础应付金额（用于业绩计算）
        base_pay_amount = float(record.get('基础应付金额', 0) or 0)
        
        sign_total = float(record.get('签约总价', 0) or 0)
        sub_total = float(record.get('认购总价', 0) or 0)
        
        # 判断合同状态
        status = record.get('合同状态', '')
        is_cancel = status in ['退单', '作废', '已退单']
        
        dept_l2 = record.get(F_DEPT_L2, '')
        dept_l1 = record.get(F_DEPT_L1, '')
        
        # 按项目部层级 2 和层级 1 分组
        key = '{}|{}|{}'.format(week_start, dept_l2, dept_l1)
        
        if is_cancel:
            # 退单
            weekly_agg[key]['cancelUnits'] += 1
            weekly_agg[key]['cancelAmount'] += base_pay_amount
        elif sign_total > 0:
            # 签约
            weekly_agg[key]['signUnits'] += 1
            weekly_agg[key]['signAmount'] += base_pay_amount
        elif sub_total > 0:
            # 认购
            weekly_agg[key]['subscribeUnits'] += 1
            weekly_agg[key]['subscribeAmount'] += base_pay_amount
    
    weekly_data = []
    for key, agg in weekly_agg.items():
        parts = key.split('|')
        week = parts[0] if len(parts) > 0 else week_start
        dept_l2 = parts[1] if len(parts) > 1 else ''
        dept_l1 = parts[2] if len(parts) > 2 else ''
        
        subscribe_units = agg['subscribeUnits']
        subscribe_amount = agg['subscribeAmount']
        sign_units = agg['signUnits']
        sign_amount = agg['signAmount']
        cancel_units = agg['cancelUnits']
        cancel_amount = agg['cancelAmount']
        
        # 套数合计 = 认购 + 签约
        total_units = subscribe_units + sign_units
        
        # 剔除退单后的数据
        exclude_cancel_units = subscribe_units + sign_units - cancel_units
        exclude_cancel_amount = subscribe_amount + sign_amount - cancel_amount
        
        weekly_data.append({
            '周': '{} ~ {}'.format(week, week_end),
            '项目部层级 2': dept_l2,
            '项目部层级 1': dept_l1,
            '认购套数': subscribe_units,
            '认购业绩': subscribe_amount,
            '签约套数': sign_units,
            '签约业绩': sign_amount,
            '套数合计': total_units,
            '退单套数': cancel_units,
            '退单业绩': cancel_amount,
            '剔除退单套数': exclude_cancel_units,
            '剔除退单业绩': exclude_cancel_amount,
        })
    
    # 导出 Excel
    try:
        import pandas as pd
        df = pd.DataFrame(weekly_data)
        # 确保列名无空格
        df.columns = [col.replace(' ', '') for col in df.columns]
        df.to_excel(output_file, index=False)
        print('  ✅ 每周数据：{} ({} 条记录)'.format(output_file, len(weekly_data)))
        return True
    except Exception as e:
        print('  ❌ 导出失败：{}'.format(e))
        return False


# ============== 主程序 ==============

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ERP 新房合同数据导出与报表生成')
    
    # 操作模式
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--export-daily', action='store_true', 
                           help='导出指定日期的数据并生成每日报表')
    mode_group.add_argument('--export-weekly', action='store_true',
                           help='导出指定周的数据并生成每周报表')
    mode_group.add_argument('--generate-daily', action='store_true',
                           help='从已有 Excel 文件生成每日报表')
    mode_group.add_argument('--generate-weekly', action='store_true',
                           help='从已有 Excel 文件生成每周报表')
    
    # 日期参数
    parser.add_argument('--date', type=str, help='指定日期 (YYYY-MM-DD)')
    parser.add_argument('--week-start', type=str, help='周开始日期 (YYYY-MM-DD)')
    parser.add_argument('--week-end', type=str, help='周结束日期 (YYYY-MM-DD)')
    
    # 文件参数
    parser.add_argument('--input', type=str, help='输入 Excel 文件路径')
    parser.add_argument('--output-dir', type=str, default='~/Desktop/ERP 导出/南宁新房',
                       help='输出目录')
    
    args = parser.parse_args()
    
    # 解析输出目录
    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print('='*80)
    print('ERP 新房合同数据导出与报表生成工具')
    print('='*80)
    print()
    
    # ========== 模式 1: 导出每日数据并生成报表 ==========
    if args.export_daily:
        if not args.date:
            print('❌ 请指定日期 (--date YYYY-MM-DD)')
            return
        
        date_str = args.date
        
        print('导出每日数据...')
        print('  日期：{}'.format(date_str))
        
        # 导出指定日期的数据
        start_dt = datetime.strptime(date_str, '%Y-%m-%d')
        end_dt = start_dt.replace(hour=23, minute=59, second=59)
        
        # 时间戳（毫秒）
        query_start_ts = int(start_dt.timestamp() * 1000)
        query_end_ts = int(end_dt.timestamp() * 1000)
        sign_tm_start = query_start_ts
        sign_tm_end = query_end_ts
        
        # 调用导出
        if HAS_ERP_CLIENT:
            phone, password = get_user_credentials()
            if phone and password:
                client = ERPAPIClient(phone=phone, password=password)
                if client.login():
                    result = client.export_new_house_contracts(
                        start_time=query_start_ts,
                        end_time=query_end_ts,
                        sign_tm_start=sign_tm_start,
                        sign_tm_end=sign_tm_end,
                        city_code='450100',
                        organ_id='625864877560328320',
                        output_dir=str(output_dir)
                    )
                    
                    if result and result.get('file'):
                        excel_file = result['file']
                        print('  ✅ 导出成功：{}'.format(excel_file))
                        
                        # 加载数据并生成报表
                        records = load_excel_records(excel_file)
                        print('  加载 {} 条记录'.format(len(records)))
                        
                        date_str_file = date_str.replace('-', '')
                        daily_file = output_dir / '南宁新房每日数据_{}.xlsx'.format(date_str_file)
                        generate_daily_report(records, str(daily_file), date_filter=date_str)
        else:
            print('⚠️ ERP API 客户端不可用，请手动导出 Excel 文件后使用 --generate-daily 模式')
    
    # ========== 模式 2: 导出每周数据并生成报表 ==========
    elif args.export_weekly:
        if not args.week_start:
            # 使用当前周
            week_start, week_end = get_week_range()
        else:
            week_start = args.week_start
            week_end = args.week_end if args.week_end else get_week_range(week_start)[1]
        
        print('导出每周数据...')
        print('  时间段：{} ~ {}'.format(week_start, week_end))
        
        # 转换日期为时间戳
        start_dt = datetime.strptime(week_start, '%Y-%m-%d')
        end_dt = datetime.strptime(week_end, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        
        # 时间戳（毫秒）
        query_start_ts = int(start_dt.timestamp() * 1000)
        query_end_ts = int(end_dt.timestamp() * 1000)
        sign_tm_start = query_start_ts
        sign_tm_end = query_end_ts
        
        # 调用导出
        if HAS_ERP_CLIENT:
            phone, password = get_user_credentials()
            if phone and password:
                client = ERPAPIClient(phone=phone, password=password)
                if client.login():
                    result = client.export_new_house_contracts(
                        start_time=query_start_ts,
                        end_time=query_end_ts,
                        sign_tm_start=sign_tm_start,
                        sign_tm_end=sign_tm_end,
                        city_code='450100',
                        organ_id='625864877560328320',
                        output_dir=str(output_dir)
                    )
                    
                    if result and result.get('file'):
                        excel_file = result['file']
                        print('  ✅ 导出成功：{}'.format(excel_file))
                        
                        # 加载数据并生成报表
                        records = load_excel_records(excel_file)
                        print('  加载 {} 条记录'.format(len(records)))
                        
                        week_start_file = week_start.replace('-', '')
                        weekly_file = output_dir / '南宁新房每周数据_{}.xlsx'.format(week_start_file)
                        generate_weekly_report(records, str(weekly_file), week_start, week_end)
        else:
            print('⚠️ ERP API 客户端不可用，请手动导出 Excel 文件后使用 --generate-weekly 模式')
    
    # ========== 模式 3: 从已有 Excel 生成每日报表 ==========
    elif args.generate_daily:
        if not args.input:
            print('❌ 请指定输入 Excel 文件 (--input <文件路径>)')
            return
        
        if not args.date:
            print('❌ 请指定日期 (--date YYYY-MM-DD)')
            return
        
        print('从 Excel 生成每日报表...')
        print('  输入文件：{}'.format(args.input))
        print('  日期：{}'.format(args.date))
        
        records = load_excel_records(args.input)
        print('  加载 {} 条记录'.format(len(records)))
        
        date_str_file = args.date.replace('-', '')
        daily_file = output_dir / '南宁新房每日数据_{}.xlsx'.format(date_str_file)
        generate_daily_report(records, str(daily_file), date_filter=args.date)
    
    # ========== 模式 4: 从已有 Excel 生成每周报表 ==========
    elif args.generate_weekly:
        if not args.input:
            print('❌ 请指定输入 Excel 文件 (--input <文件路径>)')
            return
        
        if not args.week_start:
            # 使用当前周
            week_start, week_end = get_week_range()
        else:
            week_start = args.week_start
            week_end = args.week_end if args.week_end else get_week_range(week_start)[1]
        
        print('从 Excel 生成每周报表...')
        print('  输入文件：{}'.format(args.input))
        print('  时间段：{} ~ {}'.format(week_start, week_end))
        
        records = load_excel_records(args.input)
        print('  加载 {} 条记录'.format(len(records)))
        
        week_start_file = week_start.replace('-', '')
        weekly_file = output_dir / '南宁新房每周数据_{}.xlsx'.format(week_start_file)
        generate_weekly_report(records, str(weekly_file), week_start, week_end)
    
    print()
    print('='*80)
    print('✅ 完成!')
    print('='*80)


if __name__ == '__main__':
    main()
