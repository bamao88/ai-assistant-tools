> 历史归档（2026-10-22）：以下为迁移前原文，仅供追溯。旧 CLI、独立配置、Cookie 恢复和远端流程均未启用，不可照抄执行。当前执行入口为上一级同名平台 reference 与 `_local-chrome.md`。原文中的相对路径按迁移前位置理解。

# 抖音视频/图文发布（reference）

> 先按 [账号与会话](_accounts-and-sessions.md) 选择目标账号和浏览器：正式已有登录优先，掉线后可在选定正式profile用同账号Cookie恢复，必要时扫码。`item.json` 可复用 [platform-video 分步执行器](../../../engines/platform-video/README.md) 的字段步骤，但其 `open` 会另开专用profile，并非接管日常Chrome；所选环境不匹配时不能直接用它替换。下述引擎登录命令只管理各自凭据，具体能力见README。


把**本地视频或图文发布到抖音**。底层 = `vendor/social-auto-upload` 的 `sau douyin` 子命令（patchright 浏览器自动化 + cookie 登录态）。

> ⚠️ 这份 reference 管 **抖音视频 / 抖音图文（笔记）**。注意与 `references/wechatsync.md` 里"抖音图文同步"区分：wechatsync 走的是文章同步链路；本 reference 走的是抖音创作者中心的真实上传。优先用本 reference 发抖音视频。

## 引擎路径与前置

```bash
ENGINE=/Volumes/ExtSSD2601/AI_Assistant/tools/vendor/social-auto-upload
SAU="$ENGINE/.venv/bin/sau"
```

- 账号 cookie 存在 `tools/var/state/social-auto-upload/cookies/douyin_<account>.json`（已软链，凭证只放 var/）。
- 浏览器用 patchright Chromium（安装时已 `patchright install chromium`）。
- 账号白名单见 `vendor/wechatsync/config/project-platforms.json` 的 `assistant_zh.expectedAccounts.douyin`（当前：`张和`）。账号标识约定：`张和` = 本项目（assistant_zh，负责张和全部自媒体）名下的抖音号，cookie 落 `douyin_张和.json`。该约定仅适用于 assistant_zh；其它项目以其内容账号映射为准，不拿此示例覆盖已确认目标。

## 当前状态（2026-06-22）

抖音发布工具入口已恢复，支持人工最终确认需要的填表模式：

- 测试号 `测试号_抖音` 已通过真实 fill-only 复测：上传测试视频、填写标题/简介/话题、上传封面、选择自主声明，最终停在发布页，未点击“发布”。定时 fill-only 也已复测：`--schedule "2026-06-23 20:30"` 成功切到“定时发布”并校验页面时间值。
- `upload-video` / `upload-note` 支持 `--fill-only`：上传素材、填写标题/正文/标签/封面/定时时间后停在发布页，不点击最终“发布”。
- 当前测试阶段只允许 `--fill-only`；禁止点击最终“发布/定时发布”。即使命令支持自动提交，也必须等用户之后重新明确授权。
- 抖音话题/关键词最多 5 个。即使素材文案给了 10 个关键词，发布命令也只能传前 5 个；底层 CLI/uploader 会防御性截断到 5 个。
- 新版创作者中心必须先点左侧“高清发布”菜单里的“发布视频/发布图文”；底层 CLI 已内置该入口，不再直接等旧的 `div[class^='container'] input`。
- 视频发布页表单渲染可能在文件解析后才出现，当前 CLI 最长等待 120s；不要把这段等待误判为卡死。

真实账号使用前核验目标身份和提交权限。SAU Cookie 失效不证明日常浏览器失效；按共用账号顺序处理。以下 `login` + `check` 仅适用于明确选用SAU凭据环境的任务，不能声称同步修复了日常Chrome。

## 命令

**登录（建议在本地真实终端跑，可加 `--headed` 看页面）：**
```bash
"$SAU" douyin login --account <account_name> --headed
```
- 登录过程可能生成临时二维码图片；这类图片就是给用户扫的，**优先直接把本地图片展示/发给用户**，不要只给路径。

**检查登录态（只读）：**
```bash
"$SAU" douyin check --account <account_name>
```
使用SAU凭据环境上传前跑 `check`；失败按共用账号规则处理。同一正式浏览器仍有效时直接走现有页面，不因SAU失败强制扫码。

**发布页探针（只打开页面并截图，不上传、不填写）：**
```bash
"$SAU" douyin open-publish-page --account <account_name> \
  --kind video \
  --screenshot-out /tmp/douyin-publish-page.png
```
图文入口把 `--kind video` 改成 `--kind note`。这一步只验证创作者中心发布入口可达；不等同于 `fill-only`，也不会设置任何文件。

