#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
南宁新房合同数据处理工具 v4
- 正确处理 Excel autoFilter
- 输出字段名无空格
"""

import sys
import os
import importlib.util
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

script_dir = os.path.dirname(os.path.abspath(__file__))
erp_export_path = os.path.join(script_dir, 'erp-export.py')

spec = importlib.util.spec_from_file_location("erp_export", erp_export_path)
erp_export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(erp_export)

ERPAPIClient = erp_export.ERPAPIClient
get_user_credentials = erp_export.get_user_credentials


def load_excel_sheets(file_path):
    """加载 Excel 文件的 5 个 sheet（忽略 autoFilter，直接读取数据）"""
    import zipfile
    import xml.etree.ElementTree as ET
    
    all_data = {}
    ns = {'ss': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    
    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            wb_xml = z.read('xl/workbook.xml')
            wb_root = ET.fromstring(wb_xml)
            
            sheets = wb_root.findall('.//ss:sheet', ns)
            sheet_map = {sheet.get('name'): f'xl/worksheets/sheet{i}.xml' 
                        for i, sheet in enumerate(sheets, 1)}
            
            for sheet_name in ['新房合同', '合同明细', '解约和作废合同', '应付费用项明细', '应收费用项明细']:
                sheet_file = sheet_map.get(sheet_name)
                if not sheet_file or sheet_file not in z.namelist():
                    print(f"  {sheet_name}: 未找到")
                    all_data[sheet_name] = []
                    continue
                
                xml_content = z.read(sheet_file)
                root = ET.fromstring(xml_content)
                rows = root.findall('.//ss:row', ns)
                
                # 读取表头（第一行，支持 inlineStr）
                headers = []
                if rows:
                    header_row = rows[0]
                    header_cells = header_row.findall('ss:c', ns)
                    for cell in header_cells:
                        t_elem = cell.find('ss:is/ss:t', ns)
                        if t_elem is not None and t_elem.text:
                            headers.append(t_elem.text)
                        else:
                            v_elem = cell.find('ss:v', ns)
                            headers.append(v_elem.text if v_elem is not None else '')
                
                # 读取数据行（跳过第一行表头，支持 v 和 is/t 两种格式）
                data_rows = []
                for row in rows[1:]:
                    cells = row.findall('ss:c', ns)
                    values = []
                    for cell in cells:
                        val = ''
                        # 先尝试 v 元素
                        v_elem = cell.find('ss:v', ns)
                        if v_elem is not None and v_elem.text:
                            val = v_elem.text
                        else:
                            # 尝试 is/t 元素（inline string）
                            t_elem = cell.find('ss:is/ss:t', ns)
                            if t_elem is not None and t_elem.text:
                                val = t_elem.text
                        values.append(val)
                    if values and any(values):
                        record = {}
                        for i, val in enumerate(values):
                            if i < len(headers) and headers[i]:
                                # 字段名去掉空格
                                field_name = headers[i].replace(' ', '')
                                record[field_name] = val
                        data_rows.append(record)
                
                print(f"  {sheet_name}: {len(data_rows)} 条记录")
                all_data[sheet_name] = data_rows
        
        return all_data
        
    except Exception as e:
        print(f"❌ 读取 Excel 失败：{e}")
        import traceback
        traceback.print_exc()
        return None


def calculate_daily_data(all_data):
    """计算每日数据（字段名无空格）"""
    daily_data = []
    contract_details = all_data.get('合同明细', [])
    
    for record in contract_details:
        sign_total = float(record.get('签约总价', 0) or 0)
        sub_total = float(record.get('认购总价', 0) or 0)
        
        # 根据金额判断
        if sign_total > 0:
            subscribe_units, subscribe_amount = 0, 0
            sign_units, sign_amt = 1, sign_total
            status = '签约'
        elif sub_total > 0:
            subscribe_units, subscribe_amount = 1, sub_total
            sign_units, sign_amt = 0, 0
            status = '认购'
        else:
            subscribe_units, subscribe_amount = 0, 0
            sign_units, sign_amt = 0, 0
            status = ''
        
        sign_date = record.get('签约日期', '') or ''
        if not sign_date:
            sign_date = record.get('认购日期', '') or ''
        if sign_date and len(sign_date) > 10:
            sign_date = sign_date[:10]
        
        daily_data.append({
            '日期': sign_date,
            '项目部层级2': record.get('项目部层级2', '') or '',
            '渠道部层级2': record.get('渠道部层级2', '') or '',
            '授权渠道部层级2': record.get('授权渠道部层级2', '') or '',
            '项目部层级1': record.get('项目部层级1', '') or '',
            '渠道部层级1': record.get('渠道部层级1', '') or '',
            '授权渠道部层级1': record.get('授权渠道部层级1', '') or '',
            '楼盘名称': record.get('楼盘名称', '') or '',
            '认购套数': subscribe_units,
            '认购业绩': subscribe_amount,
            '签约套数': sign_units,
            '签约业绩': sign_amt,
            '合同状态': status
        })
    
    return daily_data


def calculate_weekly_data(all_data):
    """计算每周数据（字段名无空格）"""
    weekly_agg = defaultdict(lambda: {
        'subscribeUnits': 0, 'subscribeAmount': 0,
        'signUnitsL1': 0, 'signUnitsL2': 0, 'signAmount': 0,
        'cancelUnits': 0, 'cancelAmount': 0,
    })
    
    for record in all_data.get('合同明细', []):
        sign_total = float(record.get('签约总价', 0) or 0)
        sub_total = float(record.get('认购总价', 0) or 0)
        
        if sign_total > 0:
            status = '签约'
        elif sub_total > 0:
            status = '认购'
        else:
            status = ''
        
        date_str = record.get('签约日期', '') or record.get('认购日期', '') or ''
        week_key = '未知'
        if date_str and len(date_str) >= 10:
            try:
                dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
                week_start = dt - timedelta(days=dt.weekday())
                week_key = week_start.strftime('%Y-%m-%d')
            except:
                pass
        
        dept_l2 = record.get('项目部层级2', '') or ''
        dept_l1 = record.get('项目部层级1', '') or ''
        key = f"{week_key}|{dept_l2}|{dept_l1}"
        
        if status == '认购':
            weekly_agg[key]['subscribeUnits'] += 1
            weekly_agg[key]['subscribeAmount'] += sub_total
        elif status == '签约':
            if record.get('渠道部层级1', ''):
                weekly_agg[key]['signUnitsL1'] += 1
            if record.get('渠道部层级2', ''):
                weekly_agg[key]['signUnitsL2'] += 1
            weekly_agg[key]['signAmount'] += sign_total
    
    weekly_data = []
    for key, agg in weekly_agg.items():
        parts = key.split('|')
        week = parts[0] if len(parts) > 0 else '未知'
        dept_l2 = parts[1] if len(parts) > 1 else ''
        dept_l1 = parts[2] if len(parts) > 2 else ''
        total = agg['signUnitsL1'] + agg['signUnitsL2']
        
        weekly_data.append({
            '周': week,
            '项目部层级2': dept_l2,
            '项目部层级1': dept_l1,
            '一级认购套数': agg['subscribeUnits'],
            '一级认购业绩': agg['subscribeAmount'],
            '一级签约套数': agg['signUnitsL1'],
            '二级签约套数': agg['signUnitsL2'],
            '套数合计': total,
            '一级业绩': agg['signAmount'],
            '退单套数': agg['cancelUnits'],
            '退单业绩': agg['cancelAmount'],
            '目标': 0,
            '完成率': '0.00%'
        })
    
    return weekly_data


def export_to_excel(data, output_file, sheet_name='数据'):
    """导出数据到 Excel（确保字段名无空格）"""
    try:
        import pandas as pd
        df = pd.DataFrame(data) if data else pd.DataFrame()
        
        # 确保列名无空格
        df.columns = [col.replace(' ', '') for col in df.columns]
        
        df.to_excel(output_file, sheet_name=sheet_name, index=False)
        print(f"✅ Excel 导出成功：{output_file}")
        return True
    except Exception as e:
        print(f"❌ Excel 导出失败：{e}")
        return False


def main():
    print("="*70)
    print("南宁新房合同数据处理工具 v4")
    print("="*70)
    
    phone, password = get_user_credentials()
    if not phone or not password:
        print("\n❌ 未找到 ERP 登录凭证")
        return
    
    print(f"\n使用账号：{phone}")
    client = ERPAPIClient(phone=phone, password=password)
    
    if not client.login():
        print("\n❌ 登录失败")
        return
    
    user_info = client.get_user_info()
    if not user_info:
        print("\n❌ 用户信息获取失败")
        return
    
    print(f"✅ 用户：{user_info.get('userName')}")
    
    # 导出今日数据
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_time = int(today.timestamp() * 1000)
    end_time = int((today + timedelta(days=1)).timestamp() * 1000) - 1
    
    print("\n导出今日新房合同数据...")
    result = client.export_new_house_contracts(
        start_time=start_time, end_time=end_time,
        city_code='450100', organ_id='625864877560328320'
    )
    
    if not result or not result.get('success'):
        print("\n❌ 导出失败")
        return
    
    # 处理数据
    print("\n处理 Excel 数据...")
    all_data = load_excel_sheets(result.get('excel_file'))
    
    if not all_data:
        print("\n❌ 无法读取数据")
        return
    
    # 计算报表
    print("\n计算每日数据...")
    daily_data = calculate_daily_data(all_data)
    print(f"✅ 生成 {len(daily_data)} 条每日数据")
    
    print("\n计算每周数据...")
    weekly_data = calculate_weekly_data(all_data)
    print(f"✅ 生成 {len(weekly_data)} 条每周数据")
    
    # 导出
    output_dir = Path('~/Desktop/ERP 导出/南宁新房').expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d')
    
    daily_file = output_dir / f"南宁新房每日数据_{timestamp}.xlsx"
    weekly_file = output_dir / f"南宁新房每周数据_{timestamp}.xlsx"
    
    print(f"\n导出每日数据...")
    export_to_excel(daily_data, str(daily_file), '每日数据')
    
    print(f"导出每周数据...")
    export_to_excel(weekly_data, str(weekly_file), '每周数据')
    
    # 统计
    print("\n" + "="*70)
    print("📊 统计摘要")
    print("="*70)
    if daily_data:
        total_sub = sum(d['认购套数'] for d in daily_data)
        total_sub_amt = sum(d['认购业绩'] for d in daily_data)
        total_sign = sum(d['签约套数'] for d in daily_data)
        total_sign_amt = sum(d['签约业绩'] for d in daily_data)
        
        print(f"\n今日总计:")
        print(f"   认购：{total_sub} 套 / ¥{total_sub_amt:,.2f}")
        print(f"   签约：{total_sign} 套 / ¥{total_sign_amt:,.2f}")
    
    print("\n" + "="*70)
    print("✅ 完成！")
    print("="*70)
    print(f"\n📁 输出文件:")
    print(f"   {daily_file}")
    print(f"   {weekly_file}")


if __name__ == "__main__":
    main()
