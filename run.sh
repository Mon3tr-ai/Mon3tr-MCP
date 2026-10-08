#!/usr/bin/env bash
# Mon3tr-MCP —— 前台运行（供 systemd / launchd / 容器 / 手动调试使用）
#
# 用法：
#   ./run.sh                              # 自动探测解释器（python3 优先，回退 python）
#   PYTHON=/usr/bin/python3.11 ./run.sh   # 指定解释器
#
# 说明：本脚本只负责「前台」把服务跑起来，不写 pid、不重定向日志；
#       后台启动请用 start.sh，停止用 stop.sh，查状态用 status.sh。
#
# 注意：脚本用 **绝对路径** 调用 Mon3tr-MCP.py（cwd 仍是项目目录）。
#       这样进程命令行里带完整项目路径，stop.sh / status.sh 才能精确认领
#       「本项目的实例」，不去碰别的目录里同名脚本跑起来的 Mon3tr-MCP。
set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE"   # Mon3tr-MCP.py 依赖相对路径读取 ArknightsGameData 等资源

PY="${PYTHON:-}"
if [ -z "$PY" ]; then
    if command -v python3 >/dev/null 2>&1; then
        PY=python3
    elif command -v python >/dev/null 2>&1; then
        PY=python
    else
        echo "Mon3tr-MCP: 找不到 python3/python，请用 PYTHON=/path/to/python 明确指定" >&2
        exit 1
    fi
fi

exec "$PY" -u "$BASE/Mon3tr-MCP.py"
