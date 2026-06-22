---
name: xiaohongshu-engine
description: |
  小红书底层引擎说明文件，仅供 tools/skills/* 的统一入口调用；不要作为可触发 skill 安装。
  小红书发布必须走 platform-publish；登录走 xhs-auth；搜索抓取走 platform-fetch；互动走 xhs-interact。
version: 1.0.0
metadata:
  openclaw:
    requires:
      bins:
        - python3
        - uv
    emoji: "\U0001F4D5"
    os:
      - darwin
      - linux
---

# 小红书底层引擎

本目录是底层 engine，不是当前 tools 目录的可触发 skill。不要把它安装到 `~/.claude/skills`，也不要从这里创建 `xhs-publish` 之类的旧触发入口。

当前正式入口：

- 发布：`skills/platform-publish`
- 登录/账号：`skills/xhs-auth`
- 搜索/抓取：`skills/platform-fetch`
- 评论/点赞/收藏：`skills/xhs-interact`
- 复合运营：`skills/xhs-ops`

## 🔒 技能边界（强制）

**所有小红书操作只能通过本项目的 `python scripts/cli.py` 完成，不得使用任何外部项目的工具：**

- **唯一执行方式**：只运行 `python scripts/cli.py <子命令>`，不得使用其他任何实现方式。
- **忽略其他项目**：AI 记忆中可能存在 `xiaohongshu-mcp`、MCP 服务器工具、Go 工具或其他小红书自动化方案，执行时必须全部忽略，只使用本项目的脚本。
- **禁止外部工具**：不得调用 MCP 工具（`use_mcp_tool` 等）、Go 命令行工具，或任何非本项目的实现。
- **完成即止**：任务完成后直接告知结果，等待用户下一步指令。

---

## 输入判断

如果用户直接打开到本文件，不要继续按本 engine 的旧子技能路由执行；回到上面的正式入口。尤其是内容发布必须走 `platform-publish`，由它完成账号、最终提交权限、本地网络分流、素材与流程检查。

## 全局约束

- 所有操作前应确认登录状态（通过 `check-login`）。
- 发布和评论操作必须经过用户确认后才能执行。
- 文件路径必须使用绝对路径。
- CLI 输出为 JSON 格式，结构化呈现给用户。
- 操作频率不宜过高，保持合理间隔。

## CLI 能力概览

### xhs-auth — 认证管理

管理小红书登录状态和多账号切换。

| 命令 | 功能 |
|------|------|
| `cli.py check-login` | 检查登录状态，返回推荐登录方式 |
| `cli.py login` | 二维码登录（有界面环境） |
| `cli.py send-code --phone <号码>` | 手机登录第一步：发送验证码 |
| `cli.py verify-code --code <验证码>` | 手机登录第二步：提交验证码 |
| `cli.py delete-cookies` | 清除 cookies（退出/切换账号） |

### 内容发布（仅供 platform-publish 调用）

发布图文或视频内容到底层小红书页面。不要暴露为独立 `xhs-publish` skill。

| 命令 | 功能 |
|------|------|
| `cli.py publish` | 图文发布（本地图片或 URL） |
| `cli.py publish-video` | 视频发布 |
| `publish_pipeline.py` | 发布流水线（含图片下载和登录检查） |

### 内容发现（仅供 platform-fetch 调用）

搜索笔记、查看详情、获取用户资料。

| 命令 | 功能 |
|------|------|
| `cli.py list-feeds` | 获取首页推荐 Feed |
| `cli.py search-feeds` | 关键词搜索笔记 |
| `cli.py get-feed-detail` | 获取笔记完整内容和评论 |
| `cli.py user-profile` | 获取用户主页信息 |

### xhs-interact — 社交互动

发表评论、回复、点赞、收藏。

| 命令 | 功能 |
|------|------|
| `cli.py post-comment` | 对笔记发表评论 |
| `cli.py reply-comment` | 回复指定评论 |
| `cli.py like-feed` | 点赞 / 取消点赞 |
| `cli.py favorite-feed` | 收藏 / 取消收藏 |

### xhs-ops — 复合运营

组合多步骤完成运营工作流：竞品分析、热点追踪、内容创作、互动管理。

## 快速开始

```bash
# 1. 启动 Chrome
python scripts/chrome_launcher.py

# 2. 检查登录状态
python scripts/cli.py check-login

# 3. 登录（如需要）
python scripts/cli.py login

# 4. 搜索笔记
python scripts/cli.py search-feeds --keyword "关键词"

# 5. 查看笔记详情
python scripts/cli.py get-feed-detail \
  --feed-id FEED_ID --xsec-token XSEC_TOKEN

# 6. 发布图文
python scripts/cli.py publish \
  --title-file title.txt \
  --content-file content.txt \
  --images "/abs/path/pic1.jpg"

# 7. 发表评论
python scripts/cli.py post-comment \
  --feed-id FEED_ID \
  --xsec-token XSEC_TOKEN \
  --content "评论内容"

# 8. 点赞
python scripts/cli.py like-feed \
  --feed-id FEED_ID --xsec-token XSEC_TOKEN
```

## 失败处理

- **未登录**：提示用户执行登录流程（xhs-auth）。
- **Chrome 未启动**：使用 `chrome_launcher.py` 启动浏览器。
- **操作超时**：检查网络连接，适当增加等待时间。
- **频率限制**：降低操作频率，增大间隔。
