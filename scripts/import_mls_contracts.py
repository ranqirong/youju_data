#!/usr/bin/env python3
"""MLS合同数据导入 - ABC三方案架构"""
import json
import mysql.connector
from datetime import datetime

# 数据库连接
conn = mysql.connector.connect(
    host='134.175.128.94',
    database='youju_data',
    user='youju_write',
    password='YoujuWrite@2024',
    charset='utf8mb4'
)
cursor = conn.cursor()

print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始导入MLS合同数据...")

# A方案: 每日快照表
cursor.execute("""
CREATE TABLE IF NOT EXISTS ods_mls_contracts_daily_snapshot (
    snapshot_date DATE NOT NULL COMMENT '快照日期',
    total_count INT NOT NULL COMMENT '总记录数',
    city_stats JSON COMMENT '各城市统计',
    raw_data_hash VARCHAR(32) COMMENT '数据MD5',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (snapshot_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='MLS合同-每日快照(A方案)';
""")

# B方案: 明细数据表
cursor.execute("""
CREATE TABLE IF NOT EXISTS ods_mls_contracts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    city VARCHAR(50) NOT NULL COMMENT '城市',
    region VARCHAR(50) COMMENT '区域',
    contract_name VARCHAR(255) NOT NULL COMMENT '合同名称',
    contract_no VARCHAR(100) NOT NULL COMMENT '合同编号',
    status VARCHAR(50) COMMENT '状态',
    party_b VARCHAR(255) COMMENT '乙方',
    creator VARCHAR(100) COMMENT '创建人',
    create_time DATETIME COMMENT '创建时间',
    sync_date DATE NOT NULL COMMENT '同步日期',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_city (city),
    INDEX idx_status (status),
    INDEX idx_create_time (create_time),
    INDEX idx_sync_date (sync_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='MLS合同-明细数据(B方案)';
""")

# C方案: 变更追踪表
cursor.execute("""
CREATE TABLE IF NOT EXISTS ods_mls_contracts_changes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    change_date DATE NOT NULL COMMENT '变更日期',
    contract_no VARCHAR(100) NOT NULL COMMENT '合同编号',
    change_type ENUM('ADD','UPDATE','DELETE') NOT NULL COMMENT '变更类型',
    old_values JSON COMMENT '旧值',
    new_values JSON COMMENT '新值',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_contract_no (contract_no),
    INDEX idx_change_date (change_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='MLS合同-变更追踪(C方案)';
""")

print(f"[{datetime.now().strftime('%H:%M:%S')}] 表结构创建完成")

# 读取JSON数据
with open('/opt/yjzf/mcp-data/mls_contracts_20260416.json', 'r', encoding='utf-8') as f:
    contracts = json.load(f)

print(f"[{datetime.now().strftime('%H:%M:%S')}] 读取到 {len(contracts)} 条合同记录")

# B方案: 批量参数化插入明细数据
insert_sql = """
INSERT INTO ods_mls_contracts 
(city, region, contract_name, contract_no, status, party_b, creator, create_time, sync_date)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '2026-04-16')
"""

params = []
for c in contracts:
    params.append((
        c['city'], c['region'], c['contract_name'], c['contract_no'],
        c['status'], c['party_b'], c['creator'], c['create_time']
    ))

cursor.executemany(insert_sql, params)
conn.commit()
print(f"[{datetime.now().strftime('%H:%M:%S')}] B方案明细表写入: {cursor.rowcount} 条")

# C方案: 记录变更(首次导入全部为ADD)
change_sql = """
INSERT INTO ods_mls_contracts_changes 
(change_date, contract_no, change_type, new_values)
VALUES (%s, %s, 'ADD', %s)
"""
change_params = []
for c in contracts:
    change_params.append(('2026-04-16', c['contract_no'], json.dumps(c, ensure_ascii=False)))

cursor.executemany(change_sql, change_params)
conn.commit()
print(f"[{datetime.now().strftime('%H:%M:%S')}] C方案变更追踪写入: {cursor.rowcount} 条")

# A方案: 记录每日快照
from collections import Counter
city_counter = Counter([c['city'] for c in contracts])
snapshot_data = {
    'city_stats': dict(city_counter),
    'total': len(contracts)
}

cursor.execute("""
INSERT INTO ods_mls_contracts_daily_snapshot 
(snapshot_date, total_count, city_stats)
VALUES ('2026-04-16', %s, %s)
ON DUPLICATE KEY UPDATE 
total_count = VALUES(total_count),
city_stats = VALUES(city_stats)
""", (len(contracts), json.dumps(snapshot_data, ensure_ascii=False)))
conn.commit()
print(f"[{datetime.now().strftime('%H:%M:%S')}] A方案快照记录完成")

# 交叉验证
cursor.execute("SELECT COUNT(*) FROM ods_mls_contracts WHERE sync_date = '2026-04-16'")
db_count = cursor.fetchone()[0]
print(f"[{datetime.now().strftime('%H:%M:%S')}] 交叉验证: 数据库 {db_count} 条 / JSON {len(contracts)} 条")

if db_count == len(contracts):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 数据一致性验证通过!")
else:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ 数据量不匹配!")

cursor.close()
conn.close()
print(f"[{datetime.now().strftime('%H:%M:%S')}] 导入完成!")
