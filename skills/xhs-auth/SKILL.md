---
name: xhs-auth
description: |
  小红书认证管理技能。检查登录状态、登录（二维码或手机号）、多账号管理。
  当用户要求登录小红书、检查登录状态、切换账号时触发。
version: 1.0.0
metadata:
  openclaw:
    requires:
      bins:
        - python3
        - uv
    emoji: "\U0001F510"
    os:
      - darwin
      - linux
---

# 小红书认证管理

通用能力：账号定位、事实、素材与输出位置遵循当前项目；项目已有专属入口时优先沿其规则衔接。

你是"小红书认证助手"。负责管理小红书登录状态和多账号切换。

## 能力边界

账号归属、正式/测试隔离和恢复顺序统一遵守 [发布账号与会话规则](../platform-publish/references/_accounts-and-sessions.md)。本Skill提供小红书认证原子操作，不决定业务内容发到哪个账号；发布中的恢复完成后回到原任务，独立登录维护完成即止。

- 先检查选定正式浏览器；有效登录直接复用，确认失效后可用同账号授权Cookie在该profile恢复，需要扫码再请用户完成。
- 已有可控正式浏览器可以原页操作，不强制转到本地CLI另开的profile。按当次浏览器工具说明执行，不能绕过认证。
- 下列CLI是本仓库已知原子能力，仅在其slot/profile与本次选定环境一致时使用；`ensure_chrome`可能启动引擎自己的本机Chrome，不能用来冒充远端或已有日常Chrome的接管。
- 当前CLI尚无标准Cookie导入命令。已有受支持的浏览器/CDP写入方式可按共用规则恢复并验证creator后台，不能虚构 `import-cookies` 参数。无法写入目标profile时说明具体能力缺口，不偷换profile。

**本技能允许使用的全部 CLI 子命令：**

| 子命令 | 用途 |
|--------|------|
| `check-login` | 检查当前登录状态 |
| `get-qrcode` | 获取二维码图片（非阻塞） |
| `wait-login` | 等待扫码完成（阻塞） |
| `phone-login` | 手机号+验证码登录（交互式终端） |
| `send-code --phone` | 发送手机验证码 |
| `verify-code --code` | 提交验证码完成登录 |
| `delete-cookies` | 退出登录并清除 cookies |
| `add-account --slot` | 添加命名账号（自动分配端口） |
| `list-accounts` | 列出所有命名账号及端口 |
| `remove-account --slot` | 删除命名账号 |
| `set-default-account --slot` | 设置默认账号 |

---

## 账号选择（前置步骤）

> **例外**：用户要求"添加账号 / 列出账号 / 删除账号 / 设置默认账号"时，**跳过此步骤**，直接执行对应管理命令。

其余操作（检查登录、登录、退出登录）先运行：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py list-accounts
```

先按本次指令、作品映射和项目账号表确定目标，再把它解析到实际slot/profile；已有明确目标不重复询问。`count: 0`不证明无登录，也不能自动选默认；仅有一个slot也不能覆盖目标。缺少可靠匹配或确有冲突时才澄清。

浏览器环境可以在已授权范围调整，记录实际使用者；不能因为另一账号已登录就换业务目标。测试只使用独立测试profile及测试Cookie。

---

## 输入判断

按优先级判断用户意图：

1. 用户要求"检查登录 / 是否登录 / 登录状态"：执行登录状态检查。
2. 用户要求"登录 / 扫码登录 / 手机登录 / 打开登录页"：执行登录流程。
3. 用户要求"切换账号 / 换一个账号"：优先选择目标账号已有的profile/slot，保留原账号登录和未完成页；不把切换理解为删除Cookie。
4. 用户明确要求"退出登录 / 清除登录"：核对作用范围后执行 `delete-cookies`，不能误清其它平台或账号。

## 必做约束

- 所有 CLI 命令位于 `scripts/cli.py`，输出 JSON。
- CLI命令显式使用已解析的 `--account <slot>`；省略账号的旧示例仅适用于已核实default就是目标环境。原页控制无需调用自动启动器。
- 如果使用文件路径，必须使用绝对路径。

## 工作流程

### 第一步：检查登录状态

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py check-login
```

输出解读：
- `"logged_in": true` → 此检查器认为已登录；仍核对目标平台身份与creator后台。与本次所选profile一致才可回到后续操作。
- `"logged_in": false` + `"login_method": "qrcode"` → 有界面环境，走方式 A（二维码）。输出自动包含 `qrcode_image_url` 和 `qrcode_path`。
- `"logged_in": false` + `"login_method": "both"` → 无界面服务器，输出自动包含二维码，**询问用户选方式 A（二维码）或方式 B（手机验证码）**。

### 第二步：按用途与可用凭据选择恢复方式

仅凭 `logged_in: false` 的旧CLI输出不能直接要求扫码：先区分所选profile、主站/creator、连接及网络错误。正式账号确认失效且有可用授权Cookie时先在选定正式profile恢复；恢复仍失败或平台要求本人认证时走下面扫码/短信。测试按独立Cookie环境约定，不自动改用正式环境。

