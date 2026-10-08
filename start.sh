#!/usr/bin/env bash
# Mon3tr-MCP —— 后台启动（nohup + pid 文件）
#
# 用法：
#   ./start.sh                              # 已在运行则直接返回，不会起第二个实例
#   PYTHON=/usr/bin/python3.11 ./start.sh   # 指定解释器
#   MCP_PORT=8123 ./start.sh                # 只影响下面的提示信息（端口由 Mon3tr-MCP.py 决定）
#
# 日志：logs/mon3tr-console.log    pid：logs/mon3tr-mcp.pid
set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE"

LOG_DIR="logs"
LOG_FILE="$LOG_DIR/mon3tr-console.log"
PID_FILE="$LOG_DIR/mon3tr-mcp.pid"
PORT="${MCP_PORT:-8000}"
mkdir -p "$LOG_DIR"

# 已有实例在跑就不重复起（顺带清理过期 pid 文件）
if [ -f "$PID_FILE" ]; then
    old="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [ -n "$old" ] && kill -0 "$old" 2>/dev/null; then
        echo "Mon3tr-MCP 已在运行 (PID $old)，未重复启动"
        exit 0
    fi
    rm -f "$PID_FILE"
fi

# 用 bash 显式执行 run.sh：不依赖文件的可执行位（从 Windows 传过去时容易丢）
nohup bash ./run.sh >> "$LOG_FILE" 2>&1 &
pid=$!
echo "$pid" > "$PID_FILE"

# 等一下确认没立刻退出（依赖缺失、端口被占等都会立刻死）
sleep 1
if kill -0 "$pid" 2>/dev/null; then
    echo "Mon3tr-MCP 已启动 (PID $pid)"
    echo "  日志: $LOG_FILE"
    echo "  端点: http://127.0.0.1:$PORT/mcp"
else
    echo "Mon3tr-MCP 启动失败，请看日志尾部：" >&2
    tail -n 20 "$LOG_FILE" >&2 || true
    rm -f "$PID_FILE"
    exit 1
fi
