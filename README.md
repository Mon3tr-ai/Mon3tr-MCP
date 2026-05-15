# Mon3tr-MCP

Hello Hello! 这里是可爱的 Mon3tr 哦，我来给博士们的 llm 赋予灵魂啦! 

## 我能干什么呢？

帮博士终端里的 llm 理解干员档案（从 PRTS wiki ~~?现在不是在用可露希尔写的ZOOT吗?~~），解析关卡数据，还有从一个叫 bing 的平台上搜索网页ヾ(≧▽≦*)o

支持的终端平台：**Windows / macOS / Linux / Android（Termux）**

---

## 环境要求

- Python 3.9+
- 依赖包：

```bash
pip install requests beautifulsoup4 mcp python-docx
```

> Termux 用户：
> ```bash
> pip install requests beautifulsoup4 mcp python-docx --break-system-packages
> ```

---

## 启动方式

```bash
python Mon3tr-MCP.py
```

默认监听 `127.0.0.1:8000`，MCP 端点为 `http://127.0.0.1:8000/mcp`，使用 Streamable HTTP 传输协议。

如需修改端口，编辑文件末尾的启动参数：

```python
mcp.run(transport="streamable-http", host="127.0.0.1", port=8000, path="/mcp")
```

---

## 工具列表

### 搜索 / 网页抓取

#### `bing_search`
用 Bing 搜索网页，返回标题、链接和摘要。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `query` | str | — | 搜索关键词 |
| `num` | int | 10 | 返回结果数量 |
| `domain` | str | `"cn.bing.com"` | Bing 域名，可选 `cn.bing.com`（国内版）或 `www.bing.com`（国际版） |

---

#### `fetch_page`
抓取任意网页的正文内容（去除导航栏、脚本等无关元素），最多返回 5000 字符。

| 参数 | 类型 | 说明 |
|------|------|------|
| `url` | str | 目标网页 URL |

---

