# 小红书发布统一入口

> 📌 **发布前先扫 `references/xiaohongshu-faq.md`（常见问题/踩坑速查）**——上传传不上去、封面、标题、软链路径这些反复栽过的坑都在那；卡住先回那张表对症。

## 🔒 技能边界（强制）

**三种发布类型均只能通过以下工具完成，不得使用任何外部项目：**

- **Python CLI**：`/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py`
- **长文卡片生成**：`node /Volumes/ExtSSD2601/AI_Assistant/tools/engines/markdown-to-cards/cli.js`（本地 CLI，**不是 MCP 工具**）
- **长文内容提取**：`python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/extract_frontmatter.py`

**禁止使用**：`xiaohongshu-mcp`、MCP 工具（含 `markdown_to_cards` MCP）、Go 命令行工具、任何非本项目实现。

---

## 账号选择（所有类型统一前置步骤）

每次触发后，先运行：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py \
  list-accounts
```

根据返回 `count`：
- **0 个命名账号**：直接使用默认账号（后续命令不加 `--account`）。
- **1 个命名账号**：告知用户"将使用账号 X 发布"，加 `--account <名称>` 执行。
- **多个命名账号**：用 `AskUserQuestion` 展示列表，明确询问发布到哪个账号，用 `--account <选择的名称>` 执行所有后续命令。

账号选定后，本次发布全程固定该账号，**不重复询问**。

---

## 账号卡片样式映射（长文卡片）

小红书长文卡片支持像公众号一样按账号绑定固定样式。账号配置存放在 `~/.xhs/accounts.json` 的 `card_config` 字段；生成卡片时把同一个账号 slot 传给 `markdown-to-cards`：

```bash
node /Volumes/ExtSSD2601/AI_Assistant/tools/engines/markdown-to-cards/cli.js \
  --account <ACCOUNT> \
  --input "<files.cards_md_file>" \
  --output-dir "$OUTDIR"
```

当前固定映射：

| 账号 slot | 固定正文风格 | 栏目/页眉标签 | 封面 |
|---|---|---|---|
| `张和_专业号` | `unified-claude` | `张和 AI 产品实战派` | `cover_template=default`，即正文用共用模板，封面使用默认小红书封面 |

如果用户没有明确要求实验风格，不要覆盖账号配置。需要临时测试其他风格时，显式传 `--style` / `--cover-template` 等参数，显式参数优先于账号默认配置。

---

## 网络分流前置步骤（强制）

> 真因：整机走 Tailscale 海外出口时，上传入口和分片 CDN（`ros-upload.xiaohongshu.com` / `ros-upload-d*.xhscdn.com`）只要有一部分掉到 exit node，就会上传 0%、卡死或极慢。`route-bypass apply` 把小红书 IP 和已观测上传 CDN 网段钉到本地网关出口；遇到 Tailscale DNS 返回坏边缘时，还会写入带 BEGIN/END 标记的受控 `/etc/hosts` 块，把关键域名切到本地网关 DNS 返回且可连通的边缘。**漏跑这步 = 视频/图片传不上去。** 详见 `references/xiaohongshu-faq.md` #1。

为避免 Tailscale exit node 导致小红书发布走海外出口，账号选定后、任何会访问小红书网页的 CLI 前，必须先刷新本地分流路由：

```bash
tailscale set --exit-node-allow-lan-access=true 2>/dev/null || true
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/xhs-route-bypass.zsh apply
```

如果在无 TTY 环境中遇到 `sudo: a password is required`，允许改用 macOS 管理员授权窗口执行同一脚本：

```bash
osascript -e 'do shell script "tailscale set --exit-node-allow-lan-access=true 2>/dev/null || true; /Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/xhs-route-bypass.zsh apply" with administrator privileges'
```

适用范围：
- 长文流程：`check-login`、`wait-login`、`long-article`、`next-step`、正式模式 `click-publish` 前都必须完成。
- 图文流程：`fill-publish` 和 `save-draft` 前都必须完成。
- 视频流程：`fill-publish-video` 和 `save-draft` 前都必须完成。

**如果直接执行和管理员授权 fallback 都失败，立即停止发布流程并报告错误；不得继续打开发布页、填写表单或点击发布。不要手工散改 `/etc/hosts` 或手工 `route add/delete`；只能使用 `route-bypass apply/remove` 管理。**

---

## 内容类型判断

按优先级路由：

1. 用户明确说"长文" → **长文流程**
2. 用户明确说"视频" / 提供 `.mp4` / `.mov` / `.avi` 路径 → **视频流程**
3. 用户明确说"图文" / 提供图片路径或图片 URL → **图文流程**
4. 提供 `.md` 文件路径或含 frontmatter（`---`）的 Markdown 内容 → **长文流程**
5. 不明确 → 用 `AskUserQuestion` 询问（长文 / 图文 / 视频）

---

## 长文发布流程

> ⚠️ **以下禁止事项违反任何一条 = 任务失败：**
> 1. 禁止使用占位/编造内容（标题、摘要、关键词、正文必须从 Markdown 文件真实提取）
> 2. 禁止跳过步骤（Step 0–5 按顺序全部执行）
> 3. 禁止只打印日志（每步必须真正调用 CLI 工具）
> 4. 禁止自选账号（测试必须用 `测试号`，正式发布使用用户指定账号）
> 5. 测试模式绝不调用 `click-publish`

**输入需求**：Markdown 文件路径（含 frontmatter，需有 `title`/`abstract`/`keywords` 字段）

### 前置步骤：提取内容

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/extract_frontmatter.py \
  "<MD_FILE_PATH>" \
  --save-dir /tmp
```