**发视频：**
```bash
"$SAU" douyin upload-video --account <account_name> \
  --file /abs/path/video.mp4 \
  --title "标题" \
  --desc "简介" \
  --tags 运动,训练 \
  --thumbnail-landscape /abs/cover-4x3.png \
  --thumbnail-portrait  /abs/cover-3x4.png \
  --fill-only --hold-seconds 0 \
  --schedule "2026-06-10 21:30"     # 可选：定时发布
```
- 必填：`--account --file --title`。其余可选。
- 封面：`--thumbnail-landscape`（4:3 横版）、`--thumbnail-portrait`（3:4 竖版）；`--thumbnail` 兼容旧参数=3:4 竖版。
- 带货可选：`--product-link --product-title`。
- `--schedule` 格式 `YYYY-MM-DD HH:MM`，传了即切换为抖音定时发布。
- 抖音最多 5 个话题，`--tags` 只传 5 个以内；如果 `publish_copy.md` 给了 10 个小红书关键词，只取前 5 个用于抖音。
- 默认 `manual-submit` 时必须传 `--fill-only`；`--hold-seconds 0` 表示浏览器保持打开直到终端 Ctrl-C，`--hold-seconds 60` 表示停 60 秒后关闭，便于自动化复测。

**发图文（笔记）：**
```bash
"$SAU" douyin upload-note --account <account_name> \
  --images /abs/1.png /abs/2.png \
  --title "图文标题" --note "图文内容" --tags 图文,测试 \
  --fill-only --hold-seconds 0
```
- 抖音图文最多 35 张，不支持 GIF。
- 抖音图文同样最多 5 个话题。

## 运行时开关

- `--headed` 有头（看页面 / 人工核对）、`--headless` 无头（默认）、`--debug` 失败时留更多调试信息。
- `--fill-only` 会强制使用有头浏览器并停在最终发布前；未给 `--hold-seconds` 时默认一直等，适合人工检查。
- 无头是该旧CLI的默认行为；本Skill正式浏览器操作默认可见，显式 `--headed` 或附着现有可见页面。

## ⚠️ 安全

- 上传走真实创作者中心。发布前把 标题/简介/标签/封面/视频 与用户确认。
- 默认 `manual-submit` 场景下必须带 `--fill-only`，让页面停在最终发布前。
- 只有用户明确授权机器点击最终“发布/定时发布”（`agent-submit`）时，才允许不带 `--fill-only` 执行上传命令；底层 CLI 还要求同一条命令显式设置 `SAU_DOUYIN_ALLOW_SUBMIT=1`。
- 测试阶段、测试号 `测试号_抖音`、或用户说“不要点击发布”时，绝不设置 `SAU_DOUYIN_ALLOW_SUBMIT=1`。
- check 失效 / 报 cookie missing or expired → 先核对错误来自脚本凭据还是实际正式页面；确认掉线后按共用恢复顺序处理，不直接要求用户重做登录。

## 发布包前置（上传前硬门）

进入抖音创作者中心前，必须先完成发布包：

1. 核对 `content-package-create` 交付的同 item `core_brief.md`。
2. 核对按 `assets/templates/publish_douyin.md` 制作的 `publish_<account>.md`，字段至少包含 `caption`、`tags`、素材路径和封面路径；缺失时回到内容包制作 Skill。
3. 运行单文件校验：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/publish-prep/check.py <publish_file> --platform douyin
```

4. 如果同一 item 还要发其他平台，再运行集合校验：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/publish-prep/check_bundle.py <item_dir>
```

缺字幕、封面、关键帧或剪辑成片时，先回发布包生成阶段补齐；不要把素材准备当成可选项跳过。

## 当前编辑页修复与提交检查（2026-09-16 real replay）

- 正文、来源、话题分开映射；正文保留空行。不得把 source_credit 和普通 #关键词拼接后当成填写完成。
- 话题逐个输入并选择精确联想项，最多 5 个；DOM 可核验 data-mention 实体的数量和名称。
- 外部转载用“自主声明 → 内容为转载信息 → 取材站外”；该声明仅显示站外，不等于完整作者署名；原作者与链接另存台账。
- 封面必须实际上传并保存，分别检查 3:4 竖封面和 4:3 横封面，记录裁切差异。
- 日期时间输入后在面板外空白处核对；再次点击已选中“定时发布”会重置默认时间。必要时使用面板选择小时和分钟。
- 用户已授权提交时，按已确认的跨平台时间提交；记录提交成功与定时公开状态的区别。只关闭成功的当前任务页，每轮为全部未完成平台重设保留标记。

## 执行路径与验证范围

