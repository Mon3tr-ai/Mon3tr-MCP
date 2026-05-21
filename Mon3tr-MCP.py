"""
Mon3tr-MCP — 明日方舟 MCP 工具集
支持 Windows / macOS / Linux（含 Android Termux）

工具列表:
  搜索/抓取: bing_search · fetch_page · fetch_prts_wiki
  游戏数据:  fetch_gamedata（按仓库相对路径从 GitHub 拉取，带缓存）
  地图解析:  parse_map · get_cell_info · get_map_legend
  敌人数据:  get_level_enemies · get_enemy_by_id
  文档工具:  generate_operator_profile · edit_document · edit_excel · edit_pdf
  干员查询:  query_operator
  剧情工具:  query_story
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
def bing_search(query: str, num: int = 10, domain: str = "cn.bing.com") -> str:
    """
    用 Bing 搜索网页，返回标题、链接和摘要。

    参数:
        query: 搜索关键词
        num: 返回结果数量（默认10）
        domain: Bing 域名，可选 "cn.bing.com"（国内版，默认）或 "www.bing.com"（国际版）
    """
    if domain not in ("cn.bing.com", "www.bing.com"):
        domain = "cn.bing.com"
    headers = {
        "User-Agent": _MOBILE_UA,
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": f"https://{domain}/",
    }
    url = f"https://{domain}/search?q={query}&count={num}"
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
    "tile_forbidden":        "禁",
    "tile_wall":             "高",
    "tile_road":             "路",
    "tile_floor":            "不",
    "tile_hole":             "穴",
    "tile_telin":            "进",
    "tile_telout":           "出",
    "tile_fence_bound":      "围",
    "tile_start":            "红",
    "tile_end":              "蓝",
    "tile_mpprts_enemy_born": "红",
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
# 干员档案文档生成工具
# ══════════════════════════════════════════════════════════════════

def _set_cell_shading(cell, color):
    """设置单元格背景色"""
    from docx.oxml.ns import qn
    shading_elm = cell._element.get_or_add_tcPr()
    shading = shading_elm.makeelement(qn('w:shd'), {
        qn('w:fill'): color,
        qn('w:val'): 'clear'
    })
    shading_elm.append(shading)


def _extract_operator_info(soup):
    """从prts wiki页面提取干员信息"""
    info = {
        'name': '',
        'gender': '',
        'combat_experience': '',
        'birthplace': '',
        'birthday': '',
        'race': '',
        'height': '',
        'infection_status': '',
        'profession': '',
        'sub_profession': '',
        'redeploy_time': '',
        'deploy_cost': '',
        'block_count': '',
        'attack_interval': '',
        'faction': '',
    }

    # 获取页面文本
    text = soup.get_text(separator='\n')

    # 提取基本信息
    patterns = {
        'name': r'【代号】(.+)',
        'gender': r'【性别】(.+)',
        'combat_experience': r'【战斗经验】(.+)',
        'birthplace': r'【出身地】(.+)',
        'birthday': r'【生日】(.+)',
        'race': r'【种族】(.+)',
        'height': r'【身高】(.+)',
        'infection_status': r'【矿石病感染情况】(.+)',
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            info[key] = match.group(1).strip()

    # 提取属性信息
    attr_patterns = {
        'redeploy_time': r'再部署时间\s*(\d+s)',
        'deploy_cost': r'初始部署费用\s*(\d+→\d+)',
        'block_count': r'阻挡数\s*(\d+)',
        'attack_interval': r'攻击间隔\s*([\d.]+s)',
        'faction': r'所属势力\s*(.+)',
    }

    for key, pattern in attr_patterns.items():
        match = re.search(pattern, text)
        if match:
            info[key] = match.group(1).strip()

    return info


@mcp.tool()
def generate_operator_profile(operator_name: str, output_path: Optional[str] = None) -> str:
    """
    生成干员档案DOCX文档。

    参数:
        operator_name: 干员名称（如 "凯尔希·思衡托"、"Mon3tr"、"维什戴尔"）
        output_path: 保存路径（含文件名），为 None 时保存到当前目录

    返回:
        生成的DOCX文件路径
    """
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT
        from docx.oxml.ns import qn
    except ImportError:
        return "错误: 缺少 python-docx 库，请运行 'pip install python-docx' 安装"

    # 获取prts wiki页面
    url = f"https://prts.wiki/w/{operator_name}"
    try:
        res = requests.get(url, headers={"User-Agent": _MOBILE_UA}, timeout=15)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
    except Exception as e:
        return f"错误: 无法获取页面 {e}"

    # 检查页面是否存在
    if '页面不存在' in res.text or '没有找到' in res.text:
        return f"错误: 未找到干员 '{operator_name}'"

    # 提取干员信息
    info = _extract_operator_info(soup)

    # 获取页面文本内容
    content = soup.find('div', {'id': 'mw-content-text'})
    if not content:
        return "错误: 无法获取页面内容"

    text = content.get_text(separator='\n')

    # 创建文档
    doc = Document()

    # 设置默认字体
    style = doc.styles['Normal']
    style.font.name = '微软雅黑'
    style.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    style.font.size = Pt(10.5)

    # 标题
    title = doc.add_heading(f'{operator_name} 干员档案', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 基本信息
    doc.add_heading('基本信息', level=1)

    # 基本信息表格
    table = doc.add_table(rows=8, cols=2)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    info_data = [
        ('代号', info['name'] or operator_name),
        ('性别', info['gender'] or '未知'),
        ('战斗经验', info['combat_experience'] or '未知'),
        ('出身地', info['birthplace'] or '未知'),
        ('生日', info['birthday'] or '未知'),
        ('种族', info['race'] or '未知'),
        ('身高', info['height'] or '未知'),
        ('矿石病感染情况', info['infection_status'] or '未知'),
    ]

    for i, (key, value) in enumerate(info_data):
        row = table.rows[i]
        row.cells[0].text = key
        row.cells[1].text = value
        _set_cell_shading(row.cells[0], 'E8E8E8')

    doc.add_paragraph()

    # 干员属性
    doc.add_heading('干员属性', level=1)

    # 从页面提取职业信息
    profession_match = re.search(r'职业\s*(\w+)', text)
    sub_profession_match = re.search(r'分支\s*(\w+)', text)

    table = doc.add_table(rows=7, cols=2)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    attr_data = [
        ('职业', profession_match.group(1) if profession_match else '未知'),
        ('分支', sub_profession_match.group(1) if sub_profession_match else '未知'),
        ('再部署时间', info['redeploy_time'] or '未知'),
        ('初始部署费用', info['deploy_cost'] or '未知'),
        ('阻挡数', info['block_count'] or '未知'),
        ('攻击间隔', info['attack_interval'] or '未知'),
        ('所属势力', info['faction'] or '未知'),
    ]

    for i, (key, value) in enumerate(attr_data):
        row = table.rows[i]
        row.cells[0].text = key
        row.cells[1].text = value
        _set_cell_shading(row.cells[0], 'E8E8E8')

    doc.add_paragraph()

    # 提取并添加天赋信息
    doc.add_heading('天赋', level=1)

    # 查找天赋部分
    talent_start = text.find('天赋')
    if talent_start >= 0:
        talent_text = text[talent_start:talent_start+2000]
        # 简化处理：提取天赋名称和描述
        talent_lines = talent_text.split('\n')
        current_talent = None
        for line in talent_lines[:30]:  # 限制行数
            line = line.strip()
            if not line:
                continue
            if '第一天赋' in line or '第二天赋' in line:
                current_talent = line
                doc.add_heading(line, level=2)
            elif current_talent and len(line) > 10:
                doc.add_paragraph(line)

    doc.add_paragraph()

    # 提取并添加技能信息
    doc.add_heading('技能', level=1)

    # 查找技能部分
    skill_start = text.find('技能')
    if skill_start >= 0:
        skill_text = text[skill_start:skill_start+3000]
        skill_lines = skill_text.split('\n')
        current_skill = None
        skill_count = 0
        for line in skill_lines[:50]:  # 限制行数
            line = line.strip()
            if not line:
                continue
            if '技能1' in line or '技能2' in line or '技能3' in line:
                current_skill = line
                skill_count += 1
                if skill_count <= 3:
                    doc.add_heading(line, level=2)
            elif current_skill and ('描述' in line or '攻击力' in line or '治疗' in line):
                if len(line) > 10:
                    doc.add_paragraph(line)

    doc.add_paragraph()

    # 保存文档
    if output_path:
        save_path = output_path
    else:
        save_path = f"{operator_name} 干员档案.docx"
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
    doc.save(save_path)

    # 返回完整路径
    full_path = os.path.abspath(save_path)
    return f"文档已成功生成：{full_path}"


# ══════════════════════════════════════════════════════════════════
# 文档编辑工具
# ══════════════════════════════════════════════════════════════════

@mcp.tool()
def edit_document(
    file_path: str,
    operation: str,
    old_text: str = "",
    new_text: str = "",
    text: str = "",
    heading: str = "",
    content: str = "",
    level: int = 1,
    position: int = -1,
    row: int = 0,
    col: int = 0,
    table_index: int = 0,
) -> str:
    """
    编辑已有的 DOCX 文档。

    参数:
        file_path:    DOCX 文件路径
        operation:    操作类型：
                      - read:          读取文档结构（段落和表格内容概览）
                      - replace_text:  查找替换文本
                      - add_paragraph: 在指定位置插入段落
                      - add_heading:   在指定位置插入标题
                      - add_section:   在指定位置插入标题+段落组合
                      - edit_table:    修改表格单元格内容
        old_text:     replace_text 用：要查找的文本
        new_text:     replace_text 用：替换后的文本 / edit_table 用：单元格新值
        text:         add_paragraph / add_heading 用：文本内容
        heading:      add_section 用：标题文本
        content:      add_section 用：段落内容（可用 \\n 分隔多段）
        level:        add_heading 用：标题级别（1-4，默认 1）
        position:     插入位置索引（默认 -1 即文档末尾，0 为文档开头）
        row:          edit_table 用：行索引（从 0 开始）
        col:          edit_table 用：列索引（从 0 开始）
        table_index:  edit_table 用：第几个表格（默认第 1 个，从 0 开始）
    """
    try:
        from docx import Document
        from docx.shared import Pt
        from docx.oxml.ns import qn
    except ImportError:
        return "错误: 缺少 python-docx 库，请运行 'pip install python-docx' 安装"

    abs_path = os.path.abspath(file_path)
    if not os.path.isfile(abs_path):
        return f"错误: 文件不存在 {abs_path}"

    try:
        doc = Document(abs_path)
    except Exception as e:
        return f"错误: 无法打开文档 {e}"

    # ── read: 读取文档结构 ──
    if operation == "read":
        lines = [f"文档: {abs_path}", ""]
        for i, para in enumerate(doc.paragraphs):
            style = para.style.name if para.style else ""
            prefix = f"[{i}] "
            if "Heading" in style:
                level_num = style.replace("Heading ", "")
                prefix += f"(H{level_num}) "
            text_content = para.text.strip()
            if text_content:
                lines.append(f"{prefix}{text_content[:120]}")
            else:
                lines.append(f"{prefix}(空行)")
        for ti, table in enumerate(doc.tables):
            lines.append(f"\n── 表格 {ti} ({len(table.rows)}行 x {len(table.columns)}列) ──")
            for ri, row in enumerate(table.rows):
                cells = [cell.text.strip()[:30] for cell in row.cells]
                lines.append(f"  [{ri}] | {' | '.join(cells)} |")
        return "\n".join(lines)

    # ── replace_text: 查找替换 ──
    if operation == "replace_text":
        if not old_text:
            return "错误: 请提供 old_text 参数"
        count = 0
        for para in doc.paragraphs:
            if old_text in para.text:
                for run in para.runs:
                    if old_text in run.text:
                        run.text = run.text.replace(old_text, new_text)
                        count += 1
        for table in doc.tables:
            for row_obj in table.rows:
                for cell in row_obj.cells:
                    for para in cell.paragraphs:
                        if old_text in para.text:
                            for run in para.runs:
                                if old_text in run.text:
                                    run.text = run.text.replace(old_text, new_text)
                                    count += 1
        doc.save(abs_path)
        return f"替换完成，共替换 {count} 处" if count > 0 else "未找到匹配文本"

    # ── add_paragraph: 插入段落 ──
    if operation == "add_paragraph":
        if not text:
            return "错误: 请提供 text 参数"
        body = doc.element.body
        new_para = doc.add_paragraph(text)
        if position >= 0 and position < len(body):
            body.insert(position, new_para._element)
        doc.save(abs_path)
        return f"已在位置 {position} 插入段落"

    # ── add_heading: 插入标题 ──
    if operation == "add_heading":
        if not text:
            return "错误: 请提供 text 参数"
        level = max(1, min(4, level))
        body = doc.element.body
        new_heading = doc.add_heading(text, level=level)
        if position >= 0 and position < len(body):
            body.insert(position, new_heading._element)
        doc.save(abs_path)
        return f"已在位置 {position} 插入 H{level} 标题"

    # ── add_section: 插入标题+段落组合 ──
    if operation == "add_section":
        if not heading and not content:
            return "错误: 请提供 heading 或 content 参数"
        body = doc.element.body
        insert_pos = position if position >= 0 else len(body)
        if heading:
            h = doc.add_heading(heading, level=level)
            body.insert(insert_pos, h._element)
            insert_pos += 1
        if content:
            for para_text in content.split("\n"):
                para_text = para_text.strip()
                if para_text:
                    p = doc.add_paragraph(para_text)
                    body.insert(insert_pos, p._element)
                    insert_pos += 1
        doc.save(abs_path)
        return f"已在位置 {position} 插入章节"

    # ── edit_table: 修改表格单元格 ──
    if operation == "edit_table":
        tables = doc.tables
        if table_index < 0 or table_index >= len(tables):
            return f"错误: 表格索引 {table_index} 超出范围（共 {len(tables)} 个表格）"
        table = tables[table_index]
        if row < 0 or row >= len(table.rows):
            return f"错误: 行索引 {row} 超出范围（共 {len(table.rows)} 行）"
        if col < 0 or col >= len(table.columns):
            return f"错误: 列索引 {col} 超出范围（共 {len(table.columns)} 列）"
        cell = table.rows[row].cells[col]
        old_val = cell.text.strip()
        cell.text = new_text
        doc.save(abs_path)
        return f"表格{table_index}[{row},{col}]: '{old_val}' -> '{new_text}'"

    return f"错误: 未知操作 '{operation}'，支持: read, replace_text, add_paragraph, add_heading, add_section, edit_table"


# ══════════════════════════════════════════════════════════════════
# Excel 表格工具
# ══════════════════════════════════════════════════════════════════

@mcp.tool()
def edit_excel(
    file_path: str,
    operation: str,
    sheet: str = "",
    cell: str = "",
    value: str = "",
    data: str = "",
    formula_str: str = "",
    bold: bool = False,
    font_color: str = "",
    bg_color: str = "",
    font_size: int = 0,
    align: str = "",
    border: bool = False,
    col_width: str = "",
    row_height: str = "",
    params: str = "",
) -> str:
    """
    创建和编辑 Excel (.xlsx) 表格。

    参数:
        file_path:    Excel 文件路径
        operation:    操作类型：
                      - create:            创建新文件（已有则覆盖）
                      - read:              读取工作表内容
                      - write:             写入数据（单格或批量）
                      - formula:           写入公式
                      - add_sheet:         添加新工作表
                      - format:            设置单元格格式
                      - merge:             合并单元格
                      - col_width:         设置列宽（如 "A:20,B:15"）
                      - row_height:        设置行高（如 "1:30,2:20"）
                      - chart:             添加图表
                      - conditional_format: 条件格式（色阶/数据条）
                      - data_validation:   数据验证（下拉列表）
                      - freeze_panes:      冻结窗格
                      - auto_filter:       自动筛选
                      - image:             插入图片
        sheet:        工作表名称（默认活动表）
        cell:         单元格引用，如 "A1" 或范围 "A1:C3"
        value:        单格写入的值
        data:         批量写入数据，JSON 二维数组，如 "[["姓名","分数"],["张三",90]]"
        formula_str:  公式（不含=号），如 "SUM(A1:A10)"
        bold:         是否加粗
        font_color:   字体颜色，如 "FF0000"
        bg_color:     背景色，如 "FFFF00"
        font_size:    字号
        align:        对齐方式：left / center / right
        border:       是否加边框
        col_width:    操作类型为 col_width 时：列宽设置，如 "A:20,B:15"
        row_height:   操作类型为 row_height 时：行高设置，如 "1:30,2:20"
        params:       高级操作的 JSON 参数，各操作可用字段：
                      chart:             {"type":"bar","title":"标题","data":"B1:D4","cats":"A2:A4","pos":"F2"}
                      conditional_format: {"range":"B2:D4","type":"color_scale","colors":["63BE7B","FFEB84","F8696B"]}
                      data_validation:   {"range":"B2:B100","list":"选项1,选项2,选项3"}
                      freeze_panes:      {"cell":"B2"}
                      auto_filter:       {"range":"A1:D10"}
                      image:             {"path":"logo.png","anchor":"A1","width":200,"height":100}
    """
    try:
        from openpyxl import Workbook, load_workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import range_boundaries
    except ImportError:
        return "错误: 缺少 openpyxl 库，请运行 'pip install openpyxl' 安装"

    abs_path = os.path.abspath(file_path)

    # ── helper ──
    def _get_sheet(wb):
        if sheet and sheet in wb.sheetnames:
            return wb[sheet]
        return wb.active

    def _apply_format(ws, cell_ref):
        """对单格或范围应用格式"""
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import range_boundaries

        if ":" in cell_ref:
            min_col, min_row, max_col, max_row = range_boundaries(cell_ref)
            targets = []
            for r in range(min_row, max_row + 1):
                for c in range(min_col, max_col + 1):
                    targets.append(ws.cell(row=r, column=c))
        else:
            targets = [ws[cell_ref]]

        for c in targets:
            if bold:
                c.font = Font(bold=True, size=font_size or None, color=font_color or None)
            elif font_size or font_color:
                c.font = Font(size=font_size or None, color=font_color or None)
            if bg_color:
                c.fill = PatternFill(start_color=bg_color, end_color=bg_color, fill_type="solid")
            if align:
                c.alignment = Alignment(horizontal=align)
            if border:
                thin = Side(style="thin")
                c.border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # ── create: 创建新文件 ──
    if operation == "create":
        wb = Workbook()
        ws = wb.active
        ws.title = sheet or "Sheet1"
        if data:
            try:
                rows = json.loads(data)
                for r, row_data in enumerate(rows, 1):
                    for c, val in enumerate(row_data, 1):
                        ws.cell(row=r, column=c, value=val)
            except json.JSONDecodeError:
                return "错误: data 不是有效的 JSON 二维数组"
        os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
        wb.save(abs_path)
        sheets_info = f"工作表: {ws.title}"
        if data:
            rows = json.loads(data)
            sheets_info += f"，{len(rows)} 行数据"
        return f"已创建 {abs_path}\n{sheets_info}"

    # ── 以下操作需要打开已有文件 ──
    if not os.path.isfile(abs_path):
        return f"错误: 文件不存在 {abs_path}"

    # ── read: 读取内容 ──
    if operation == "read":
        wb = load_workbook(abs_path, data_only=True)
        ws = _get_sheet(wb)
        lines = [f"文件: {abs_path}", f"工作表: {ws.title}", f"尺寸: {ws.max_row} 行 x {ws.max_column} 列", ""]

        if cell and ":" in cell:
            target = ws[cell]
            from openpyxl.utils import range_boundaries
            min_col, min_row, max_col, max_row = range_boundaries(cell)
            for r in range(min_row, max_row + 1):
                vals = []
                for c in range(min_col, max_col + 1):
                    v = ws.cell(row=r, column=c).value
                    vals.append(str(v) if v is not None else "")
                lines.append(f"  [{r}] | {' | '.join(vals)} |")
        else:
            for r in range(1, min(ws.max_row + 1, 101)):
                vals = []
                for c in range(1, min(ws.max_column + 1, 27)):
                    v = ws.cell(row=r, column=c).value
                    vals.append(str(v) if v is not None else "")
                line = f"  [{r}] | {' | '.join(vals)} |"
                lines.append(line)
            if ws.max_row > 100:
                lines.append(f"  ... 共 {ws.max_row} 行，仅显示前 100 行")
        return "\n".join(lines)

    # ── write: 写入数据 ──
    if operation == "write":
        wb = load_workbook(abs_path)
        ws = _get_sheet(wb)
        count = 0
        if data:
            try:
                rows_data = json.loads(data)
            except json.JSONDecodeError:
                return "错误: data 不是有效的 JSON 二维数组"
            if cell:
                from openpyxl.utils.cell import coordinate_to_tuple
                start_row, start_col = coordinate_to_tuple(cell)
            else:
                start_row, start_col = 1, 1
            for r, row_data in enumerate(rows_data):
                for c, val in enumerate(row_data):
                    ws.cell(row=start_row + r, column=start_col + c, value=val)
                    count += 1
        elif cell and value != "":
            if ":" in cell:
                from openpyxl.utils import range_boundaries
                min_col, min_row, max_col, max_row = range_boundaries(cell)
                for r in range(min_row, max_row + 1):
                    for c in range(min_col, max_col + 1):
                        ws.cell(row=r, column=c, value=value)
                        count += 1
            else:
                ws[cell] = value
                count = 1
        else:
            return "错误: 请提供 cell+value 或 data 参数"
        wb.save(abs_path)
        return f"已写入 {count} 个单元格"

    # ── formula: 写入公式 ──
    if operation == "formula":
        if not cell or not formula_str:
            return "错误: 请提供 cell 和 formula_str 参数"
        wb = load_workbook(abs_path)
        ws = _get_sheet(wb)
        ws[cell] = f"={formula_str}"
        wb.save(abs_path)
        return f"已写入公式: {cell} = {formula_str}"

    # ── add_sheet: 添加工作表 ──
    if operation == "add_sheet":
        if not sheet:
            return "错误: 请提供 sheet 参数（新工作表名称）"
        wb = load_workbook(abs_path)
        if sheet in wb.sheetnames:
            return f"错误: 工作表 '{sheet}' 已存在"
        wb.create_sheet(title=sheet)
        wb.save(abs_path)
        return f"已添加工作表 '{sheet}'，当前工作表: {', '.join(wb.sheetnames)}"

    # ── format: 设置格式 ──
    if operation == "format":
        if not cell:
            return "错误: 请提供 cell 参数"
        wb = load_workbook(abs_path)
        ws = _get_sheet(wb)
        _apply_format(ws, cell)
        wb.save(abs_path)
        return f"已设置 {cell} 的格式"

    # ── merge: 合并单元格 ──
    if operation == "merge":
        if not cell or ":" not in cell:
            return "错误: 请提供 cell 参数（范围如 A1:C3）"
        wb = load_workbook(abs_path)
        ws = _get_sheet(wb)
        ws.merge_cells(cell)
        wb.save(abs_path)
        return f"已合并 {cell}"

    # ── col_width: 设置列宽 ──
    if operation == "col_width":
        if not col_width:
            return "错误: 请提供 col_width 参数（如 'A:20,B:15'）"
        wb = load_workbook(abs_path)
        ws = _get_sheet(wb)
        for item in col_width.split(","):
            item = item.strip()
            if ":" in item:
                col_letter, width = item.split(":", 1)
                ws.column_dimensions[col_letter.strip()].width = float(width.strip())
        wb.save(abs_path)
        return f"已设置列宽: {col_width}"

    # ── row_height: 设置行高 ──
    if operation == "row_height":
        if not row_height:
            return "错误: 请提供 row_height 参数（如 '1:30,2:20'）"
        wb = load_workbook(abs_path)
        ws = _get_sheet(wb)
        for item in row_height.split(","):
            item = item.strip()
            if ":" in item:
                row_num, height = item.split(":", 1)
                ws.row_dimensions[int(row_num)].height = float(height.strip())
        wb.save(abs_path)
        return f"已设置行高: {row_height}"

    # ── 解析 params JSON ──
    p = {}
    if params:
        try:
            p = json.loads(params)
        except json.JSONDecodeError:
            return "错误: params 不是有效的 JSON"

    # ── chart: 添加图表 ──
    if operation == "chart":
        from openpyxl.chart import BarChart, LineChart, PieChart, AreaChart, ScatterChart, Reference
        chart_map = {
            "bar": BarChart, "line": LineChart, "pie": PieChart,
            "area": AreaChart, "scatter": ScatterChart,
        }
        ctype = p.get("type", "bar")
        if ctype not in chart_map:
            return f"错误: 不支持的图表类型 '{ctype}'，支持: {', '.join(chart_map)}"
        if not cell:
            return "错误: 请提供 cell 参数指定数据范围（如 A1:D4）"
        wb = load_workbook(abs_path)
        ws = _get_sheet(wb)
        chart = chart_map[ctype]()
        chart.title = p.get("title", "")
        chart.style = int(p.get("style", 10))
        # 数据系列
        from openpyxl.utils import range_boundaries as rb
        d_min_col, d_min_row, d_max_col, d_max_row = rb(cell)
        cats_ref = p.get("cats", "")
        if cats_ref:
            cats = Reference(ws, *rb(cats_ref)[0:2], *rb(cats_ref)[2:4])
        else:
            cats = Reference(ws, min_col=d_min_col, min_row=d_min_row + 1, max_row=d_max_row)
        for c in range(d_min_col + (1 if not cats_ref else 0), d_max_col + 1):
            vals = Reference(ws, min_col=c, min_row=d_min_row, max_row=d_max_row)
            chart.add_data(vals, titles_from_data=True)
        chart.set_categories(cats)
        # 尺寸
        chart.width = float(p.get("width", 15))
        chart.height = float(p.get("height", 10))
        # 位置
        pos = p.get("pos", "F2")
        ws.add_chart(chart, pos)
        wb.save(abs_path)
        return f"已添加 {ctype} 图表，数据范围 {cell}，位置 {pos}"

    # ── conditional_format: 条件格式 ──
    if operation == "conditional_format":
        from openpyxl.formatting.rule import ColorScaleRule, DataBarRule
        from openpyxl.utils import range_boundaries as rb
        if not cell:
            return "错误: 请提供 cell 参数指定范围（如 B2:D10）"
        wb = load_workbook(abs_path)
        ws = _get_sheet(wb)
        cf_type = p.get("type", "color_scale")
        colors = p.get("colors", ["63BE7B", "FFEB84", "F8696B"])
        if cf_type == "color_scale":
            rule = ColorScaleRule(
                start_type="min", start_color=colors[0],
                mid_type="percentile", mid_value=50, mid_color=colors[1] if len(colors) > 1 else "FFFFFF",
                end_type="max", end_color=colors[2] if len(colors) > 2 else "F8696B",
            )
            ws.conditional_formatting.add(cell, rule)
        elif cf_type == "data_bar":
            from openpyxl.formatting.rule import DataBarRule
            rule = DataBarRule(start_type="min", end_type="max", color=colors[0])
            ws.conditional_formatting.add(cell, rule)
        else:
            return f"错误: 不支持的条件格式类型 '{cf_type}'，支持: color_scale, data_bar"
        wb.save(abs_path)
        return f"已对 {cell} 添加 {cf_type} 条件格式"

    # ── data_validation: 数据验证 ──
    if operation == "data_validation":
        from openpyxl.worksheet.datavalidation import DataValidation
        if not cell:
            return "错误: 请提供 cell 参数指定范围（如 B2:B100）"
        list_str = p.get("list", "")
        if not list_str:
            return "错误: params 中请提供 list 字段（逗号分隔的选项）"
        wb = load_workbook(abs_path)
        ws = _get_sheet(wb)
        dv = DataValidation(type="list", formula1=f'"{list_str}"', allow_blank=True)
        dv.error = "请从列表中选择"
        dv.errorTitle = "无效输入"
        ws.add_data_validation(dv)
        dv.add(cell)
        wb.save(abs_path)
        return f"已对 {cell} 添加下拉列表: {list_str}"

    # ── freeze_panes: 冻结窗格 ──
    if operation == "freeze_panes":
        freeze_cell = p.get("cell", cell or "A2")
        wb = load_workbook(abs_path)
        ws = _get_sheet(wb)
        ws.freeze_panes = freeze_cell
        wb.save(abs_path)
        return f"已冻结窗格: {freeze_cell}"

    # ── auto_filter: 自动筛选 ──
    if operation == "auto_filter":
        filter_range = cell or p.get("range", "")
        if not filter_range:
            return "错误: 请提供 cell 参数指定筛选范围（如 A1:D10）"
        wb = load_workbook(abs_path)
        ws = _get_sheet(wb)
        ws.auto_filter.ref = filter_range
        wb.save(abs_path)
        return f"已对 {filter_range} 启用自动筛选"

    # ── image: 插入图片 ──
    if operation == "image":
        from openpyxl.drawing.image import Image as XlImage
        img_path = p.get("path", "")
        if not img_path:
            return "错误: params 中请提供 path 字段（图片路径）"
        img_abs = os.path.abspath(img_path)
        if not os.path.isfile(img_abs):
            return f"错误: 图片不存在 {img_abs}"
        wb = load_workbook(abs_path)
        ws = _get_sheet(wb)
        img = XlImage(img_abs)
        if "width" in p:
            img.width = int(p["width"])
        if "height" in p:
            img.height = int(p["height"])
        anchor = p.get("anchor", cell or "A1")
        ws.add_image(img, anchor)
        wb.save(abs_path)
        return f"已插入图片 {img_path}，锚点 {anchor}"

    return (
        f"错误: 未知操作 '{operation}'，支持: "
        "create, read, write, formula, add_sheet, format, merge, col_width, row_height, "
        "chart, conditional_format, data_validation, freeze_panes, auto_filter, image"
    )


# ══════════════════════════════════════════════════════════════════
# PDF 读写工具
# ══════════════════════════════════════════════════════════════════

@mcp.tool()
def edit_pdf(
    file_path: str,
    operation: str,
    output_path: str = "",
    pages: str = "",
    content: str = "",
    title: str = "",
    author: str = "",
    font_size: int = 12,
    page_size: str = "A4",
    margin: int = 72,
    params: str = "",
) -> str:
    """
    读取和生成 PDF 文件。

    参数:
        file_path:    PDF 文件路径（read/info/merge/extract 用）
        operation:    操作类型：
                      - read:    读取 PDF 文本内容
                      - info:    获取 PDF 元信息（页数、标题、作者等）
                      - create:  创建新 PDF（从文本生成）
                      - merge:   合并多个 PDF
                      - extract: 提取指定页面到新文件
                      - to_word: PDF 转 Word (.docx)
        output_path:  输出文件路径（create/merge/extract 必填）
        pages:        页码范围，如 "1,3,5-8"（read/extract 用，默认全部）
        content:      文本内容（create 用，用 \\n 分段）
        title:        文档标题（create 用）
        author:       文档作者（create 用）
        font_size:    字号（create 用，默认 12）
        page_size:    页面大小（create 用：A4/Letter/A5，默认 A4）
        margin:       页边距点数（create 用，默认 72，即 1 英寸）
        params:       JSON 参数，高级选项：
                      merge:   {"files":["a.pdf","b.pdf","c.pdf"]}
                      create:  {"line_spacing":1.5,"header":"页眉","footer":"页脚"}
    """
    abs_path = os.path.abspath(file_path)

    # ── helper: 解析页码范围 ──
    def _parse_pages(pages_str: str, max_page: int) -> list:
        if not pages_str:
            return list(range(max_page))
        result = []
        for part in pages_str.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-", 1)
                result.extend(range(int(start) - 1, int(end)))
            else:
                result.append(int(part) - 1)
        return [p for p in result if 0 <= p < max_page]

    # ── read: 读取文本 ──
    if operation == "read":
        try:
            from pypdf import PdfReader
        except ImportError:
            return "错误: 缺少 pypdf 库，请运行 'pip install pypdf' 安装"
        if not os.path.isfile(abs_path):
            return f"错误: 文件不存在 {abs_path}"
        reader = PdfReader(abs_path)
        page_list = _parse_pages(pages, len(reader.pages))
        lines = [f"文件: {abs_path}", f"总页数: {len(reader.pages)}", ""]
        for i in page_list:
            text = reader.pages[i].extract_text() or ""
            lines.append(f"── 第 {i + 1} 页 ──")
            lines.append(text.strip() if text.strip() else "(无可提取文本)")
            lines.append("")
        return "\n".join(lines)

    # ── info: 获取元信息 ──
    if operation == "info":
        try:
            from pypdf import PdfReader
        except ImportError:
            return "错误: 缺少 pypdf 库，请运行 'pip install pypdf' 安装"
        if not os.path.isfile(abs_path):
            return f"错误: 文件不存在 {abs_path}"
        reader = PdfReader(abs_path)
        meta = reader.metadata
        lines = [
            f"文件: {abs_path}",
            f"页数: {len(reader.pages)}",
            f"标题: {meta.title if meta and meta.title else '无'}",
            f"作者: {meta.author if meta and meta.author else '无'}",
            f"主题: {meta.subject if meta and meta.subject else '无'}",
            f"创建者: {meta.creator if meta and meta.creator else '无'}",
        ]
        if reader.pages:
            page = reader.pages[0]
            box = page.mediabox
            lines.append(f"页面尺寸: {float(box.width):.0f} x {float(box.height):.0f} 点")
        lines.append(f"加密: {'是' if reader.is_encrypted else '否'}")
        return "\n".join(lines)

    # ── create: 创建 PDF ──
    if operation == "create":
        try:
            from reportlab.lib.pagesizes import A4, LETTER, A5
            from reportlab.lib.units import mm
            from reportlab.pdfgen import canvas
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
        except ImportError:
            return "错误: 缺少 reportlab 库，请运行 'pip install reportlab' 安装"
        if not content:
            return "错误: 请提供 content 参数"
        if not output_path:
            return "错误: 请提供 output_path 参数"

        size_map = {"A4": A4, "Letter": LETTER, "A5": A5}
        pagesize = size_map.get(page_size, A4)

        # 解析 params
        p = {}
        if params:
            try:
                p = json.loads(params)
            except json.JSONDecodeError:
                return "错误: params 不是有效的 JSON"

        out_abs = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(out_abs) or ".", exist_ok=True)

        # 注册中文字体（尝试常见路径）
        chinese_font = None
        font_paths = [
            "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
            "C:/Windows/Fonts/simsun.ttc",      # 宋体
            "C:/Windows/Fonts/simhei.ttf",      # 黑体
            "/System/Library/Fonts/PingFang.ttc",  # macOS
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",  # Linux
        ]
        for fp in font_paths:
            if os.path.isfile(fp):
                try:
                    pdfmetrics.registerFont(TTFont("ChineseFont", fp))
                    chinese_font = "ChineseFont"
                    break
                except Exception:
                    continue

        font_name = chinese_font or "Helvetica"

        doc = SimpleDocTemplate(
            out_abs, pagesize=pagesize,
            leftMargin=margin, rightMargin=margin,
            topMargin=margin, bottomMargin=margin,
            title=title or "",
            author=author or "",
        )

        style = ParagraphStyle(
            "Body",
            fontName=font_name,
            fontSize=font_size,
            leading=font_size * float(p.get("line_spacing", 1.5)),
        )
        title_style = ParagraphStyle(
            "Title",
            fontName=font_name,
            fontSize=font_size + 6,
            leading=(font_size + 6) * 1.5,
            alignment=1,  # center
            spaceAfter=20,
        )

        story = []
        if title:
            story.append(Paragraph(title, title_style))
        for para in content.split("\n"):
            para = para.strip()
            if para:
                story.append(Paragraph(para, style))
                story.append(Spacer(1, font_size * 0.5))

        doc.build(story)
        return f"已创建 PDF: {out_abs}（{len(content.split(chr(10)))} 段）"

    # ── merge: 合并 PDF ──
    if operation == "merge":
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError:
            return "错误: 缺少 pypdf 库，请运行 'pip install pypdf' 安装"
        if not output_path:
            return "错误: 请提供 output_path 参数"

        p = {}
        if params:
            try:
                p = json.loads(params)
            except json.JSONDecodeError:
                return "错误: params 不是有效的 JSON"

        files = p.get("files", [])
        if not files and file_path:
            files = [file_path]
        if not files:
            return "错误: 请在 params.files 中提供要合并的 PDF 文件列表"

        writer = PdfWriter()
        total_pages = 0
        for f in files:
            f_abs = os.path.abspath(f)
            if not os.path.isfile(f_abs):
                return f"错误: 文件不存在 {f_abs}"
            reader = PdfReader(f_abs)
            for page in reader.pages:
                writer.add_page(page)
                total_pages += 1

        out_abs = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(out_abs) or ".", exist_ok=True)
        with open(out_abs, "wb") as f:
            writer.write(f)
        return f"已合并 {len(files)} 个 PDF（共 {total_pages} 页）-> {out_abs}"

    # ── extract: 提取页面 ──
    if operation == "extract":
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError:
            return "错误: 缺少 pypdf 库，请运行 'pip install pypdf' 安装"
        if not os.path.isfile(abs_path):
            return f"错误: 文件不存在 {abs_path}"
        if not output_path:
            return "错误: 请提供 output_path 参数"
        reader = PdfReader(abs_path)
        page_list = _parse_pages(pages, len(reader.pages))
        if not page_list:
            return "错误: 未指定有效页码"
        writer = PdfWriter()
        for i in page_list:
            writer.add_page(reader.pages[i])
        out_abs = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(out_abs) or ".", exist_ok=True)
        with open(out_abs, "wb") as f:
            writer.write(f)
        return f"已提取 {len(page_list)} 页 -> {out_abs}"

    # ── to_word: PDF 转 Word ──
    if operation == "to_word":
        try:
            from pdf2docx import Converter
        except ImportError:
            return "错误: 缺少 pdf2docx 库，请运行 'pip install pdf2docx' 安装"
        if not os.path.isfile(abs_path):
            return f"错误: 文件不存在 {abs_path}"
        out_abs = os.path.abspath(output_path) if output_path else abs_path.rsplit(".", 1)[0] + ".docx"
        os.makedirs(os.path.dirname(out_abs) or ".", exist_ok=True)
        # 解析页码范围
        p = {}
        if params:
            try:
                p = json.loads(params)
            except json.JSONDecodeError:
                return "错误: params 不是有效的 JSON"
        cv = Converter(abs_path)
        start_page = p.get("start", 0)
        end_page = p.get("end", None)
        if pages:
            page_list = _parse_pages(pages, len(cv.pages))
            if page_list:
                start_page = page_list[0]
                end_page = page_list[-1] + 1
        cv.convert(out_abs, start=start_page, end=end_page)
        cv.close()
        return f"已转换: {abs_path} -> {out_abs}"

    return (
        f"错误: 未知操作 '{operation}'，支持: read, info, create, merge, extract, to_word"
    )


# ══════════════════════════════════════════════════════════════════
# 己方干员查询工具
# ══════════════════════════════════════════════════════════════════

@mcp.tool()
def query_operator(name: str, max_results: int = 5) -> str:
    """
    查询明日方舟己方干员的详细数据，包括属性、天赋、技能。

    参数:
        name:         干员名称或 ID（支持模糊搜索，如 "凯尔希"、"amiya"、"Mon3tr"）
        max_results:  最大返回条数（默认 5）
    """
    _LOCAL_BASE = Path(__file__).parent / "ArknightsGameData"
    _REMOTE_BASE = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN"

    def _data_path(rel: str) -> str:
        local = _LOCAL_BASE / rel
        if local.is_file():
            return str(local)
        return f"{_REMOTE_BASE}/{rel}"

    try:
        _chars = _load_json(_data_path("gamedata/excel/character_table.json"))
        _skills = _load_json(_data_path("gamedata/excel/skill_table.json"))
    except Exception as e:
        return f"错误: 无法加载游戏数据 {e}"

    _PROF = {"PIONEER": "先锋", "WARRIOR": "近卫", "TANK": "重装", "SNIPER": "狙击",
             "CASTER": "术师", "MEDIC": "医疗", "SUPPORTER": "辅助", "SPECIALIST": "特种"}
    _POS = {"MELEE": "近战", "RANGED": "远程"}
    _RARITY = {"TIER_1": "★", "TIER_2": "★★", "TIER_3": "★★★",
               "TIER_4": "★★★★", "TIER_5": "★★★★★", "TIER_6": "★★★★★★"}

    def _clean(s):
        return re.sub(r"<[^>]+>", "", str(s)) if s else ""

    query = name.lower().strip()
    matches = [
        (cid, d) for cid, d in _chars.items()
        if query in d.get("name", "").lower()
        or query in cid.lower()
        or query in d.get("appellation", "").lower()
    ]
    if not matches:
        return f"未找到干员 \"{name}\""

    results = []
    for cid, d in matches[:max_results]:
        lines = [f"[{cid}]"]
        lines.append(f"  名称: {d.get('name')} ({d.get('appellation', '')})")
        lines.append(f"  稀有度: {_RARITY.get(d.get('rarity'), d.get('rarity'))}")
        lines.append(f"  职业: {_PROF.get(d.get('profession'), d.get('profession'))}")
        lines.append(f"  分支: {d.get('subProfessionId')}")
        lines.append(f"  位置: {_POS.get(d.get('position'), d.get('position'))}")
        desc = _clean(d.get("description"))
        if desc:
            lines.append(f"  描述: {desc[:120]}")
        nation = d.get("nationId", "")
        if nation:
            lines.append(f"  势力: {nation}")

        # 满级属性
        phases = d.get("phases", [])
        if phases:
            attrs_list = phases[-1].get("attributesKeyFrames", [])
            if attrs_list:
                a = attrs_list[-1].get("data", {})
                lines.append("  满级属性:")
                for k, label in [("maxHp", "生命"), ("atk", "攻击"), ("def", "防御"),
                                 ("magicResistance", "法抗"), ("cost", "费用"),
                                 ("blockCnt", "阻挡"), ("baseAttackTime", "攻击间隔")]:
                    v = a.get(k)
                    if v is not None:
                        lines.append(f"    {label}: {v}")

        # 天赋
        talents = d.get("talents", [])
        if talents:
            lines.append("  天赋:")
            for t in talents:
                cands = t.get("candidates", [])
                if cands:
                    last_t = cands[-1]
                    t_name = last_t.get("name", "?")
                    t_desc = _clean(last_t.get("description", ""))[:100]
                    lines.append(f"    - {t_name}: {t_desc}")

        # 技能
        char_skills = d.get("skills", [])
        if char_skills:
            lines.append("  技能:")
            for sk in char_skills:
                sk_id = sk.get("skillId", "")
                sk_data = _skills.get(sk_id, {})
                levels = sk_data.get("levels", [])
                sk_name = levels[-1].get("name", sk_id) if levels else sk_id
                sk_desc = _clean(levels[-1].get("description", ""))[:100] if levels else ""
                lines.append(f"    - {sk_name}: {sk_desc}")

        results.append("\n".join(lines))
    return "\n\n".join(results)


# ══════════════════════════════════════════════════════════════════
# 剧情查询工具
# ══════════════════════════════════════════════════════════════════

def _parse_story_script(text: str, show_stage_direction: bool = False) -> str:
    """解析剧情脚本，提取对话和旁白"""
    lines = text.split("\n")
    result = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 对话: [name="角色"] 内容
        m = re.match(r'\[name="([^"]+)"\]\s*(.*)', line)
        if m:
            char, dialogue = m.group(1), m.group(2).strip()
            if dialogue:
                result.append(f"{char}: {dialogue}")
            continue
        # 旁白/描述行（不以 [ 开头的纯文本）
        if not line.startswith("["):
            result.append(line)
            continue
        # 可选：显示舞台指令
        if show_stage_direction:
            tag = re.match(r"\[(\w+)", line)
            if tag:
                result.append(f"[{tag.group(1)}]")
    return "\n".join(result)


@mcp.tool()
def query_story(
    query: str = "",
    story_id: str = "",
    operation: str = "search",
    max_results: int = 20,
    show_direction: bool = False,
) -> str:
    """
    查询和获取明日方舟剧情文本。

    参数:
        query:           搜索关键词（章节名、活动名、关卡代号，如 "第七章"、"骑兵与猎人"、"GT-1"）
        story_id:        剧情 ID（read 操作用，如 "obt/main/level_main_01-07_beg"）
        operation:       操作类型：
                         - search: 搜索剧情（默认）
                         - read:   读取指定剧情文本
                         - list:   列出某章节/活动的所有剧情
        max_results:     search 最大返回条数（默认 20）
        show_direction:  是否显示舞台指令（默认 false，仅显示对话）
    """
    _LOCAL_STORY = Path(__file__).parent / "ArknightsGameData"
    _REMOTE_BASE = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN"

    def _data_path(rel: str) -> str:
        local = _LOCAL_STORY / rel
        if local.is_file():
            return str(local)
        return f"{_REMOTE_BASE}/{rel}"

    # ── 加载剧情索引 ──
    try:
        review = _load_json(_data_path("gamedata/excel/story_review_table.json"))
        story_table = _load_json(_data_path("gamedata/excel/story_table.json"))
    except Exception as e:
        return f"错误: 无法加载剧情索引 {e}"

    # story_review_table 的 storyId 格式: main_15_level_main_15-15_beg
    # story_table 的 key 格式:        obt/main/level_main_15-15_beg
    # 实际文件路径:                    gamedata/story/obt/main/level_main_15-15_beg.txt
    def _resolve_story_id(sid: str) -> str:
        """将 review_table 的 storyId 转为实际文件路径"""
        # 先直接查 story_table
        if sid in story_table:
            return sid
        # 尝试转换: main_15_level_main_15-15_beg -> obt/main/level_main_15-15_beg
        # 匹配模式: main_{chapter}_level_{rest}
        m = re.match(r"main_(\d+)_level_(.+)", sid)
        if m:
            candidate = f"obt/main/level_{m.group(2)}"
            if candidate in story_table:
                return candidate
        # 活动剧情: act3d0_level_act3d0_01_beg -> obt/activity/level_act3d0_01_beg
        m = re.match(r"act\w+_level_(.+)", sid)
        if m:
            candidate = f"obt/activity/level_{m.group(1)}"
            if candidate in story_table:
                return candidate
        return sid

    # ── search: 搜索剧情 ──
    if operation == "search":
        if not query:
            return "错误: 请提供 query 参数"
        q = query.lower().strip()
        matches = []
        for key, entry in review.items():
            name = entry.get("name", "")
            entry_type = entry.get("entryType", "")
            # 匹配活动名
            if q in name.lower() or q in key.lower():
                for iu in entry.get("infoUnlockDatas", []):
                    matches.append({
                        "activity": name,
                        "storyId": iu.get("storyId", ""),
                        "storyCode": iu.get("storyCode", ""),
                        "storyName": iu.get("storyName", ""),
                        "avgTag": iu.get("avgTag", ""),
                        "entryType": entry_type,
                    })
            else:
                # 匹配关卡代号或剧情名
                for iu in entry.get("infoUnlockDatas", []):
                    code = iu.get("storyCode") or ""
                    sname = iu.get("storyName") or ""
                    sid = iu.get("storyId") or ""
                    if q in code.lower() or q in sname.lower() or q in sid.lower():
                        matches.append({
                            "activity": name,
                            "storyId": sid,
                            "storyCode": code,
                            "storyName": sname,
                            "avgTag": iu.get("avgTag", ""),
                            "entryType": entry_type,
                        })
        if not matches:
            return f"未找到匹配 \"{query}\" 的剧情"
        lines = [f"找到 {len(matches)} 条匹配（显示前 {min(max_results, len(matches))} 条）:", ""]
        for m in matches[:max_results]:
            tag = f"[{m['avgTag']}]" if m["avgTag"] else ""
            code = m["storyCode"] or "—"
            resolved = _resolve_story_id(m["storyId"])
            lines.append(f"  {m['activity']} / {code} {m['storyName']} {tag}")
            lines.append(f"    storyId: {m['storyId']}")
            lines.append("")
        if len(matches) > max_results:
            lines.append(f"... 共 {len(matches)} 条，仅显示前 {max_results} 条")
        return "\n".join(lines)

    # ── list: 列出章节/活动剧情 ──
    if operation == "list":
        if not query:
            return "错误: 请提供 query 参数（章节名或活动名）"
        q = query.lower().strip()
        found = None
        for key, entry in review.items():
            name = entry.get("name", "")
            if q in name.lower() or q in key.lower():
                found = (key, entry)
                break
        if not found:
            return f"未找到匹配 \"{query}\" 的章节/活动"
        key, entry = found
        lines = [
            f"活动: {entry.get('name', key)}",
            f"类型: {entry.get('entryType', '?')} / {entry.get('actType', '?')}",
            f"剧情数: {len(entry.get('infoUnlockDatas', []))}",
            "",
        ]
        for iu in entry.get("infoUnlockDatas", []):
            tag = f"[{iu.get('avgTag', '')}]" if iu.get("avgTag") else ""
            code = iu.get("storyCode", "—")
            lines.append(f"  {code} {iu.get('storyName', '?')} {tag}")
            lines.append(f"    storyId: {iu.get('storyId', '')}")
        return "\n".join(lines)

    # ── read: 读取剧情文本 ──
    if operation == "read":
        if not story_id:
            return "错误: 请提供 story_id 参数"
        resolved = _resolve_story_id(story_id)
        url = _data_path(f"gamedata/story/{resolved}.txt")
        try:
            if url.startswith(("http://", "https://")):
                r = requests.get(url, timeout=15)
                if r.status_code != 200:
                    return f"错误: 无法获取剧情文件 (HTTP {r.status_code})"
                text = r.text
            else:
                with open(url, "r", encoding="utf-8") as f:
                    text = f.read()
        except Exception as e:
            return f"错误: 无法读取剧情 {e}"
        parsed = _parse_story_script(text, show_direction)
        if not parsed:
            return "该剧情文件无可提取的对话内容"
        return f"[{story_id}]\n\n{parsed}"

    return f"错误: 未知操作 '{operation}'，支持: search, read, list"


# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
