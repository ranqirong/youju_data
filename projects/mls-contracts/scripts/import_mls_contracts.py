#!/usr/bin/env python3
"""MLS合同数据导入 - ABC三方案架构
数据库: youju_data / youju_write / YoujuWrite@2024"""
import json
import mysql.connector
from datetime import datetime
from collections import Counter

conn = mysql.connector.connect(
    host='134.175.128.94', database='youju_data',
    user='youju', password='Youju2024@Data', charset='utf8mb4'
)
cursor = conn.cursor()
today = '2026-04-16'

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# 读取JSON
with open('/opt/yjzf/mcp-data/mls_contracts_20260416.json', 'r') as f:
    contracts = json.load(f)
log(f"读取 {len(contracts)} 条合同记录")

# B方案: 批量参数化插入明细
insert_sql = """
INSERT INTO ods_mls_contracts
(city, region, contract_name, contract_no, status, party_b, creator, create_time, sync_date)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""
batch = [(c['city'], c['region'], c['contract_name'], c['contract_no'],
          c['status'], c['party_b'], c['creator'], c['create_time'], today)
         for c in contracts]
cursor.executemany(insert_sql, batch)
conn.commit()
log(f"B方案明细表写入: {cursor.rowcount} 条")

# C方案: 变更追踪(首次全ADD)
change_sql = """
INSERT INTO ods_mls_contracts_changes
(change_date, contract_no, change_type, new_values)
VALUES (%s, %s, 'ADD', %s)
"""
change_batch = [(today, c['contract_no'], json.dumps(c, ensure_ascii=False)) for c in contracts]
cursor.executemany(change_sql, change_batch)
conn.commit()
log(f"C方案变更追踪写入: {cursor.rowcount} 条")

# A方案: 每日快照
city_stats = dict(Counter([c['city'] for c in contracts]))
cursor.execute("""
INSERT INTO ods_mls_contracts_daily_snapshot
(snapshot_date, total_count, city_stats)
VALUES (%s, %s, %s)
ON DUPLICATE KEY UPDATE
total_count = VALUES(total_count),
city_stats = VALUES(city_stats)
""", (today, len(contracts), json.dumps(city_stats, ensure_ascii=False)))
conn.commit()
log(f"A方案快照记录完成: {city_stats}")

# 交叉验证
cursor.execute("SELECT COUNT(*) FROM ods_mls_contracts WHERE sync_date = %s", (today,))
db_count = cursor.fetchone()[0]
status = "✅ 通过" if db_count == len(contracts) else "⚠️ 不匹配!"
log(f"交叉验证: 数据库 {db_count} 条 / JSON {len(contracts)} 条 → {status}")

# 按城市验证
cursor.execute("""
SELECT city, COUNT(*), GROUP_CONCAT(DISTINCT status) 
FROM ods_mls_contracts WHERE sync_date = %s GROUP BY city ORDER BY city
""", (today,))
log("按城市分布:")
for row in cursor.fetchall():
    log(f"  {row[0]}: {row[1]}条 ({row[2]})")

cursor.close()
conn.close()
log("导入完成!")