读取 `_execution-quality.md`；网页可完整执行，也可在脚本后补救，受同一质量门和最新提交权限约束。2026-09-16 的正文、5话题、转载声明、双封面和定时提交通过人工辅助网页 real replay，未执行视频发布CLI，不能据此宣称CLI验证通过。当前发布包已有明确授权时不重复逐项索要确认。

### 2026-09-17 正式账号填表测试补充

- 当前项目账号以项目 `account.yaml` 为准。咪咪电视机运营项目使用账号slot `mimi_tv`，页面核对“猫猫电视机 / dyc9zv5r5jd4”，不要套用上文 assistant_zh 项目的张和白名单。
- Cookie 请求头可能含原始 JSON 值；导入器现逐条解析，保留值内等号，凭据文件权限0600，不输出值。导入成功不等于已登录。
- 登录检查增加 `sau douyin check --account mimi_tv --headed`。检查等待发布控件加载，不能把SPA跳转或通用协议页脚认作退出登录；无头结果与可见浏览器不一致时，记录差异并核对实际账号。
- 视频新增 `--declaration '内容为转载信息'`，用原生“取材站外”完成转载声明。声明失败应停住，不能默默继续。
- 测试必须 `--fill-only --hold-seconds 0`，绝不设置 `SAU_DOUYIN_ALLOW_SUBMIT=1`。视频填表异常现在也保留页面供补救；不要Ctrl-C或结束进程，否则浏览器生命周期结束可能丢失现场。
- 维护时可显式设置 `SAU_DOUYIN_CDP_PORT=<空闲本地端口>`，供原页面检查；普通发布无需设置，不得暴露到远程网络。

### 2026-09-17 本轮结果与维护限制

本轮正式账号已获授权做 fill-only，但未获提交权限，未点击发布。真实验证与改动范围如下：

- 登录、标题、正文、首次5个原生话题：真实页面通过。正文一次 insert_text 会压缩空行，现改用逐行输入+Enter生成段落；空行已在真实页面核对。
- 重填正文会清掉已有话题，必须重新选择并复核。本轮重填后联想连续10/30/60秒未返回，脚本删除临时#文本后停止；**最终页面没有话题**，不得沿用首次通过结论。尚不能断言是网络还是编辑器触发机制导致，后续需调查原生“添加话题”入口。
- 新版封面窗口使用 dy-creator-content-modal，输入框在可见semi-upload内；两种比例通过顶部step切换。已修正定位。载入编辑器不等于保存；按钮未启用不得点击，完成后必须等弹窗关闭。本轮实际显示图片，但平台报“保存封面失败”，最终封面为空。新增等待/禁用按钮保护尚未完成成功保存的real replay。
- 转载声明修正为点击semi-radio外层（文字可能pointer-events:none），可接续已打开的声明弹窗；“内容为转载信息 → 取材站外 → 确定”真实通过。
- 定时真实填入2026-09-18 17:00，并在点击面板外后再次核对值；这是测试字段，**没有创建定时发布任务**。后续执行必须重新计算有效未来时间，不复制测试日期。
- 视频首次38%时失败，原页一次重新选文件后长期0%解析，未完成上传验证。新增等待上限600秒、失败优先于“重新上传”完成标记、异常传播及fill-only留页；新增保护为logic/contract验证，不能声称已解决平台上传失败。
- 原始CLI已在运行时，磁盘上的修复不会自动替换其代码；本轮补救是复用同一页面运行更新后的函数。不要启动第二次全量上传，也不要结束持有现场的原进程。
- 页面质量检查用实际最终状态：正文空行、原生话题实体、封面缩略图、声明、定时失焦后的值、视频完成状态。full_page截图可能被固定导航遮挡，不能单凭一张长图称完整覆盖；可配合分区域截图/DOM读数。浏览器工具安全策略校验不可用时停止接管，不用其它通道绕过。

验证：32项logic/contract测试通过（12项抖音相关+20项CLI），语法和diff检查通过。real replay只覆盖上述部分字段；完整E2E和product acceptance未通过。保留正式账号页供人工检查，禁止提交。

后续脚本修复已落入正式uploader：精确话题匹配及原生实体核验、选择话题后的输入焦点、封面文件输入的非负索引、明确比例续做和保存失败停止、编辑页等待上限。9项本地浏览器控件回归通过，属于logic/contract；真实重放仍未完成，上传/封面/话题全流程仍不得标稳定。代码与验证说明见 `tools/feedback/2026-06-22_douyin-publish_登录态无效且缺少填表模式.md` 的2026-09-17续轮记录。


2026-09-17 维护补充：当前三平台视频包的菜单、上传、封面恢复按 [执行器固化说明](../../../engines/platform-video/README.md#2026-09-17-网页补救固化) 执行；代码已更新，真实新一轮验证尚未完成。
