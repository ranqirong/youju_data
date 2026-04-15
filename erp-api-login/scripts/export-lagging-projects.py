#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
落后项目数据报表导出工具
- 合并同项目不同业态数据（住宅、公寓、商铺、别墅等）
- 计算落后数量 = 竞司成交 - 优居成交
- 输出字段：部门、所在部门、竞对公司、项目名称、竞司成交、竞司进场量、优居成交、我司进场量、落后数量
"""

import sys
import os
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


def merge_project_data(df):
    """
    合并同项目不同业态的数据
    
    Args:
        df: 原始数据 DataFrame
    
    Returns:
        合并后的 DataFrame
    """
    print('  合并同项目不同业态数据...')
    
    # 识别项目名称列（可能有多种命名）
    project_cols = ['项目名称', '楼盘名称', '项目', '楼盘']
    project_col = None
    for col in project_cols:
        if col in df.columns:
            project_col = col
            break
    
    if not project_col:
        print('  ⚠️ 未找到项目名称列')
        return df
    
    # 识别业态列
    property_type_cols = ['物业类型', '业态', '类型', '产品']
    property_type_col = None
    for col in property_type_cols:
        if col in df.columns:
            property_type_col = col
            break
    
    # 识别数值列
    numeric_cols_map = {
        '竞司成交': ['竞司成交', '竞对成交', '竞争对手成交', '竞品成交'],
        '竞司进场量': ['竞司进场量', '竞对进场量', '竞争对手进场量', '竞品带看'],
        '优居成交': ['优居成交', '我司成交', '我方成交'],
        '我司进场量': ['我司进场量', '我方进场量', '带看量', '进场量'],
    }
    
    # 找到实际的列名
    actual_cols = {}
    for target_col, possible_names in numeric_cols_map.items():
        for name in possible_names:
            if name in df.columns:
                actual_cols[target_col] = name
                break
    
    print('  项目名称列：{}'.format(project_col))
    print('  业态列：{}'.format(property_type_col if property_type_col else '未找到'))
    print('  数值列：{}'.format(actual_cols))
    
    # 按项目名称分组汇总
    if property_type_col:
        # 有业态列，需要合并
        group_cols = [project_col]
        
        # 检查是否有部门相关列
        dept_cols = ['部门', '所在部门', '竞对公司']
        for col in dept_cols:
            if col in df.columns:
                group_cols.append(col)
        
        # 汇总数值列
        agg_dict = {}
        for target_col, actual_col in actual_cols.items():
            agg_dict[actual_col] = 'sum'
        
        # 非数值列取第一个值
        for col in df.columns:
            if col not in agg_dict and col not in group_cols:
                agg_dict[col] = 'first'
        
        # 执行分组汇总
        df_merged = df.groupby(group_cols, as_index=False).agg(agg_dict)
        
        print('  合并前项目数：{} 个'.format(len(df)))
        print('  合并后项目数：{} 个'.format(len(df_merged)))
        
        return df_merged
    else:
        # 无业态列，直接返回
        print('  无业态列，无需合并')
        return df


def calculate_lagging(df):
    """
    计算落后数量
    
    Args:
        df: 数据 DataFrame
    
    Returns:
        添加落后数量列的 DataFrame
    """
    print('  计算落后数量...')
    
    # 找到成交列
    rival_deal_col = None
    your_deal_col = None
    
    for col in df.columns:
        col_lower = col.lower()
        if '竞司' in col or '竞对' in col or '竞争对手' in col:
            if '成交' in col_lower:
                rival_deal_col = col
        elif '优居' in col or '我司' in col or '我方' in col:
            if '成交' in col_lower:
                your_deal_col = col
    
    if rival_deal_col and your_deal_col:
        # 计算落后数量 = 竞司成交 - 优居成交
        df['落后数量'] = df[rival_deal_col].fillna(0) - df[your_deal_col].fillna(0)
        print('  竞司成交列：{}'.format(rival_deal_col))
        print('  优居成交列：{}'.format(your_deal_col))
        print('  落后数量计算完成')
    else:
        print('  ⚠️ 未找到成交列，无法计算落后数量')
        if rival_deal_col:
            print('    找到竞司成交列：{}'.format(rival_deal_col))
        if your_deal_col:
            print('    找到优居成交列：{}'.format(your_deal_col))
        df['落后数量'] = 0
    
    return df


def format_output(df):
    """
    格式化输出字段
    
    Args:
        df: 数据 DataFrame
    
    Returns:
        格式化后的 DataFrame
    """
    print('  格式化输出字段...')
    
    # 目标字段
    target_cols = {
        '部门': ['部门', '一级部门', '二级部门'],
        '所在部门': ['所在部门', '部门名称', '所属部门'],
        '竞对公司': ['竞对公司', '竞争对手', '竞品公司'],
        '项目名称': ['项目名称', '楼盘名称', '项目', '楼盘'],
        '竞司成交': ['竞司成交', '竞对成交', '竞争对手成交', '竞品成交'],
        '竞司进场量': ['竞司进场量', '竞对进场量', '竞争对手进场量', '竞品带看'],
        '优居成交': ['优居成交', '我司成交', '我方成交'],
        '我司进场量': ['我司进场量', '我方进场量', '带看量', '进场量'],
        '落后数量': ['落后数量'],
    }
    
    # 重命名列
    rename_map = {}
    for target_col, possible_names in target_cols.items():
        for name in possible_names:
            if name in df.columns:
                rename_map[name] = target_col
                break
    
    if rename_map:
        df = df.rename(columns=rename_map)
        print('  重命名列：{}'.format(rename_map))
    
    # 选择目标字段
    available_cols = [col for col in target_cols.keys() if col in df.columns]
    
    if available_cols:
        df = df[available_cols]
        print('  输出字段：{}'.format(available_cols))
    else:
        print('  ⚠️ 未找到任何目标字段')
    
    return df


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='落后项目数据报表导出工具')
    
    parser.add_argument('--input', type=str, required=True,
                       help='竞对数据导出文件路径（Excel 文件）')
    parser.add_argument('--output', type=str, default=None,
                       help='输出文件路径（默认自动生成）')
    parser.add_argument('--start-date', type=str, default=None,
                       help='开始日期 (YYYY-MM-DD)，默认 30 天前')
    parser.add_argument('--end-date', type=str, default=None,
                       help='结束日期 (YYYY-MM-DD)，默认为今天')
    parser.add_argument('--dept-ids', type=str, nargs='*',
                       default=['625864877560328320'],
                       help='部门 ID 列表')
    parser.add_argument('--rival-ids', type=str, nargs='*',
                       help='竞对公司 ID 列表')
    parser.add_argument('--merge-property', action='store_true', default=True,
                       help='合并同项目不同业态数据（默认启用）')
    
    args = parser.parse_args()
    
    print('='*80)
    print('落后项目数据报表导出工具')
    print('='*80)
    print()
    
    # 检查输入文件
    if not os.path.exists(args.input):
        print('❌ 输入文件不存在：{}'.format(args.input))
        print()
        print('💡 提示：请先导出竞对数据，然后使用导出的文件作为输入')
        print('   运行：python3 export-rival-stats.py --start-date 2026-03-01 --end-date 2026-03-31')
        return
    
    print('输入文件：{}'.format(args.input))
    print()
    
    # 读取竞对数据
    print('步骤 1: 读取竞对数据...')
    
    try:
        if args.input.endswith('.xlsx') or args.input.endswith('.xls'):
            df = pd.read_excel(args.input)
        elif args.input.endswith('.csv'):
            df = pd.read_csv(args.input, encoding='utf-8')
        else:
            print('❌ 不支持的文件格式：{}'.format(args.input))
            return
        
        print('  读取数据：{} 行 × {} 列'.format(len(df), len(df.columns)))
        print('  列名：{}'.format(list(df.columns)[:10]))
    except Exception as e:
        print('❌ 读取文件失败：{}'.format(e))
        return
    
    print()
    
    # 合并同项目不同业态数据
    if args.merge_property:
        print('步骤 2: 合并同项目不同业态数据...')
        df = merge_project_data(df)
        print()
    else:
        print('步骤 2: 跳过合并（--no-merge-property）')
        print()
    
    # 计算落后数量
    print('步骤 3: 计算落后数量...')
    df = calculate_lagging(df)
    print()
    
    # 格式化输出字段
    print('步骤 4: 格式化输出字段...')
    df_output = format_output(df)
    print()
    
    # 导出结果
    print('步骤 5: 导出结果...')
    
    if args.output:
        output_file = args.output
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path('~/Desktop/ERP 导出').expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / '落后项目数据报表_{}.xlsx'.format(timestamp)
    
    try:
        df_output.to_excel(output_file, index=False)
        print('  ✅ 导出成功：{}'.format(output_file))
        print('  记录数：{} 条'.format(len(df_output)))
    except Exception as e:
        print('  ❌ 导出失败：{}'.format(e))
        return
    
    print()
    
    # 显示统计摘要
    print('='*80)
    print('统计摘要')
    print('='*80)
    print()
    
    if '落后数量' in df_output.columns:
        total_lagging = df_output['落后数量'].sum()
        negative_lagging = df_output[df_output['落后数量'] > 0]
        print('总落后数量：{}'.format(total_lagging))
        print('落后项目数：{} 个（落后数量 > 0）'.format(len(negative_lagging)))
        
        if len(negative_lagging) > 0:
            print()
            print('落后项目 TOP10:')
            top10 = negative_lagging.nlargest(10, '落后数量')
            for idx, row in top10.iterrows():
                project = row.get('项目名称', '未知')
                lagging = row.get('落后数量', 0)
                print('  - {}: 落后 {} 套'.format(project, int(lagging)))
    
    print()
    print('='*80)
    print('✅ 完成!')
    print('='*80)
    print()
    print('📁 输出文件：{}'.format(output_file))
    print()
    
    # 使用说明
    print('💡 使用说明:')
    print('  1. 先导出竞对数据：')
    print('     python3 export-rival-stats.py --start-date 2026-03-01 --end-date 2026-03-31')
    print()
    print('  2. 从 ERP 系统导出落后项目的竞司成交明细')
    print()
    print('  3. 运行本工具处理数据：')
    print('     python3 export-lagging-projects.py --input 竞对数据文件.xlsx')
    print()


if __name__ == '__main__':
    main()
