# Mon3tr-MCP 跨平台部署脚本

同一套能力，四种系统各有一条落地路径。Windows 那套（隐藏窗口的登录自启计划任务）已经在跑，这里是等价的 Linux / macOS / Termux 版本。

| 系统 | 启动 | 停止 | 状态 | 开机自启 |
|------|------|------|------|----------|
| Windows | 计划任务 `Mon3tr-MCP` → `start-hidden.vbs`（隐藏窗口） | `stop-service.bat` | 看计划任务 / `logs\mon3tr-console.log` | 任务计划程序，登录时触发（Delay 20s） |
| Linux（systemd --user） | `systemctl --user start mon3tr-mcp` | `systemctl --user stop mon3tr-mcp` | `systemctl --user status mon3tr-mcp` | `systemctl --user enable --now mon3tr-mcp` |
| Linux（无 systemd） | `./start.sh` | `./stop.sh` | `./status.sh` | `crontab -e` 加 `@reboot /path/to/start.sh` |
| macOS | `./start.sh` | `./stop.sh` | `./status.sh` | `deploy/macos/` 里的 launchd plist |
| Termux（Android） | `./start.sh` | `./stop.sh` | `./status.sh` | 用 termux-boot 在 `~/.termux/boot/` 放启动脚本 |

## 通用脚本（Linux / macOS / Termux）

| 文件 | 作用 |
|------|------|
| `run.sh` | **前台**运行，给 systemd / launchd / 容器 / 手动调试用。自动探测解释器：`python3` 优先，回退 `python`；可用 `PYTHON=/path/to/python` 覆盖 |
| `start.sh` | **后台**启动（`nohup` + `logs/mon3tr-mcp.pid`），已在运行就不会起第二个实例 |
| `stop.sh` | 先 `SIGTERM`，10 秒后仍在则 `SIGKILL`；pid 文件丢了会自动按命令行匹配 `Mon3tr-MCP.py` |
| `status.sh` | 进程 / 已运行时长 / `127.0.0.1:8000` 是否可达 / 日志尾部（端口探测用 bash 内建 `/dev/tcp`，不依赖 nc/ss/lsof） |

```bash
chmod +x run.sh start.sh stop.sh status.sh   # 从 Windows 传过去时先补可执行位
./start.sh
./status.sh
```

日志都在 `logs/mon3tr-console.log`（与 Windows 那套同一个文件）。

## Linux：systemd --user

```bash
mkdir -p ~/.config/systemd/user
cp deploy/systemd/mon3tr-mcp.service ~/.config/systemd/user/
# 项目不在 ~/Mon3tr-MCP 时，改 unit 里的 WorkingDirectory / ExecStart
systemctl --user daemon-reload
systemctl --user enable --now mon3tr-mcp
systemctl --user status mon3tr-mcp
journalctl --user -u mon3tr-mcp -f
```

⚠️ **要「没登录也常驻」必须开 linger**：

```bash
loginctl enable-linger "$USER"
```

user 单元默认 `Linger=no`，SSH 会话一结束，systemd 会停掉 `user@<uid>` 连带服务一起带走——8.163 上 mihomo 就是这么被"杀掉"过一次（表现为端口突然消失、依赖它的服务全崩）。`systemctl --user` 里跑任何常驻服务都要注意这一点。

装了 systemd 那套之后**不要再叠加 `./start.sh`**：两边都会去抢 `127.0.0.1:8000`，先起的那个会占住端口，后起的那个直接退出。要么用 systemd，要么用脚本，二选一。

## macOS：launchd

`deploy/macos/com.amiyawish.mon3tr-mcp.plist` 里的 `/Users/CHANGE_ME/` 换成你的实际家目录：

```bash
sed "s#/Users/CHANGE_ME#$HOME#g" deploy/macos/com.amiyawish.mon3tr-mcp.plist \
    > ~/Library/LaunchAgents/com.amiyawish.mon3tr-mcp.plist
launchctl load -w ~/Library/LaunchAgents/com.amiyawish.mon3tr-mcp.plist
launchctl list | grep mon3tr          # 看是否加载
launchctl unload -w ~/Library/LaunchAgents/com.amiyawish.mon3tr-mcp.plist   # 卸载
```

`RunAtLoad` + `KeepAlive` 的效果等价于 systemd 的 `enable` + `Restart=on-failure`。

## Termux（Android）

```bash
pkg install python
pip install requests beautifulsoup4 mcp python-docx openpyxl pypdf reportlab pdf2docx cloudscraper
./start.sh
```

开机自启需要装 termux-boot 插件，然后在 `~/.termux/boot/` 放一个脚本调用本项目的 `start.sh`（`termux-wake-lock` 可顺便防止被系统休眠杀掉）。

## 与 AI 题库服务的联动

题库服务（`ocsjs-ai-answer-service`）连的是 `http://127.0.0.1:8000/mcp`，两侧**启动顺序无所谓**：题库服务的 MCP 桥会按 1/2/4…30s 退避重连，MCP 后起也能追上。

判断 MCP 是否真的起来了，看进程和端口最直接（`/api/health` 的 `mcp.connected` 只能当参考——它是题库侧 MCP 会话的状态缓存，端口没了它未必马上翻 `false`，2026-10-08 实测见过它滞后的情形）：

```bash
./status.sh                        # 本机脚本，Linux/macOS/Termux
ss -ltnp | grep 8000               # 或 netstat -ano | grep :8000

curl -s http://127.0.0.1:5000/api/health    # 题库侧状态（参考）
# 期望看到 "mcp":{"connected":true,"tools":["bing_search","fetch_page"]}
```

ℹ️ **Mon3tr-MCP 冷启动要 30~60 秒**（要 import 一堆解析库、加载干员/关卡数据），这期间端口还没绑、日志也没几行，别当成启动失败。Windows 那条计划任务链路同样是这个速度——任务触发后等一分钟再判断。

## 两个坑（跨平台搬运时最容易踩）

1. **行尾**：`.sh` / `.service` / `.plist` 必须是 LF。仓库里的 `.gitattributes`（`text eol=lf`）已经强制了这一点，但如果你用手工拷贝/网盘传文件绕过了 git，Linux 上会报 `bad interpreter: /usr/bin/env bash^M`。
2. **可执行位**：从 Windows 或压缩包搬过去的 `.sh` 往往没有 `+x`，`chmod +x` 一下；`start.sh` 内部用 `bash ./run.sh` 就是为了不完全依赖它。
