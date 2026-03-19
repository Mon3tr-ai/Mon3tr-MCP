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
pip install requests beautifulsoup4 mcp
```

> Termux 用户：
> ```bash
> pip install requests beautifulsoup4 mcp --break-system-packages
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
> 关卡 JSON 位于 `zh_CN/gamedata/levels/` 目录下。

#### `parse_map`
解析关卡 JSON 文件，输出文字地图、红蓝门坐标和关卡基本参数。

| 参数 | 类型 | 说明 |
|------|------|------|
| `json_file_path` | str | 关卡 JSON 文件路径，如 `levels/obt/main/level_main_01-01.json` |

输出示例：
```
左上角(0,0)
    y=0 [禁][禁][高][高][高][禁][禁]
    y=1 [红][路][路][路][路][路][蓝] <- 红门(0,1)
    y=2 [禁][禁][高][高][高][禁][禁]
        x=0 x=1 x=2 x=3 x=4 x=5 x=6

图例:
禁-禁入区 高-高台 路-可部署位 ...

地图尺寸: 3 行 x 7 列
部署上限: 8 个干员
生命值: 3
初始费用: 10
蓝门坐标: (6,1)
红门坐标: (0,1)
```

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
| 进 | 传送进入点 |
| 出 | 传送离开点 |
| 围 | 围墙，可部署围墙 |

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

## 数据来源

关卡 JSON 和敌人数据库均可从以下仓库获取：

```
https://github.com/yuanyan3060/ArknightsGameResource
```

克隆后所需文件路径：
```
ArknightsGameData/
├── zh_CN/gamedata/
│   ├── levels/          ← 关卡 JSON（parse_map / get_level_enemies 使用）
│   └── excel/
│       └── enemy_database.json   ← 敌人数据库
```

---