输出 JSON 包含：
- `title` — 标题
- `abstract` — 摘要
- `keywords` — 关键词数组（已去空格）
- `body` — 正文
- `valid` — 是否通过验证（`false` 时停止执行，报告 `errors`）
- `files.title_file` / `files.body_file` / `files.desc_file` / `files.cards_md_file` — 已保存的临时文件路径

**`valid` 为 `false` → 停止执行，将 `errors` 报告给用户。**

### Step 0：检查登录状态

执行本步骤前，必须先完成“网络分流前置步骤”。

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py \
  --account <ACCOUNT> \
  check-login
```

- 返回 `"logged_in": true` → 继续。
- 返回 `"logged_in": false` → 展示二维码（`qrcode_image_url`），立即自动执行：

执行 `wait-login` 前，也必须先完成“网络分流前置步骤”。

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py \
  --account <ACCOUNT> \
  wait-login
```

`wait-login` 自动轮询最长 120 秒，登录成功后继续，无需人工确认。

### Step 1：生成卡片图片

```bash
OUTDIR="/tmp/xhs_cards_$(date +%s)"
mkdir -p "$OUTDIR"

node /Volumes/ExtSSD2601/AI_Assistant/tools/engines/markdown-to-cards/cli.js \
  --account <ACCOUNT> \
  --input "<files.cards_md_file>" \
  --output-dir "$OUTDIR"
```

解析返回 JSON 中的 `files` 数组，记录所有图片路径（含封面 `card_00_cover.png`）。

若账号配置中已有 `card_config`，不要再手动重复传 `--style`；例如 `张和_专业号` 会自动使用 `unified-claude` 正文风格、`张和 AI 产品实战派` 页眉标签和默认封面模板。

**验收条件**：`files` 数组长度 > 0。若为空或报错 → 失败，不继续。

### Step 2：（已由前置步骤完成）

临时文件已由 `extract_frontmatter.py` 生成，直接使用：
- `{files.title_file}` — 标题
- `{files.body_file}` — 占位正文（Step 3 用）
- `{files.desc_file}` — 描述（Step 4 用）

### Step 3：长文编辑器填写

执行本步骤前，必须先完成“网络分流前置步骤”。

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py \
  --account <ACCOUNT> \
  long-article \
  --title-file "<files.title_file>" \
  --content-file "<files.body_file>"
```

**验收条件**：返回 `"success": true`，页面出现"长文已填写，请选择模板"等成功信号。若报错或 `success: false` → 失败。

### Step 4：进入发布页

执行本步骤前，必须先完成“网络分流前置步骤”。

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py \
  --account <ACCOUNT> \
  next-step \
  --content-file "<files.desc_file>" \
  --images <Step1 卡片图片路径，逐个展开> \
  --topics <keywords 数组元素，空格分隔> \
  --original
```

`--images` 必须传入 Step 1 `files` 数组里的**所有路径**，逐个展开。
`--topics` 必须传入前置步骤 `keywords` 数组的**所有元素**（已去空格）。

