#!/usr/bin/env bash
# Mon3tr-MCP —— 停止（先 SIGTERM 优雅退出，10 秒后仍在则 SIGKILL）
#
# 用法：./stop.sh
#
# 认领规则（从严到宽）：
#   1. 优先信 logs/mon3tr-mcp.pid（start.sh 写的，指向本项目实例）
#   2. pid 文件丢了/过期了，则按 **本项目的绝对路径** 匹配进程命令行
#      （run.sh 用 "$BASE/Mon3tr-MCP.py" 启动，所以能精确认出自己）
#
# 刻意不做的事：不按裸文件名 “Mon3tr-MCP.py” 全机匹配。
# 那样会把别的目录里跑的同名服务一起杀掉 —— 2026-10-08 在 8.163 上真踩过：
# 测试目录里执行 stop.sh，把生产环境 /root/Mon3tr-MCP 的实例（systemd 管的）
# 一起 SIGTERM 了，8.163 的 8000 端口直接空了。所以这里必须带项目路径。
set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE"

PID_FILE="logs/mon3tr-mcp.pid"
PATTERN="$BASE/Mon3tr-MCP[.]py"     # [.] 避免正则把 . 当通配符

find_pids() {
    if [ -f "$PID_FILE" ]; then
        p="$(cat "$PID_FILE" 2>/dev/null || true)"
        if [ -n "$p" ] && kill -0 "$p" 2>/dev/null; then
            echo "$p"
            return
        fi
    fi
    if command -v pgrep >/dev/null 2>&1; then
        candidates="$(pgrep -f "$PATTERN" 2>/dev/null || true)"
    else
        candidates="$(ps -eo pid=,args= 2>/dev/null | grep -F "$BASE/Mon3tr-MCP.py" | grep -v grep | awk '{print $1}' || true)"
    fi
    # 只认解释器进程：免得把“命令行里恰好含这个路径”的编辑器 / 包装脚本 / shell 本身算进来
    for p in $candidates; do
        args="$(ps -o args= -p "$p" 2>/dev/null || true)"
        case "$args" in
            *python*) echo "$p" ;;
        esac
    done
}

pids="$(find_pids | tr '\n' ' ' | sed 's/ *$//')"

if [ -z "$pids" ]; then
    echo "Mon3tr-MCP 未在运行（本项目：$BASE）"
    rm -f "$PID_FILE"
    exit 0
fi

# 先把“要杀谁”打出来，误杀时一眼能看出来
for p in $pids; do
    args="$(ps -o args= -p "$p" 2>/dev/null || true)"
    echo "停止 PID $p : ${args:-<进程已退出>}"
    kill "$p" 2>/dev/null || true
done

# 最多等 10 秒优雅退出
for _ in $(seq 1 10); do
    alive=""
    for p in $pids; do
        if kill -0 "$p" 2>/dev/null; then alive=1; fi
    done
    [ -z "$alive" ] && break
    sleep 1
done

# 还不走就强杀
for p in $pids; do
    if kill -0 "$p" 2>/dev/null; then
        echo "PID $p 未在 10 秒内退出，强制结束"
        kill -9 "$p" 2>/dev/null || true
    fi
done

rm -f "$PID_FILE"
echo "Mon3tr-MCP 已停止 (PID: $pids)"
