#!/usr/bin/env bash
# Mon3tr-MCP —— 查看状态（进程 + 端口可达性 + 日志尾部）
#
# 用法：
#   ./status.sh                 # 默认看 8000
#   MCP_PORT=8123 ./status.sh   # 看别的端口
set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE"

PID_FILE="logs/mon3tr-mcp.pid"
LOG_FILE="logs/mon3tr-console.log"
PORT="${MCP_PORT:-8000}"
PATTERN="$BASE/Mon3tr-MCP[.]py"   # 只认本项目的实例，理由见 stop.sh 顶部注释

pid=""
if [ -f "$PID_FILE" ]; then
    p="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [ -n "$p" ] && kill -0 "$p" 2>/dev/null; then pid="$p"; fi
fi
if [ -z "$pid" ] && command -v pgrep >/dev/null 2>&1; then
    # 同样只认解释器进程（理由见 stop.sh 顶部注释）
    for p in $(pgrep -f "$PATTERN" 2>/dev/null || true); do
        args="$(ps -o args= -p "$p" 2>/dev/null || true)"
        case "$args" in
            *python*) pid="$p"; break ;;
        esac
    done
fi

echo "项目：$BASE"
if [ -z "$pid" ]; then
    echo "进程：未运行"
else
    echo "进程：运行中 (PID $pid)"
    args="$(ps -o args= -p "$pid" 2>/dev/null || true)"
    [ -n "$args" ] && echo "命令：$args"
    etime="$(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ' || true)"
    [ -n "$etime" ] && echo "已运行：$etime"
fi

# 端口探测用 bash 内建 /dev/tcp（不依赖 nc/ss/lsof，Linux/macOS/Termux 都支持）
if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; then
    exec 3>&- 2>/dev/null || true
    echo "端口：127.0.0.1:$PORT 可达 —— MCP 端点 http://127.0.0.1:$PORT/mcp"
else
    echo "端口：127.0.0.1:$PORT 不可达"
fi

if [ -f "$LOG_FILE" ]; then
    echo "日志：$LOG_FILE（最后 5 行）"
    tail -n 5 "$LOG_FILE" | sed 's/^/  /'
else
    echo "日志：$LOG_FILE（还没有生成）"
fi
