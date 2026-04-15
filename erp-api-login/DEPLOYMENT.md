# ERP API Login 技能部署包

## 版本信息

- **版本**: v20260327-final
- **发布日期**: 2026-03-27 17:11
- **文件总数**: 23 个
- **总大小**: 275,378 字节

## 核心功能分类

### 1. 人事数据管理
- 人事数据导出 (`export-personnel.py`)
- 指标字典获取 (`get-statistics-dict.py`)
- 自定义报表导出 (`create-custom-export.py`)
- 导出文件列表 (`get-export-list.py`)

### 2. 新房合同管理
- 合同导出与报表生成 (`generate-report.py`)
- 数据处理脚本 (`process-new-house-data-v4.py` 等)

### 3. 项目管理
- 项目明细导出 (`export-project-list.py`)
- 0 成交项目统计 (`export-zero-deal-projects.py`)

### 4. 带看管理
- 带看数据导出 (`export-visit-list.py`)
- 带看进场统计 (`export-visit-statistics.py`)

### 5. 竞对分析
- 竞对数据导出 (`export-rival-stats.py`)
- 落后项目报表 (`export-lagging-projects.py`)

## 部署步骤

```bash
# 1. 备份原技能（推荐）
cp -r ~/.openclaw/skills/erp-api-login ~/.openclaw/skills/erp-api-login.backup.2026-03-27 17:11

# 2. 解压部署包
unzip ~/Desktop/erp-api-login-skill-v20260327-final.zip -d ~/.openclaw/skills/

# 3. 验证部署
python3 ~/.openclaw/skills/erp-api-login/scripts/export-personnel.py --help
```

## 快速使用

### 人事数据导出
```bash
python3 export-personnel.py
```

### 生成新房合同报表
```bash
python3 generate-report.py --export-weekly --week-start 2026-03-24 --week-end 2026-03-30
```

### 落后项目报表
```bash
python3 export-lagging-projects.py --input 竞对数据文件.xlsx
```

## 文件清单

| 类别 | 文件数 | 总大小 |
|------|--------|--------|
| 核心文件 | 2 | 27,330 字节 |
| ERP API 客户端 | 1 | 63,097 字节 |
| 凭证配置 | 1 | 6,068 字节 |
| 人事数据相关 | 4 | 12,784 字节 |
| 新房合同相关 | 5 | 80,039 字节 |
| 项目相关 | 2 | 18,073 字节 |
| 带看相关 | 2 | 23,195 字节 |
| 竞对分析 | 2 | 17,701 字节 |
| 文档 | 5 | 29,092 字节 |
| **总计** | **24** | **275,378 字节** |

---
**MD5**: 待计算
**生成时间**: 2026-03-27 17:11
