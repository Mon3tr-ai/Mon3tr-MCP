# Mon3tr-MCP

Hello Hello! 这里是可爱的 Mon3tr 哦，我来给博士们的 llm 赋予灵魂啦!

## 我能干什么呢？

帮博士终端里的 llm 理解干员档案（从 PRTS wiki ~~?现在不是在用可露希尔写的ZOOT吗?~~），解析关卡数据，查询剧情文本，生成/编辑各种文档，还有从一个叫 bing 的平台上搜索网页 ヾ(≧▽≦*)o

支持的终端平台：**Windows / macOS / Linux / Android（Termux）**

---

## 环境要求

- Python 3.9+
- 依赖包：

```bash
pip install requests beautifulsoup4 mcp python-docx openpyxl pypdf reportlab pdf2docx
```

> Termux 用户：
> ```bash
> pip install requests beautifulsoup4 mcp python-docx openpyxl pypdf reportlab pdf2docx --break-system-packages
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

---

#### `parse_map`
解析关卡 JSON 文件，输出文字地图、门坐标和关卡基本参数。支持本地路径、URL 或仓库相对路径（自动补全远端地址）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `json_file_path` | str | 关卡 JSON 路径/URL，或仓库相对路径（如 `gamedata/levels/obt/main/level_main_01-07.json`） |

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
| 红 | 敌人生成点（红门 / tile_start / tile_mpprts_enemy_born） |
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

> 所需数据文件：`gamedata/levels/enemydata/enemy_database.json`，同样来自上述 GameData 仓库。

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

---

### 干员查询

> 数据来自 `character_table.json` 和 `skill_table.json`，优先读取本地 `ArknightsGameData/`，无本地文件时自动从远端拉取。

#### `query_operator`
查询己方干员的详细数据，包括属性、天赋、技能。支持模糊搜索。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | str | — | 干员名称或 ID，如 `凯尔希`、`amiya`、`Mon3tr` |
| `max_results` | int | 5 | 最大返回条数 |

输出包含：名称、英文名、稀有度、职业、分支、位置、势力、满级属性、天赋、技能。

---

### 剧情查询

> 数据来自 `story_review_table.json` 和 `story_table.json`，剧情文本从远端 `gamedata/story/` 拉取。

#### `query_story`
查询和获取明日方舟剧情文本。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `query` | str | `""` | 搜索关键词（章节名、活动名、关卡代号） |
| `story_id` | str | `""` | 剧情 ID（`read` 操作用） |
| `operation` | str | `"search"` | 操作类型：`search`（搜索）、`read`（读取文本）、`list`（列出章节剧情） |
| `max_results` | int | 20 | search 最大返回条数 |
| `show_direction` | bool | `false` | 是否显示舞台指令 |

示例：
```
query_story(query="15-17")                    → 搜索 15-17 相关剧情
query_story(query="离解复合", operation="list") → 列出该活动所有剧情
query_story(story_id="main_15_level_main_15-15_beg", operation="read") → 读取剧情文本
```

---

### 文档生成 / 编辑

#### `generate_operator_profile`
从 prts.wiki 抓取干员信息，生成格式化的 DOCX 档案文档。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `operator_name` | str | — | 干员名称，如 `凯尔希·思衡托`、`Mon3tr` |
| `output_path` | str | `None` | 保存路径，为 `None` 时保存到当前目录 |

---

#### `edit_document`
编辑已有的 DOCX 文档。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `file_path` | str | — | DOCX 文件路径 |
| `operation` | str | — | 操作类型 |
| `old_text` | str | `""` | replace_text 用：查找文本 |
| `new_text` | str | `""` | replace_text 用：替换文本 / edit_table 用：新值 |
| `text` | str | `""` | add_paragraph / add_heading 用：文本内容 |
| `heading` | str | `""` | add_section 用：标题文本 |
| `content` | str | `""` | add_section 用：段落内容（`\n` 分隔多段） |
| `level` | int | `1` | add_heading 用：标题级别（1-4） |
| `position` | int | `-1` | 插入位置索引（-1 为末尾） |
| `row` / `col` | int | `0` | edit_table 用：行列索引 |
| `table_index` | int | `0` | edit_table 用：第几个表格 |

| operation | 功能 |
|-----------|------|
| `read` | 读取文档结构（段落索引+表格内容） |
| `replace_text` | 查找替换文本 |
| `add_paragraph` | 插入段落 |
| `add_heading` | 插入标题（H1-H4） |
| `add_section` | 插入标题+多段落组合 |
| `edit_table` | 修改表格单元格 |

---

#### `edit_excel`
创建和编辑 Excel (.xlsx) 表格。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `file_path` | str | — | Excel 文件路径 |
| `operation` | str | — | 操作类型 |
| `sheet` | str | `""` | 工作表名称（默认活动表） |
| `cell` | str | `""` | 单元格引用，如 `A1` 或范围 `A1:C3` |
| `value` | str | `""` | 单格写入的值 |
| `data` | str | `""` | 批量写入，JSON 二维数组 |
| `formula_str` | str | `""` | 公式（不含 `=`） |
| `bold` | bool | `false` | 是否加粗 |
| `font_color` / `bg_color` | str | `""` | 字体/背景颜色 |
| `align` | str | `""` | 对齐：`left` / `center` / `right` |
| `border` | bool | `false` | 是否加边框 |
| `params` | str | `""` | 高级操作的 JSON 参数 |

| operation | 功能 | params 示例 |
|-----------|------|-------------|
| `create` | 创建新文件 | `data='[["姓名","分数"],["张三",90]]'` |
| `read` | 读取内容 | `cell="A1:D10"` 可选指定范围 |
| `write` | 写入数据 | `cell="A1"`, `data='[[1,2],[3,4]]'` |
| `formula` | 写入公式 | `cell="E2"`, `formula_str="SUM(A2:D2)"` |
| `add_sheet` | 添加工作表 | `sheet="排名"` |
| `format` | 设置格式 | `cell="A1"`, `bold=True`, `bg_color="4472C4"` |
| `merge` | 合并单元格 | `cell="A1:C1"` |
| `col_width` | 设置列宽 | `col_width="A:20,B:15"` |
| `row_height` | 设置行高 | `row_height="1:30,2:20"` |
| `chart` | 添加图表 | `params='{"type":"bar","title":"月度对比","pos":"F2"}'` |
| `conditional_format` | 条件格式 | `params='{"type":"color_scale"}'` |
| `data_validation` | 下拉列表 | `params='{"list":"选项1,选项2"}'` |
| `freeze_panes` | 冻结窗格 | `params='{"cell":"B2"}'` |
| `auto_filter` | 自动筛选 | `cell="A1:D10"` |
| `image` | 插入图片 | `params='{"path":"logo.png","width":200}'` |

---

#### `edit_pdf`
读取和生成 PDF 文件。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `file_path` | str | — | PDF 文件路径 |
| `operation` | str | — | 操作类型 |
| `output_path` | str | `""` | 输出文件路径 |
| `pages` | str | `""` | 页码范围，如 `1,3,5-8` |
| `content` | str | `""` | create 用：文本内容（`\n` 分段） |
| `title` | str | `""` | create 用：文档标题 |
| `author` | str | `""` | create 用：文档作者 |
| `font_size` | int | `12` | create 用：字号 |
| `page_size` | str | `"A4"` | create 用：`A4` / `Letter` / `A5` |
| `params` | str | `""` | JSON 参数 |

| operation | 功能 |
|-----------|------|
| `read` | 读取 PDF 文本内容 |
| `info` | 获取元信息（页数/标题/作者/尺寸） |
| `create` | 从文本生成 PDF（自动注册中文字体） |
| `merge` | 合并多个 PDF（`params='{"files":["a.pdf","b.pdf"]}'`） |
| `extract` | 提取指定页面 |
| `to_word` | PDF 转 Word (.docx) |

---

## 数据来源

所有游戏数据工具均支持本地路径和远端 URL。不克隆仓库也可直接使用——传入仓库相对路径即可自动从 GitHub 拉取。

### 游戏数据仓库

```
https://github.com/Kengxxiao/ArknightsGameData
```

克隆到项目根目录下的 `ArknightsGameData/` 即可启用本地优先读取：

```
ArknightsGameData/
└── gamedata/
    ├── excel/
    │   ├── character_table.json       ← 干员数据（query_operator 使用）
    │   ├── skill_table.json           ← 技能数据（query_operator 使用）
    │   ├── enemy_database.json        ← 敌人数据库（get_level_enemies / get_enemy_by_id 使用）
    │   ├── story_table.json           ← 剧情索引（query_story 使用）
    │   └── story_review_table.json    ← 剧情回顾索引（query_story 使用）
    ├── levels/
    │   ├── obt/main/level_main_*.json ← 关卡 JSON（parse_map / get_level_enemies 使用）
    │   └── enemydata/
    │       └── enemy_database.json
    └── story/                         ← 剧情文本（query_story read 操作使用，仅远端）
        └── obt/main/level_main_*.txt
```

### 关卡代号对照表

`lookup_stage` 工具使用的关卡代号/名称对照数据来自：

```
https://github.com/MaaAssistantArknights/MaaAssistantArknights
```

---

## 完整依赖一览

| 包 | 用途 |
|----|------|
| `requests` | HTTP 请求 |
| `beautifulsoup4` | 网页解析 |
| `mcp` | MCP 服务框架 |
| `python-docx` | DOCX 生成/编辑 |
| `openpyxl` | Excel 生成/编辑 |
| `pypdf` | PDF 读取 |
| `reportlab` | PDF 生成 |
| `pdf2docx` | PDF 转 Word |