**验收条件**：CLI 返回成功，页面出现描述区/话题区/封面区/发布按钮。若仍停在"请选择模板"或长文编辑器 → 失败。

### Step 5：发布

- **测试模式**（消息含"模式：测试"）：到此停止，**绝不调用 `click-publish`**。告知用户"已走到发布页，测试通过"。
- **正式模式**：

执行正式发布前，必须先完成“网络分流前置步骤”。

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py \
  --account <ACCOUNT> \
  click-publish
```

### Step 6：收尾

```bash
rm -rf "$OUTDIR"
```

发布完成后发飞书消息通知（群 ID 见 WORKFLOWS.md）：`「{title}」已发布到小红书长文`

若为定时发布任务，更新 `~/.openclaw/workspace/workflow-state.json` 状态为 `done`，并追加 7 天后的 `pull_stats` 任务。

---

## 图文发布流程

**输入需求**：标题 + 正文 + 图片（本地绝对路径或 HTTP/HTTPS URL，脚本自动下载）

### 输入判断

1. 用户已提供 `标题 + 正文 + 图片` → 进入图文发布。
2. 用户只提供网页 URL → 用 WebFetch 提取内容和图片，给出草稿等待确认。
3. 信息不全 → 先补齐，不直接发布。

### 图片提取规则（URL 模式）

- **优先取 `data-src`**：若 `img` 同时有 `src` 和 `data-src`，以 `data-src` 为准。
- **跳过占位图**：`src` 含 `/shims/`、`/placeholder`、`/theme/`、`16x9.png`、`1x1.png` 等直接忽略。
- **只取内容图**：跳过网站 logo、图标、视频封面缩略图。
- **格式验证**：图片 URL 以 `.jpg`、`.jpeg`、`.png`、`.webp`、`.gif` 结尾，否则跳过。

### 标题检查

长度 ≤ 20（UTF-16 单位：汉字/全角符号计 1，英文/数字/半角符号每 2 个计 1）。

**超长处理（禁止机械截断）**：根据原标题核心含义重新创作，目标 19–20 单位，直接使用新标题，无需询问用户。

### 正文格式

- 段落之间双换行分隔；简体中文；话题标签放最后一行：`#标签1 #标签2 #标签3`

### 用户确认

通过 `AskUserQuestion` 展示标题、正文、图片，获得明确确认后继续。

### 写入临时文件

将标题和正文写入 UTF-8 文本文件，不在命令行参数中内联中文。

### 执行发布

执行本步骤前，必须先完成“网络分流前置步骤”。

```bash
# 步骤 1: 填写图文表单
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py \
  fill-publish \
  --title-file /tmp/xhs_title.txt \
  --content-file /tmp/xhs_content.txt \
  --images "<path_or_url_1>" "<path_or_url_2>" \
  [--tags "标签1" "标签2"] \
  [--schedule-at "2026-03-10T12:00:00"] \
  [--original] [--visibility "公开可见"]
```

图片支持本地路径和 HTTP/HTTPS URL，**脚本自动下载，禁止手动 curl/wget**。

```bash
# 步骤 2（仅保存草稿时）:
tailscale set --exit-node-allow-lan-access=true 2>/dev/null || true
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/xhs-route-bypass.zsh apply

/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py \
  save-draft
```

填写完成后告知用户：
> "内容已全部填写完毕，请：
> 1. 在浏览器中检查标题、正文、图片是否正确
> 2. 本地分流已应用；如果页面停留超过 30 分钟，点击发布前重新运行 `/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/xhs-route-bypass.zsh apply`
> 3. 手动点击页面上的发布按钮
> 发布完成后无需关闭或恢复 Tailscale exit node。"

> ⚠️ **`click-publish` 和 `publish` 禁止在自动化流程中调用。** 发布必须由用户手动点击。

> ⚠️ **用户要求取消时必须调用 `save-draft`**，不得直接关闭 tab。

---

## 视频发布流程

**输入需求**：标题 + 正文 + 视频（本地绝对路径，`.mp4`/`.mov` 等）+ 封面图（本地绝对路径，`.jpg`/`.png` 等）

### 稳定性门槛与发布顺序