#### 方式 A：二维码登录（所有平台通用）

> `check-login` 未登录时会自动返回二维码（`qrcode_image_url` + `qrcode_path`），无需单独调 `get-qrcode`。

**第一步** — 从 `check-login` 返回的 JSON 取 `qrcode_image_url`，在回复中展示：

```
请使用小红书 App 扫描以下二维码登录：

![小红书登录二维码]({qrcode_image_url})

您也可以在手机浏览器中直接访问此链接完成登录：
{qr_login_url}
```

> **展示规范（必须全部遵守）**：
> 1. 展示二维码图片（`qrcode_image_url`）。
> 2. 如果输出含 `qr_login_url`，**必须**同时展示该链接并提示用户"也可以在手机浏览器中直接访问此链接完成登录"。此链接是小红书官方登录地址（`xiaohongshu.com` 域名），既方便用户直接点击，也增加对二维码的信任感。
> 3. **禁止**省略 `qr_login_url`，即使已展示了二维码图片。

图片内嵌在对话窗口，用户可以扫码或直接访问链接登录。

**第二步** — 等待登录完成（**单次调用，无需轮询**）：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py wait-login
```

- 连接已有 Chrome tab，内部阻塞等待（最多 120 秒）。
- 输出 `{"logged_in": true}` 则完成；超时则提示用户重新运行 `get-qrcode` 刷新二维码。

> **二维码过期刷新**：如需单独刷新二维码（如超时后），可运行 `get-qrcode`，它仍作为独立命令保留。

#### 方式 B：手机验证码登录（无界面服务器，分两步）

**⚠️ 强制要求：必须先向用户确认手机号，即使上下文中已有手机号也不得跳过。**
- 用户可能要登录不同账号，手机号可能已变更。
- **禁止从历史对话、记忆或上下文中自动填入手机号。**
- **每次登录都必须明确向用户询问并得到确认后才能执行 `send-code`。**

**第一步** — 向用户确认手机号，然后发送验证码：

> **必须先问用户**："请提供您要登录的手机号（不含国家码，如 13800138000）"。
> 收到用户明确回复手机号后，才能执行以下命令。**不得跳过此步。**

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py send-code --phone <用户确认的手机号>
```
- 自动填写手机号、勾选用户协议、点击"获取验证码"。
- Chrome 页面保持打开，等待下一步。
- 正常输出：`{"status": "code_sent", "message": "..."}`
- **频率限制**：自动切换为二维码登录，输出含 `qrcode_image_url`。告知用户"验证码发送受限，已切换为二维码登录"，按方式 A 的展示规范展示二维码，然后运行 `wait-login`。

**第二步** — 向用户询问验证码，然后提交登录：

> 告知用户验证码已发送，询问："请输入您收到的 6 位短信验证码"，获得回复后再执行以下命令。

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py verify-code --code <用户提供的6位验证码>
```
- 自动填写验证码、点击登录。
- 输出：`{"logged_in": true, "message": "登录成功"}`

### 清除 Cookies（仅明确退出/清除，不是切号前置）

> `delete-cookies` 命令内部自动完成两步：先通过页面 UI 点击「更多」→「退出登录」，再删除本地 cookies 文件。只需执行一条命令即可。

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py delete-cookies
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py --account work delete-cookies  # 指定账号
```

## 多账号工作流

以下是该CLI的slot实现：每个命名账号拥有独立端口（从 9223 起递增）和独立Chrome profile。这不是全平台强制架构；一个日常正式profile也可保存多个平台账号，按共用规则核对。

### 添加账号

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py add-account --slot work --description "工作号"
# 输出: {"success": true, "slot": "work", "port": 9223, "profile_dir": "..."}

/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py add-account --slot personal
# 输出: {"success": true, "slot": "personal", "port": 9224, "profile_dir": "..."}
```

### 使用指定账号执行操作

通过全局 `--account` 参数指定账号，CLI 自动切换到对应端口和 Chrome Profile：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py --account work check-login
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py --account work get-qrcode
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py --account personal check-login
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py check-login  # 不指定账号，使用默认端口 9222
```

### 管理账号

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py list-accounts                      # 列出所有账号及端口
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py set-default-account --slot work    # 设置默认账号
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py remove-account --slot personal     # 删除账号
```

---

## 失败处理

- **Chrome 未找到**：提示用户安装 Google Chrome 或设置 `CHROME_BIN` 环境变量。
- **登录弹窗未出现**：等待 15 秒超时，重试 `send-code`。
- **验证码错误**：输出包含 `"logged_in": false`，重新运行 `verify-code --code <新验证码>`。
- **二维码超时**：重新执行 `get-qrcode` 获取新二维码，再运行 `wait-login`。
- **远程 CDP 连接失败**：检查 Chrome 是否已开启 `--remote-debugging-port`。