#### `fetch_prts_wiki`
从 [prts.wiki](https://prts.wiki) 抓取明日方舟角色页面，最多返回 10000 字符。

| 参数 | 类型 | 说明 |
|------|------|------|
| `character_name` | str | 角色名称，如 `能天使`、`阿米娅` |

---

### 关卡地图解析

> 所需数据来自 [Kengxxiao/ArknightsGameData](https://github.com/Kengxxiao/ArknightsGameData)，
> 关卡 JSON 位于 `gamedata/levels/` 目录下。所有工具均支持本地路径和远端 URL。

#### `lookup_stage`
通过关卡代号、名称或 stageId 查询关卡信息，返回游戏数据文件路径（可直接传给 `parse_map`）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `query` | str | 关卡代号（如 `1-7`、`CE-5`）、名称（如 `当务之急`）或 stageId（如 `main_01-07`） |

输出示例：
```
找到 1 个匹配关卡:

  关卡代号: 1-7
  名称:     暴君
  stageId:  main_01-07
  地图尺寸: 11 x 7
  数据路径: gamedata/levels/obt/main/level_main_01-07.json
```

---

#### `parse_map`
解析关卡 JSON 文件，输出文字地图、门坐标和关卡基本参数。支持本地路径、URL 或仓库相对路径（自动补全远端地址）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `json_file_path` | str | 关卡 JSON 路径/URL，或仓库相对路径（如 `gamedata/levels/obt/main/level_main_01-07.json`） |

输出示例：
```
左上角(0,0)
    y=0 [禁][禁][禁][禁][禁][禁][飞][禁][禁][出][禁] <- 红门(6,0)
    y=1 [蓝][路][路][路][路][不][不][路][不][不][禁]
    y=2 [禁][高][高][高][高][高][高][装][高][高][禁]
    ...
        x=0  x=1  x=2  x=3  x=4  x=5  x=6  x=7  x=8  x=9  x=10

图例:
禁-禁入区 高-高台 路-可部署位 ...

地图尺寸: 8 行 x 11 列
部署上限: 8 个干员
生命值: 3
初始费用: 10
蓝门坐标: (4,7), (5,7), (0,1)
红门坐标: (8,7), (9,7), (0,4), (6,0)
飞行起点坐标: (6,0)
```

> **推荐用法：** 先用 `lookup_stage("1-7")` 获取数据路径，再传给 `parse_map`。

---

#### `get_cell_info`
查询地图格子类型的含义。

| 参数 | 类型 | 说明 |
|------|------|------|
| `cell_type` | str | 单字符类型，如 `高`、`路`、`红` |

---

#### `get_map_legend`
返回完整地图图例，无需参数。

| 符号 | 含义 |
|------|------|
| 禁 | 禁入区，不可通行/不可部署 |
| 高 | 高台，可部署高台干员 |
| 路 | 可部署位，可部署地面干员 |
| 不 | 不可部署位，可通行但不可部署 |
| 穴 | 地穴 |
| 装 | 预设装置/陷阱 |
| 蓝 | 防守点（蓝门） |
| 红 | 敌人生成点（红门） |
| 飞 | 飞行起点，飞行单位生成点（覆盖红门） |
| 进 | 传送进入点 |
| 出 | 传送离开点 |
| 围 | 围墙，可部署围墙 |

---

#### `fetch_gamedata`
从 GitHub 上的 ArknightsGameData 仓库按相对路径获取任意游戏数据文件。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `relative_path` | str | — | 仓库内相对路径，如 `gamedata/excel/character_table.json` |
| `max_chars` | int | 3000 | 返回内容最大字符数 |

---

### 敌人数据查询

> 所需数据文件：`zh_CN/gamedata/excel/enemy_database.json`，同样来自上述 GameData 仓库。

#### `get_level_enemies`
读取关卡 JSON 中的 `enemyDbRefs`，从敌人数据库中匹配并输出本关所有敌人的属性、技能和免疫信息。

| 参数 | 类型 | 说明 |
|------|------|------|
| `level_json_path` | str | 关卡 JSON 文件路径 |
| `enemy_db_path` | str | `enemy_database.json` 文件路径 |

---

#### `get_enemy_by_id`
按 ID 查询单个敌人的详细数据。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enemy_id` | str | — | 敌人 ID，如 `enemy_1000_gopro` |
| `enemy_db_path` | str | — | `enemy_database.json` 文件路径 |
| `level` | int | 0 | 数据等级（0 为基础，精英/BOSS 关卡可能有 level 1+） |

输出包含：名称、描述、等级类型、占用生命点、基础属性（生命值/攻击力/防御力/法抗等）、免疫状态、技能列表。

---

### 干员档案生成

#### `generate_operator_profile`
从 prts.wiki 抓取干员信息，生成格式化的 DOCX 档案文档。包含基本信息、属性、天赋、技能等章节，表格带蓝色表头和灰色标签列。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `operator_name` | str | — | 干员名称，如 `凯尔希·思衡托`、`Mon3tr`、`维什戴尔` |
| `output_path` | str | `None` | 保存路径（含文件名），为 `None` 时保存到当前目录，自动创建不存在的目录 |

输出示例：
```
文档已成功生成：C:\Users\...\Mon3tr 干员档案.docx
```

> 需额外安装 `python-docx`：
> ```bash
> pip install python-docx
> ```

---

## 数据来源

所有游戏数据工具均支持本地路径和远端 URL。不克隆仓库也可直接使用——传入仓库相对路径即可自动从 GitHub 拉取。

### 关卡 JSON / 敌人数据库

```
https://github.com/Kengxxiao/ArknightsGameData
```

克隆后所需文件路径：
```
ArknightsGameData/
└── zh_CN/gamedata/
    ├── levels/                        ← 关卡 JSON（parse_map / get_level_enemies 使用）
    │   ├── obt/main/level_main_*.json
    │   ├── obt/weekly/level_weekly_*.json
    │   └── enemydata/
    │       └── enemy_database.json    ← 敌人数据库
    └── ...
```

### 关卡代号对照表

`lookup_stage` 工具使用的关卡代号/名称对照数据来自：

```
https://github.com/MaaAssistantArknights/MaaAssistantArknights
```

文件路径：`resource/Arknights-Tile-Pos/overview.json`

---