- 小红书视频链路不稳定时，只能使用 `测试号` 做复现和修复；在 `测试号` 连续跑通「本地网络分流与 host 探测通过 → 视频上传进度推进并完成 → 标签联想全部插入 → 封面上传通过 → 发布按钮可点击」前，禁止对真实账号执行 `publish-video` 或自动点击最终发布按钮。
- 多条待发布笔记必须逐条处理：一次只执行一条 `fill-publish-video` 或 `publish-video`，该条成功后写入对应内容目录的 `published.md` / 状态记录，再进入下一条。禁止写后台循环一次性提交所有真实账号笔记，禁止同时打开多条发布页并行上传，禁止“先把所有笔记都开始上传再回来检查”。
- 批量计划只是队列，不是并发发布许可。即使用户说"这个账号其他笔记都发掉"，也要按队列一条一条跑，并在每条失败时停止后续真实发布，先诊断失败原因。

### 必做约束

- 没有视频不得发布；没有封面图也不得发布。视频和封面图都是必填。
- 标题长度 ≤ 20（规则同图文）。
- 发布前用 `AskUserQuestion` 确认标题、正文、视频。
- 所有路径必须绝对路径。

### 执行发布

执行本步骤前，必须先完成“网络分流前置步骤”。

```bash
# 步骤 1: 填写视频表单
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py \
  fill-publish-video \
  --title-file /tmp/xhs_title.txt \
  --content-file /tmp/xhs_content.txt \
  --video "/abs/path/video.mp4" \
  --cover "/abs/path/cover.png" \
  [--tags "标签1" "标签2"] \
  [--visibility "公开可见"] \
  [--no-original]
```

说明：
- `fill-publish-video` 会自动校验小红书本地网络分流；校验失败时会自动刷新路由和托管 hosts。不得手工跳过，只有本地调试才允许加 `--skip-route-bypass`。
- `--video` 会自动解析软链到真实文件路径。
- `--cover` 必填；会在同一发布页完成「修改封面 → 上传图片 → 确定」，并等待最终发布按钮可点击后才返回成功；不再调用临时外挂脚本。
- 视频默认声明原创；如果素材不是原创，显式加 `--no-original`。

填写完成后告知用户：
> "内容已全部填写完毕，请：
> 1. 在浏览器中检查标题、正文、视频是否正确（视频处理最长需 10 分钟）
> 2. 本地分流已应用；如果页面停留超过 30 分钟，点击发布前重新运行 `/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/xhs-route-bypass.zsh apply`
> 3. 手动点击页面上的发布按钮
> 发布完成后无需关闭或恢复 Tailscale exit node。"

> ⚠️ **填表预览流程禁止调用 `click-publish`。** 只有用户明确确认“正式发布/定时发布”时，才允许改走下面的一键正式入口。

> ⚠️ **用户要求取消时必须调用 `save-draft`**，不得直接关闭 tab。

### 一键正式视频发布入口（用户确认后才用）

当用户已经明确确认要正式发布/定时发布，并且测试号稳定性门槛已经满足，才允许对选定账号逐条使用 `publish-video`；它会在一个流程内完成「本地网络分流刷新与 host 探测 → 软链解析 → 上传视频 → 填标题/正文/标签 → 默认原创声明 → 定时/可见范围 → 必填封面 → 等待按钮可点 → 点击发布」。

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py \
  publish-video \
  --title-file /tmp/xhs_title.txt \
  --content-file /tmp/xhs_content.txt \
  --video "/abs/path/video.mp4" \
  --cover "/abs/path/cover.png" \
  [--tags "标签1" "标签2"] \
  [--schedule-at "2026-06-21T20:00:00"] \
  [--visibility "公开可见"] \
  [--no-original]
```

禁止再使用 `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/tmp/...` 下的临时封面脚本或临时 `_publish.py` 作为正式入口；相关能力已固化进引擎。

### ⚠️ 故障复盘：为什么会把发布/路由搞坏（2026-06-21）——当前 skill 设计漏洞

**现象**：视频上传反复不通 → 我去手工排查网络 → 越改越坏，最后路由表被搞乱（`creator` 的 IP 报 `Errno 49 Can't assign address`、域名互相打架），且"发布完成"是**假成功**（两个号定时列表里根本没有笔记）。

**根因 = skill 这几处设计漏洞**：

