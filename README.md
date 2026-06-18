# FilmCutter — 数据库部署说明

## 概述

FilmCutter 使用 **SQLite** 作为本地数据库，默认文件名为 `data.db`，存放于项目根目录。

数据库无需手动创建或迁移——程序首次启动时会**自动建表**。SQLite 是零配置的嵌入式数据库，不需要安装任何数据库服务。

## 环境要求

| 组件 | 说明 |
|------|------|
| Python | 3.x（开发环境 3.12+） |
| PyQt5 | `pip install PyQt5` |
| FFmpeg | 需在系统 PATH 中可用 |
| SQLite | Python 标准库自带，无需额外安装 |

## 快速开始

```bash
# 1. 创建虚拟环境（首次）
python -m venv .venv

# 2. 激活虚拟环境
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 3. 安装依赖
pip install PyQt5

# 4. 启动程序（数据库自动创建）
python movie_gui.py
# 或
python run.py
```

首次启动后，项目根目录会自动生成 `data.db` 文件。

## 数据库表结构

### actors（演员表）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增主键 |
| country | TEXT | NOT NULL | 国家/地区代码 |
| name | TEXT | NOT NULL | 演员姓名 |
| chn_name | TEXT | | 中文名（可选） |
| | | UNIQUE(country, name) | 同国家同名为同一演员 |

国家代码：`CHN`（中国）、`JAP`（日本）、`KOR`（韩国）、`WEST`（西方）、`SLA`（斯拉夫）、`SEA`（东南亚）、`LTA`（拉美）。

### projects（项目表）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增主键 |
| slug | TEXT | NOT NULL UNIQUE | 项目标识，格式 `Movie.Year` 或 `Movie.Year.S01E01` |
| movie | TEXT | NOT NULL | 影片名 |
| year | INTEGER | NOT NULL | 年份 |
| is_series | INTEGER | NOT NULL DEFAULT 0 | 是否为剧集（0=电影, 1=剧集） |
| season | INTEGER | | 季数（剧集时使用） |
| source_file_path | TEXT | NOT NULL | 源视频文件路径 |
| target_base_path | TEXT | NOT NULL | 输出目录路径 |

### project_actors（项目-演员关联表）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| project_id | INTEGER | NOT NULL | 外键 → projects.id |
| actor_id | INTEGER | NOT NULL | 外键 → actors.id |
| | | PRIMARY KEY(project_id, actor_id) | 联合主键 |

## 数据库文件管理

- **备份**：直接复制 `data.db` 文件即可。
- **重置**：删除 `data.db`，重启程序会自动重建空库。
- **多库**：程序支持通过 `db_path` 参数指定不同的数据库路径，可以按项目/场景切换数据库。
- **位置**：`data.db` 已加入 `.gitignore`，不会被提交到版本控制。

## 无数据迁移

本项目采用**“删表重建”策略**处理 schema 变更，不维护迁移脚本。

具体逻辑（见 `movie_core.py`）：
- `ActorManager._init_db()`：检测 `actors` 表的列结构，若缺少 `id` 列或存在 `created_at` 列（旧版 schema），删除旧表后重建。
- `ProjectManager._init_db()`：检测 `projects` 表的列结构，若存在 `country` 或 `updated_at` 列（旧版 schema），删除 `projects` 和 `project_actors` 表后重建。

这意味着升级到新版本 schema 时**旧数据会丢失**。如需要保留数据，请在升级前手动备份 `data.db`，并在升级后重新录入。
