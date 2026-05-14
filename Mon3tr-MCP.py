"""
Mon3tr-MCP — 明日方舟 MCP 工具集
支持 Windows / macOS / Linux（含 Android Termux）

工具列表:
  搜索/抓取: bing_search · fetch_page · fetch_prts_wiki
  游戏数据:  fetch_gamedata（按仓库相对路径从 GitHub 拉取，带缓存）
  地图解析:  parse_map · get_cell_info · get_map_legend
  敌人数据:  get_level_enemies · get_enemy_by_id
  注: parse_map / get_level_enemies / get_enemy_by_id 均支持本地路径、完整 URL
      或仓库相对路径（自动补全远端地址）
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

# ── 远端游戏数据源 ────────────────────────────────────────────────
_GAMEDATA_BASE_URL = (
    "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN"
)
_json_cache: dict = {}

# ── Windows 控制台 UTF-8 输出修正 ────────────────────────────────
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

mcp = FastMCP("Mon3tr-MCP", host="127.0.0.1", port=8000)


# ══════════════════════════════════════════════════════════════════
# 搜索 / 网页抓取工具
# ══════════════════════════════════════════════════════════════════

_MOBILE_UA = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Mobile Safari/537.36"
)


@mcp.tool()
def bing_search(query: str, num: int = 10) -> str:
    """用 Bing 搜索网页，返回标题、链接和摘要"""
    headers = {
        "User-Agent": _MOBILE_UA,
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.bing.com/",
    }
    url = f"https://www.bing.com/search?q={query}&count={num}"
    res = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")
    results = []
    for li in soup.select("li.b_algo"):
        title = li.select_one("h2")
        link = li.select_one("a")
        snippet = li.select_one(".b_caption p")
        if title and link:
            results.append(
                f"标题：{title.get_text()}\n"
                f"链接：{link['href']}\n"
                f"摘要：{snippet.get_text() if snippet else '无'}"
            )
    return "\n---\n".join(results) if results else "没有找到结果"


@mcp.tool()
def fetch_page(url: str) -> str:
    """抓取指定网页的正文内容"""
    headers = {
        "User-Agent": _MOBILE_UA,
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        content = "\n".join(lines)
        return content[:3000] + "..." if len(content) > 3000 else content
    except Exception as e:
        return f"抓取失败：{e}"


@mcp.tool()
def fetch_prts_wiki(character_name: str) -> str:
    """从 prts.wiki 抓取明日方舟角色详细信息"""
    headers = {
        "User-Agent": _MOBILE_UA,
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    url = f"https://prts.wiki/w/{character_name}"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "table"]):
            tag.decompose()
        content = soup.find("div", {"id": "mw-content-text"})
        if not content:
            return "未找到该角色页面，请检查角色名称"
        text = content.get_text(separator="\n")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        result = "\n".join(lines)
        return result[:5000] + "..." if len(result) > 5000 else result
    except Exception as e:
        return f"抓取失败：{e}"


# ══════════════════════════════════════════════════════════════════
# 通用 JSON 加载（本地路径 / HTTP URL，带内存缓存）
# ══════════════════════════════════════════════════════════════════

def _load_json(path_or_url: str) -> dict:
    if path_or_url.startswith(("http://", "https://")):
        if path_or_url not in _json_cache:
            res = requests.get(path_or_url, timeout=15)
            res.raise_for_status()
            _json_cache[path_or_url] = res.json()
        return _json_cache[path_or_url]
    with Path(path_or_url).open("r", encoding="utf-8") as f:
        return json.load(f)


def _is_accessible(path_or_url: str) -> bool:
    return path_or_url.startswith(("http://", "https://")) or Path(path_or_url).is_file()


# ══════════════════════════════════════════════════════════════════
# 地图解析辅助函数
# ══════════════════════════════════════════════════════════════════

_TILE_MAP = {
    "tile_forbidden":   "禁",
    "tile_wall":        "高",
    "tile_road":        "路",
    "tile_floor":       "不",
    "tile_hole":        "穴",
    "tile_telin":       "进",
    "tile_telout":      "出",
    "tile_fence_bound": "围",
}

_FLY_START_TILES = {"tile_flystart"}

_CELL_DESC = {
    "禁": "禁入区 - 不可通行/不可部署",
    "高": "高台 - 可部署高台干员",
    "路": "可部署位 - 可部署地面干员",
    "不": "不可部署位 - 可通行但不可部署",
    "穴": "地穴",
    "装": "装置 - 预设装置/陷阱",
    "蓝": "目标点 - 防守点(蓝门)",
    "红": "侵入点 - 敌人生成点(红门)",
    "进": "传送进入点",
    "出": "传送离开点",
    "围": "围墙 - 可部署围墙",
    "飞": "飞行起点 - 飞行单位生成点",
    "?": "未知区域",
}

_LEVEL_TYPE_NAME = {0: "普通", 1: "精英", 2: "BOSS"}


def _parse_arknights_map_data(data: dict):
    """解析已加载的关卡 JSON dict，返回 (game_grid, blue_doors, red_doors, fly_doors, data)"""
    map_matrix = data["mapData"]["map"]
    tiles = data["mapData"]["tiles"]
    rows = len(map_matrix)
    cols = len(map_matrix[0])

    grid = [["?" for _ in range(cols)] for _ in range(rows)]
    fly_start_points: set = set()

    for y in range(rows):
        for x in range(cols):
            tile_index = map_matrix[y][x]
            tile_key = tiles[tile_index].get("tileKey") if tile_index < len(tiles) else None
            if tile_key in _TILE_MAP:
                grid[rows - y - 1][x] = _TILE_MAP[tile_key]
            elif tile_key in _FLY_START_TILES:
                fly_start_points.add((y, x))
            # tile_start / tile_end 留作 '?' 占位，后续被门覆盖

    # 标记预设装置（在标记门之前，确保门的排除条件能正确检查 '装'）
    if "predefines" in data and "tokenInsts" in data["predefines"]:
        for token in data["predefines"]["tokenInsts"]:
            r = token["position"]["row"]
            c = token["position"]["col"]
            grid[r][c] = "装"

    blue_doors: set = set()
    for route in data.get("routes", []):
        sp, ep = route["startPosition"], route["endPosition"]
        if sp["row"] != ep["row"] or sp["col"] != ep["col"]:
            er, ec = ep["row"], ep["col"]
            if grid[er][ec] not in {"穴", "装"}:
                grid[er][ec] = "蓝"
                blue_doors.add((er, ec))

    red_doors: set = set()
    for route in data.get("routes", []):
        sp, ep = route["startPosition"], route["endPosition"]
        if sp["row"] != ep["row"] or sp["col"] != ep["col"]:
            sr, sc = sp["row"], sp["col"]
            if grid[sr][sc] not in {"路", "不", "围", "装", "穴"}:
                grid[sr][sc] = "红"
                red_doors.add((sr, sc))

    # 标记飞行单位生成点（覆盖红门）
    for fy, fx in fly_start_points:
        grid[rows - fy - 1][fx] = "飞"

    # 坐标系翻转：game_grid[0] 对应屏幕上方
    game_grid = [["?" for _ in range(cols)] for _ in range(rows)]
    for row in range(rows):
        for col in range(cols):
            game_grid[rows - 1 - row][col] = grid[row][col]

    # fly_start_points 是 JSON 坐标，转为与 blue_doors/red_doors 一致的格式
    fly_doors = {(rows - 1 - fy, fx) for fy, fx in fly_start_points}

    return game_grid, blue_doors, red_doors, fly_doors, data


def _build_text_map(game_grid, blue_doors, red_doors) -> str:
    rows = len(game_grid)
    cols = len(game_grid[0])
    lines = ["左上角(0,0)"]
    for y in range(rows):
        row_str = f"    y={y} [" + "][".join(game_grid[y]) + "]"
        for r, c in red_doors:
            if rows - 1 - r == y:
                row_str += f" <- 红门({c},{rows-1-r})"
        lines.append(row_str)
    x_width = max(len(str(cols - 1)), 2)
    x_axis = "        " + "".join(
        f"x={x}".ljust(x_width + 3) for x in range(cols)
    )
    lines.append(x_axis)
    lines.append("\n图例:")
    lines.append(
        "禁-禁入区 高-高台 路-可部署位 不-不可部署位 穴-地穴 "
        "装-装置 蓝-防守点 红-侵入点 进-传送进入 出-传送离开 围-围墙 飞-飞行起点"
    )
    return "\n".join(lines)


def _get_cell_description(cell_type: str) -> str:
    return _CELL_DESC.get(cell_type, "未知区域")


# ══════════════════════════════════════════════════════════════════
# 地图 MCP 工具
# ══════════════════════════════════════════════════════════════════

@mcp.tool()
def parse_map(json_file_path: str) -> str:
    """
    解析明日方舟关卡 JSON 并返回文字地图及关卡基本信息。支持本地路径或 URL。

    参数:
        json_file_path: 关卡 JSON 的本地路径或完整 URL。
                        也可传入仓库相对路径（如 gamedata/levels/obt/main/level_main_01-08.json），
                        将自动拼接远端地址。

    返回:
        文字地图 + 红/蓝门坐标 + 关卡选项信息
    """
    if not json_file_path.startswith(("http://", "https://")):
        if not Path(json_file_path).is_file():
            # 尝试视作仓库相对路径从远端获取
            json_file_path = f"{_GAMEDATA_BASE_URL}/{json_file_path.lstrip('/')}"
    try:
        data = _load_json(json_file_path)
        game_grid, blue_doors, red_doors, fly_doors, data = _parse_arknights_map_data(data)
    except requests.HTTPError as e:
        return f"错误: 远端请求失败 {e}"
    except json.JSONDecodeError:
        return f"错误: 不是有效的 JSON"
    except KeyError as e:
        return f"错误: JSON 缺少必要字段 {e}"
    except Exception as e:
        return f"处理时发生错误: {e}"

    rows = len(game_grid)
    text_map = _build_text_map(game_grid, blue_doors, red_doors)
    blue_list = ", ".join(f"({c},{rows-1-r})" for r, c in sorted(blue_doors)) or "无"
    red_list  = ", ".join(f"({c},{rows-1-r})" for r, c in sorted(red_doors))  or "无"
    fly_list  = ", ".join(f"({c},{rows-1-r})" for r, c in sorted(fly_doors)) or "无"
    opts = data.get("options", {})
    info_lines = [
        f"地图尺寸: {rows} 行 x {len(game_grid[0])} 列",
        f"部署上限: {opts.get('characterLimit', '未知')} 个干员",
        f"生命值: {opts.get('maxLifePoint', '未知')}",
        f"初始费用: {opts.get('initialCost', '未知')}",
        f"蓝门坐标: {blue_list}",
        f"红门坐标: {red_list}",
        f"飞行起点坐标: {fly_list}",
    ]
    return text_map + "\n\n" + "\n".join(info_lines)


@mcp.tool()
def get_cell_info(cell_type: str) -> str:
    """
    查询地图格子类型的含义。

    参数:
        cell_type: 单字符类型，如 '高'、'路'、'红' 等
    """
    return _get_cell_description(cell_type)


@mcp.tool()
def get_map_legend() -> str:
    """返回完整的地图图例说明。"""
    return "\n".join(f"{k}: {v}" for k, v in _CELL_DESC.items())


# ══════════════════════════════════════════════════════════════════
# 敌人数据辅助函数
# ══════════════════════════════════════════════════════════════════

def _load_enemy_db(db_path_or_url: str) -> dict:
    raw = _load_json(db_path_or_url)
    return {entry["key"]: entry["value"] for entry in raw["enemies"]}


def _mv(field):
    """取 m_value（当 m_defined=True 时），否则返回 None。"""
    if field and field.get("m_defined"):
        return field.get("m_value")
    return None


def _merge_enemy_data(base: dict, overwrite: Optional[dict]) -> dict:
    """将 overwrittenData 中 m_defined=True 的字段覆盖到 base 上。"""
    if not overwrite:
        return base
    merged = dict(base)
    for field in (
        "name", "description", "prefabKey", "applyWay", "motion",
        "enemyTags", "lifePointReduce", "levelType", "rangeRadius",
        "numOfExtraDrops", "viewRadius", "notCountInTotal",
    ):
        ow_field = overwrite.get(field)
        if ow_field and ow_field.get("m_defined"):
            merged[field] = ow_field
    if "attributes" in overwrite:
        merged_attrs = dict(base.get("attributes", {}))
        for attr_key, attr_val in overwrite["attributes"].items():
            if attr_val and attr_val.get("m_defined"):
                merged_attrs[attr_key] = attr_val
        merged["attributes"] = merged_attrs
    return merged


def _format_enemy(enemy_id: str, enemy_data: dict, data_level: int = 0) -> str:
    attrs = enemy_data.get("attributes", {})

    def av(key):
        f = attrs.get(key)
        return _mv(f) if f else None

    lines = ["[{}]".format(enemy_id)]

    name = _mv(enemy_data.get("name"))
    if name:
        lines.append(f"名称: {name}")
    lines.append(f"数据级别: {data_level}")

    desc = _mv(enemy_data.get("description"))
    if desc:
        lines.append(f"描述: {re.sub(r'<[^>]+>', '', desc)}")

    tags = _mv(enemy_data.get("enemyTags"))
    if tags:
        lines.append(f"标签: {', '.join(tags)}")

    level_type = _mv(enemy_data.get("levelType"))
    if level_type is not None:
        lines.append(f"等级类型: {_LEVEL_TYPE_NAME.get(level_type, str(level_type))}")

    lp = _mv(enemy_data.get("lifePointReduce"))
    if lp is not None:
        lines.append(f"占用生命点: {lp}")

    rr = _mv(enemy_data.get("rangeRadius"))
    if rr:
        lines.append(f"攻击半径: {rr}")

    stat_fields = [
        ("maxHp",            "生命值"),
        ("atk",              "攻击力"),
        ("def",              "防御力"),
        ("magicResistance",  "法抗(%)"),
        ("moveSpeed",        "移动速度"),
        ("attackSpeed",      "攻击速度"),
        ("baseAttackTime",   "攻击间隔(s)"),
        ("massLevel",        "重量等级"),
        ("blockCnt",         "阻挡数"),
        ("hpRecoveryPerSec", "每秒回血"),
    ]
    stat_lines = [
        f"  {label}: {av(key)}"
        for key, label in stat_fields
        if av(key) not in (None, 0, 0.0)
    ]
    if stat_lines:
        lines.append("属性:")
        lines.extend(stat_lines)

    immune_keys = [
        ("stunImmune",     "眩晕免疫"),
        ("silenceImmune",  "沉默免疫"),
        ("sleepImmune",    "睡眠免疫"),
        ("frozenImmune",   "冻结免疫"),
        ("levitateImmune", "浮空免疫"),
    ]
    immunities = [label for key, label in immune_keys if av(key)]
    if immunities:
        lines.append(f"免疫: {', '.join(immunities)}")

    skills = enemy_data.get("skills")
    if skills:
        lines.append("技能:")
        for sk in skills:
            bb_str = ", ".join(
                f"{b['key']}={b['value']}"
                for b in sk.get("blackboard", [])
                if b.get("value") is not None
            )
            sk_line = f"  - {sk.get('prefabKey', '?')} (冷却:{sk.get('cooldown', 0)}s)"
            if bb_str:
                sk_line += f" [{bb_str}]"
            lines.append(sk_line)

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════
# 敌人 MCP 工具
# ══════════════════════════════════════════════════════════════════

@mcp.tool()
def get_level_enemies(level_json_path: str, enemy_db_path: str) -> str:
    """
    读取关卡 JSON 的 enemyDbRefs，从 enemy_database.json 中查找敌人数据。
    两个参数均支持本地路径或 URL；也可传入仓库相对路径自动补全远端地址。

    参数:
        level_json_path: 关卡 JSON 路径/URL（如 gamedata/levels/obt/main/level_main_01-08.json）
        enemy_db_path:   enemy_database.json 路径/URL（如 gamedata/levels/enemydata/enemy_database.json）
    """
    def _resolve(p: str) -> str:
        if p.startswith(("http://", "https://")) or Path(p).is_file():
            return p
        return f"{_GAMEDATA_BASE_URL}/{p.lstrip('/')}"

    level_json_path = _resolve(level_json_path)
    enemy_db_path   = _resolve(enemy_db_path)
    try:
        level_data = _load_json(level_json_path)
        enemy_db   = _load_enemy_db(enemy_db_path)
    except requests.HTTPError as e:
        return f"错误: 远端请求失败 {e}"
    except json.JSONDecodeError as e:
        return f"错误: JSON 解析失败 - {e}"
    except Exception as e:
        return f"错误: {e}"

    refs = level_data.get("enemyDbRefs", [])
    if not refs:
        return "该关卡没有 enemyDbRefs 数据"

    results, not_found = [], []
    for ref in refs:
        eid   = ref["id"]
        level = ref.get("level", 0)
        ow    = ref.get("overwrittenData")
        if eid not in enemy_db:
            not_found.append(eid)
            continue
        entries    = enemy_db[eid]
        base_entry = next((e for e in entries if e["level"] == 0), entries[0])
        base_data  = base_entry["enemyData"]
        if level != 0:
            diff_entry = next((e for e in entries if e["level"] == level), None)
            if diff_entry:
                base_data = _merge_enemy_data(base_data, diff_entry["enemyData"])
        merged = _merge_enemy_data(base_data, ow)
        results.append(_format_enemy(eid, merged, data_level=level))

    output = f"关卡敌人数据（共 {len(results)} 种）\n" + "=" * 50 + "\n"
    output += "\n\n".join(results)
    if not_found:
        output += f"\n\n未在数据库中找到的敌人: {', '.join(not_found)}"
    return output


@mcp.tool()
def get_enemy_by_id(enemy_id: str, enemy_db_path: str, level: int = 0) -> str:
    """
    从 enemy_database.json 按 ID 查询单个敌人的数据。支持本地路径或 URL。

    参数:
        enemy_id:      敌人 ID，如 enemy_1000_gopro
        enemy_db_path: enemy_database.json 的路径/URL，或仓库相对路径
                       （如 gamedata/levels/enemydata/enemy_database.json）
        level:         数据等级（默认 0；精英/BOSS 关卡可能有 level 1+）
    """
    if not enemy_db_path.startswith(("http://", "https://")) and not Path(enemy_db_path).is_file():
        enemy_db_path = f"{_GAMEDATA_BASE_URL}/{enemy_db_path.lstrip('/')}"
    try:
        enemy_db = _load_enemy_db(enemy_db_path)
    except requests.HTTPError as e:
        return f"错误: 远端请求失败 {e}"
    except Exception as e:
        return f"错误: {e}"

    if enemy_id not in enemy_db:
        return f"未找到敌人: {enemy_id}"

    entries    = enemy_db[enemy_id]
    base_entry = next((e for e in entries if e["level"] == 0), entries[0])
    base_data  = base_entry["enemyData"]
    if level != 0:
        diff_entry = next((e for e in entries if e["level"] == level), None)
        if diff_entry:
            base_data = _merge_enemy_data(base_data, diff_entry["enemyData"])
    return _format_enemy(enemy_id, base_data, data_level=level)


# ══════════════════════════════════════════════════════════════════
# 远端游戏数据获取工具
# ══════════════════════════════════════════════════════════════════

@mcp.tool()
def fetch_gamedata(relative_path: str, max_chars: int = 3000) -> str:
    """
    从 GitHub 上的 ArknightsGameData 仓库（Kengxxiao/ArknightsGameData，zh_CN 分支）
    按相对路径获取游戏数据文件，结果以 JSON 字符串返回（带缓存）。

    参数:
        relative_path: 仓库内相对路径，如
                       gamedata/excel/character_table.json
                       gamedata/excel/skill_table.json
                       gamedata/levels/obt/main/level_main_01-08.json
                       gamedata/levels/enemydata/enemy_database.json
        max_chars:     返回内容最大字符数（默认 3000，大文件可调大）

    返回:
        JSON 字符串（超出 max_chars 时截断并提示）
    """
    url = f"{_GAMEDATA_BASE_URL}/{relative_path.lstrip('/')}"
    try:
        data = _load_json(url)
    except requests.HTTPError as e:
        return f"错误: 远端请求失败 {e}\n请求地址: {url}"
    except Exception as e:
        return f"错误: {e}"
    content = json.dumps(data, ensure_ascii=False, indent=2)
    if len(content) > max_chars:
        return content[:max_chars] + f"\n\n...(已截断，完整长度 {len(content)} 字符，请增大 max_chars)"
    return content


# ══════════════════════════════════════════════════════════════════
# 关卡查询工具
# ══════════════════════════════════════════════════════════════════

_STAGE_OVERVIEW_URL = (
    "https://raw.githubusercontent.com/MaaAssistantArknights/"
    "MaaAssistantArknights/dev-v2/resource/Arknights-Tile-Pos/overview.json"
)
_stage_overview_cache: Optional[dict] = None


def _load_stage_overview() -> dict:
    global _stage_overview_cache
    if _stage_overview_cache is None:
        res = requests.get(_STAGE_OVERVIEW_URL, timeout=15)
        res.raise_for_status()
        _stage_overview_cache = res.json()
    return _stage_overview_cache


@mcp.tool()
def lookup_stage(query: str) -> str:
    """
    通过关卡代号、名称或 stageId 查询关卡信息及游戏数据文件路径。

    参数:
        query: 关卡代号（如 "1-7"、"CE-5"、"GT-1"）、
               关卡名称（如 "当务之急"、"龙门外环"）或
               stageId（如 "main_01-07"）

    返回:
        匹配的关卡列表，包含代号、名称、stageId、
        游戏数据 JSON 路径（可用于 parse_map / fetch_gamedata）
    """
    try:
        overview = _load_stage_overview()
    except Exception as e:
        return f"错误: 无法获取关卡数据表 {e}"

    query_lower = query.lower().strip()
    results = []
    for entry in overview.values():
        code = entry.get("code", "")
        name = entry.get("name", "")
        stage_id = entry.get("stageId", "")
        if (query_lower in code.lower()
                or query_lower in name
                or query_lower in stage_id.lower()):
            results.append(entry)

    if not results:
        return f"未找到匹配 '{query}' 的关卡"

    lines = [f"找到 {len(results)} 个匹配关卡:", ""]
    for e in results[:20]:
        level_id = e.get("levelId", "")
        json_path = f"gamedata/levels/{level_id}.json"
        lines.append(f"  关卡代号: {e.get('code', '?')}")
        lines.append(f"  名称:     {e.get('name', '?')}")
        lines.append(f"  stageId:  {e.get('stageId', '?')}")
        lines.append(f"  地图尺寸: {e.get('width', '?')} x {e.get('height', '?')}")
        lines.append(f"  数据路径: {json_path}")
        lines.append("")
    if len(results) > 20:
        lines.append(f"... 共 {len(results)} 条，仅显示前 20 条")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