1. **「网络分流前置」只写了"跑 `route-bypass apply`"，没写"它看起来没生效时怎么办 + 明令禁止手工乱钉"。** 当 route-bypass 像是没生效时（实因 DNS 经海外出口把 xhs 解析到海外/失效边缘 IP，或 IP 轮换过期），我就跑偏去**手工往 `/etc/hosts` 钉静态 IP + 手工 `route add/delete`**，把 route-bypass 的 managed 路由状态搞乱、IP 互相打架。**这是本次最大教训。**
2. **route-bypass 是"apply 时刻把当前 IP 钉死"的，IP 会轮换/过期**；skill 没强调"不通时只重跑、永远别手工钉 IP"。
3. **`click-publish` 只 `sleep` 后打日志"发布完成"，从不核实笔记是否真生成** → 假阳性。我据此误报 evc01 已发，实际没发。
4. **没规定"验证 = 去账号『定时发布/草稿』列表确认笔记真在"**，只看引擎日志就当成功。

**正确做法（已验证有效，应固化进 skill）**：

- **分流不通/出错时，唯一修法 = `route-bypass remove` 然后 `route-bypass apply`（干净重置）。绝不手工散改 `/etc/hosts`、绝不手工 `route add/delete`** —— 当前允许的 hosts 只限 `route-bypass` 写入的 `# BEGIN xhs-route-bypass managed hosts` 托管块，`remove` 会清理。
- **判定"发布成功"必须去账号定时/草稿列表核实笔记真在**，不能信"发布完成"日志（`click-publish` 当前不可信）。
- **标签联想等待要够长**（已从 3s 调到 10s + settle），否则标签选不上、丢标签。
- IP **必须走本地网关**（账号风控要求）；`route-bypass status` 里 `route decisions for route target IPv4` 不得出现 `interface=utun*` 或 `destination=default`，CLI 还会探测 `www.xiaohongshu.com/explore` 和 `ros-upload.xiaohongshu.com/` 是否能实际连通。正常态下 `route-bypass apply` 一跑即生效，不需要任何手工 hosts/route 操作。

---

## CLI 子命令总表

| 子命令 | 用途 | 适用流程 |
|--------|------|---------|
| `list-accounts` | 获取账号列表 | 共用（前置） |
| `check-login` | 检查登录状态 | 长文 |
| `wait-login` | 等待扫码登录 | 长文 |
| `long-article` | 填写长文编辑器 | 长文 |
| `next-step` | 进入发布页填描述+图片+话题 | 长文 |
| `click-publish` | 点击发布（长文正式模式自动；图文/视频用户手动） | 长文/共用 |
| `fill-publish` | 填写图文表单 | 图文 |
| `fill-publish-video` | 填写视频表单 | 视频 |
| `save-draft` | 保存草稿 | 图文/视频 |

---

## 指定账号 / 远程 Chrome

```bash
# 指定账号
... cli.py --account work fill-publish ...

# 远程 Chrome
... cli.py --host 10.0.0.12 --port 9222 fill-publish ...
```

---

## 处理输出

- **Exit code 0**：成功，输出 JSON 包含 `success`、发布相关字段。
- **Exit code 1**：未登录，提示用户扫码登录（参考 xhs-auth）。
- **Exit code 2**：错误，报告 JSON 中的 `error` 字段。

---

## 失败处理

> 更细的踩坑速查见 `references/xiaohongshu-faq.md`。

| 情况 | 处理 |
|------|------|
| 视频/图片传不上去、上传卡死超时 | **先查网络分流**：跑 `route-bypass apply` 后看 `route-bypass status`，所有上传目标不得走 `utun*` 或 `destination=default`，并确认 CLI host probe 通过；九成是 DNS/分流（faq #1） |
| 上传报文件错误/传空 | 路径若是软链先 `realpath` 解析成真实文件再传（faq #2） |
| 登录失败 | 提示用户重新扫码登录并重试 |
| 图片下载失败 | 提示更换图片 URL 或改用本地图片 |
| 标题过长 | 自动重写，保持语义，无需询问用户 |
| 视频处理超时 | 视频上传后最长等 10 分钟，超时提示重试 |
| 长文 Step 4 未到发布页 | 失败，不宣称"测试通过"，报告给用户 |
| 用户取消发布 | 必须运行 `save-draft`，不得直接关闭 tab |
| `extract_frontmatter.py` valid=false | 停止执行，将 errors 报告给用户 |
