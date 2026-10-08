#!/usr/bin/env bash
# 把 TinyFish API Key 写进项目目录的 .env（供 tinyfish_search 读取）
#
# 用法：
#   ./set-tinyfish-key.sh sk-tinyfish-xxxx     # 直接传 key
#   ./set-tinyfish-key.sh                      # 交互式输入（不回显）
#
# Key 免费获取：https://tinyfish.ai （Search API 免费 12000 次/天）
set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$BASE/.env"

key="${1:-}"
if [ -z "$key" ]; then
    printf 'TinyFish API Key（https://tinyfish.ai）: '
    if [ -t 0 ] && command -v stty >/dev/null 2>&1; then
        stty -echo
        read -r key
        stty echo
        echo
    else
        read -r key
    fi
fi

key="$(printf '%s' "$key" | tr -d '\r\n' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
if [ -z "$key" ]; then
    echo "没有拿到 key，未做修改" >&2
    exit 1
fi
case "$key" in
    sk-tinyfish-*) ;;
    *) echo "警告：key 不像 TinyFish 的格式（通常以 sk-tinyfish- 开头），仍然写入" >&2 ;;
esac

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
if [ -f "$ENV_FILE" ]; then
    grep -v '^[[:space:]]*TINYFISH_API_KEY[[:space:]]*=' "$ENV_FILE" >> "$tmp" || true
fi
printf 'TINYFISH_API_KEY=%s\n' "$key" >> "$tmp"
mv "$tmp" "$ENV_FILE"
trap - EXIT
chmod 600 "$ENV_FILE" 2>/dev/null || true

echo "已写入 $ENV_FILE（权限 600）"
echo "重启 Mon3tr-MCP 后生效："
echo "  systemd : systemctl restart Mon3tr-MCP"
echo "  launchd : launchctl kickstart -k gui/\$(id -u)/com.amiyawish.mon3tr-mcp"
echo "  手动/容器: 直接重启进程即可"
