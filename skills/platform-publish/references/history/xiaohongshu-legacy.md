> 历史归档（2026-10-22）：以下为迁移前原文，仅供追溯。旧 CLI、独立配置、Cookie 恢复和远端流程均未启用，不可照抄执行。当前执行入口为上一级同名平台 reference 与 `_local-chrome.md`。原文中的相对路径按迁移前位置理解。

# 小红书发布统一入口

按两层执行：先确定承担上传的电脑，再由脚本驱动该电脑上的可见浏览器。脚本负责逐步操作，Agent通过字段与画面验收，浏览器负责原页补救。2026-10-03的“鼠标键盘先做、脚本仅辅助”默认已被替换。

- 账号、浏览器选择、Cookie原位恢复与扫码顺序：[账号与会话](_accounts-and-sessions.md)。
- 远程电脑、SSH授权、素材交接与远端路径：[发布机工作流](_remote-publishing.md)。
- 操作分工、提交前检查与页面保留：[执行与质量](_execution-quality.md)。
- 上传、登录、控件等具体故障：[故障速查](xiaohongshu-faq.md)。

## 阅读导航

- 账号选择与现场证据：所有类型必读。
- Markdown卡片图文 / 原生长文 / 图文 / 视频：只读本次类型。
- 工具与远程连接、原位维护命令：运行命令或接回已填页面前读取。

## 当前逐条流程

1. 核对最新提交权限、发布包与发布机；同名设备、已连接SSH或Apple账号相同，都不能替代平台账号核对。
2. 正式优先复用已登录的可见浏览器；确认掉线后，有合适授权Cookie就在本次选定正式profile恢复并读回创作后台身份，需要短信/扫码再请负责人完成。测试使用独立测试profile和测试Cookie。不要把电脑连接失败报告成平台账号掉线。
3. 用脚本在真实网页执行上传和字段步骤；每步读回进度、正文段落、原生话题、封面、来源/声明和完整排期。网络请求由发布机浏览器发起，不使用直接投稿API。
4. Agent检查首屏、全页、字段清单与实际封面效果。脚本未覆盖或控件变化时原页补救；不重跑完整上传，不把脚本退出码当平台成功。
5. 测试/只填表到此保留，不点击发布或定时发布，也不自动保存草稿。正式提交只在质量通过且当前仍有授权时独立执行；结果未知先查稿件去重。

一个视频测试号的提交前通过不覆盖其他账号、图文/长文、其他平台、最终提交或长期稳定性。当前双Mac GG验证边界在 `_remote-publishing.md`，正式远程执行器仍有连接/路径/恢复适配缺口。

## 内容类型声明默认值

小红书所有内容形态在「添加内容类型声明」中，默认选择「虚构演绎，仅供娱乐」。这是负责人已确认的发布偏好，不重复询问；按完整选项文字定位，当前它是第一项，但不把选项序号当作永久规则。不要仅因封面或插画由 AI 制作而自动改选「笔记含AI合成内容」。本次指令明确指定其它声明时，以最新指令为准。

内容类型声明与原创声明、来源记录分别核对；默认值不代表原创或权利清理。选完后关闭下拉框，再操作定时等键盘输入，失焦读回最终选项，防止输入过程中意外切换声明。已提交稿件不因默认值更新而回改。

## 可复用工具与边界

- Python CLI：`/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py`
- 视频分步执行器：[platform-video README](../../../engines/platform-video/README.md)，`run`填表、`submit`单独验收授权；目前本机支持不能直接等同远程支持。
- 卡片图片由 `content-package-create` 在本地生成；本发布流程只接收并核对已确认文件。

使用当前实际可用工具与已核实的副作用。优先复用已验证步骤；整条CLI只有在不会重置现存页面、能够停在提交前且本次环境适配时才用。下面CLI示例按**引擎与浏览器同机**理解；远程会话先看文末“指定账号与远程Chrome”，不能直接照搬本机路径。

不得使用抓取/互动工具投稿、直接接口投稿、无人值守批量提交或自动重试试发。保留已提交定时稿，结果不明先查重。

## 账号选择（所有类型统一前置步骤）

按共用规则解析本次指令、作品账号映射与项目 `account.yaml`；浏览器profile只是可调整的环境偏好，不能反推内容目标账号。没有可靠账号依据时，再用下列命令列出已配置的账号；列出账号不等于核实浏览器已登录，更不等于核实登录的是目标账号：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py \
  list-accounts
```

根据返回 `count`：
- **0 个命名账号**：不能仅凭此推断默认账号就是发布目标；回到项目配置或询问目标账号。
- **1 个或多个命名账号**：按已明确的目标匹配slot；没有可靠匹配才询问。不能因只有一个候选就覆盖作品目标，也不重复询问已确定的账号。

目标账号仅按任务要求变更；执行环境可以按共用规则调整。Cookie/扫码恢复落在本次选定profile，现存页面优先续做。

---

## 发布页现场证据（所有类型强制）

使用CLI填表时，`fill-publish` / `fill-publish-video` 成功不等于可以直接发布。每次填表成功后，CLI JSON 必须返回并由 agent 检查这三项；逐步脚本或浏览器补救也须提供等价的原页截图与字段证据：

- `pre_publish_screenshot`：当前视口截图，用来快速看首屏是否正确。
- `pre_publish_full_screenshot`：全页截图，用来看首屏外的封面、原创声明、可见范围和活动区域。
- `pre_publish_audit_json`：发布前 DOM 审计 JSON，用来看标题、正文摘要、素材状态、发布按钮和活动关联。

审计时必须明确向用户说明：

- 当前是否关联活动。
- 活动名称是什么；例如页面自动带出 `AI新手村` 时，不能静默保留。
- 是否建议保留。默认更稳的判断是：自动关联活动后，先研究关联是否准确；不能因为页面自动带出就直接认为应保留。

如果成功 JSON 缺少上述任一字段，或截图 / 审计 JSON 读不到，按流程失败处理：停在当前页面，补截图 / 审计，不得点击发布。

失败时也必须保留现场：`fill-publish` / `fill-publish-video` 返回失败时应包含 `page_preserved: true` 和 `failure_screenshot`。看到失败后先检查当前 Chrome 发布页，不要直接关闭页面、重跑脚本或减少素材。

所有 `contenteditable` 正文输入必须使用引擎里的 DOM Range 清空逻辑；不得退回 `Ctrl+A` / `Command+A` + 删除。macOS 下快捷键清空可能落到整页或失效，二次填表会造成正文重复。

---

## 卡片图文交接

卡片图片由 [`content-package-create` 的卡片制作说明](../../content-package-create/references/xiaohongshu-cards.md)在本地生成。发布时只核对已确认的图片顺序、账号、标题、正文和封面效果，不在发布页临时生成新卡片。

---

## 内容类型判断

按优先级路由：

0. 已有 `publish_<account>.md` + `assets/xhs_cards/card_*.png` / `card_*.jpg`，或用户明确说这些是发布包生成阶段 / `markdown-to-cards` 生成并确认过的卡片图 → **Markdown 卡片图文流程**（走 `fill-publish`，不要走小红书原生长文）
1. 用户明确说"长文" → **长文流程**
2. 用户明确说"视频" / 提供 `.mp4` / `.mov` / `.avi` 路径 → **视频流程**
3. 用户明确说"图文" / 提供图片路径或图片 URL → **图文流程**
4. 提供 `.md` 文件路径或含 frontmatter（`---`）的 Markdown 内容 → **长文流程**
5. 不明确 → 用 `AskUserQuestion` 询问（长文 / 图文 / 视频）

---

## Markdown 卡片图文流程（发布包产物）

适用场景：内容已经通过 `content-package-create` / `markdown-to-cards` 形成发布包，目录里有：

- `publish_<account>.md`：frontmatter 含 `title` / `description` / `keywords`
- `assets/xhs_cards/card_00_cover.png` 和后续 `card_*.png` / `card_*.jpg`
- 用户已经确认平台标题、封面标题、发布页正文和卡片图

这种情况是**图文发布**，不是小红书原生长文。不要调用 `long-article` / `next-step`，否则会进入小红书原生长文模板，丢掉已确认的 Markdown 卡片视觉。

### 脚本操作与浏览器验收

在可见浏览器的图文发布页按已确认的图片顺序、标题、分段正文和话题填写，逐张检查上传状态，并按上面的浏览器流程核验。提交前确认图片重开仍可加载；需要用户检查时停在当前页。

### 同机CLI填表入口

同机完整填表可用下面的 `fill-publish`；已上传页只补缺失步骤。其历史上传助手可能自动重置/重试（见FAQ），未确认能保留当前页时，不调用整条入口，改用已验证的逐步浏览器操作。

1. 用 `extract_frontmatter.py` 从 `publish_<account>.md` 提取：
   - `files.title_file` → `fill-publish --title-file`
   - `files.desc_file` → `fill-publish --content-file`
   - `keywords` → `--tags`
2. 图片按本地已确认卡片顺序传入 `--images`：
   - `card_00_cover.png`
   - `card_01.png`
   - `card_02.png` / 上传修复后的 `card_02_upload.jpg`
   - 后续卡片
   - 使用已确认卡片；只有平台失败或兼容性检查给出证据时才准备等比例高质量JPEG副本，保留原图并检查画面。
3. 填写图文表单：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py \
  --account <ACCOUNT> fill-publish \
  --title-file "<files.title_file>" \
  --content-file "<files.desc_file>" \
  --images "<card_00_cover>" "<card_01>" "<card_02>" "<card_03>" \
  --tags "<keyword_1>" "<keyword_2>"
# 仅本条确认原创时添加 --original
```

4. 发布前必须检查页面上传状态和审计产物：
   - 图片 slot 数量 = 本次传入图片数量
   - 每个 slot 都有图片预览
   - 页面没有"上传失败"、失败态 class、红色错误提示
   - 标题、正文、话题、原创声明正确
   - **必须检查三项成功产物**：使用 `fill-publish` JSON 返回的 `pre_publish_screenshot`、`pre_publish_full_screenshot`、`pre_publish_audit_json`；只看 CLI 日志或只看一张首屏截图不够。
   - **必须审计活动关联**：从截图和 `pre_publish_audit_json` 里说明当前是否关联活动、活动名称、是否建议保留；自动带出的活动默认先研究关联准确性。
   - **CLI 的 `"success": true` 不等于上传成功**：如果页面文字含"上传失败"，或 DOM 里出现 `.mask.failed`，必须停止，不得点击发布。
5. 只有用户已授权 `agent-submit`，且第 4 步全部通过，才允许调用 `click-publish`。正式点击前再次截图/DOM 检查；截图和检查结果要在发布记录或对话里说明。
6. 到点公开核验属于后续任务，不阻塞本轮接受提交后的收尾；只有本次任务包含后续核验时，再按可访问的公开主页、笔记详情或后台状态确认：
   - 新笔记标题正确
   - 正文和话题正确
   - `imageList` 数量 = 本次发布图片数量
   - 再把 `note_url`、`published_at` 回填到本地 `published.md` / `content_index.yaml`

### 上传失败处理

- 第一次看到某张图片上传失败时，先保留当前页面，不要关闭重来。
- 不能因为上传失败减少卡片数量；卡片数量由内容质量决定，发布链路必须适配内容。
- PNG 反复失败时，把同画面重新编码成高质量 JPG 上传副本后重传，例如：

```bash
sips -s format jpeg -s formatOptions 95 "<card_png>" --out "<card_upload.jpg>"
```

- 大尺寸卡片可生成等比例上传副本，例如宽度 1080、质量 95；这只是上传格式适配，不改正文、不裁切、不减少卡片，必须截图确认文字可读。
- 旧引擎包含上传失败后重置发布页并重试的机制；当前脚本+浏览器流程不套用该机制。失败时保留原页，先辨认哪张图片失败及页面是否可局部恢复，不自动重置或连续试发。
- 若经单独确认使用旧引擎辅助上传，其失败/超时证据可能保存在 `/tmp/xhs_upload_*.png` 和 `/tmp/xhs_upload_*.json`；不能把引擎重试结果直接当作平台已保存证据。
- 重传或使用上传副本后，发布记录里写明使用了哪个上传目录或替代文件。
- 在所有图片恢复成功前，禁止点击发布。
- 当前引擎会在 `fill-publish`、`publish` / `click-publish` 前保存发布页截图并检查失败态；如果仍然看到页面异常，以页面截图为准，不能相信日志。

---

## 长文发布流程

原生长文使用“写长文”编辑器；已有Markdown卡片成品时走前面的图文流程，不为了脚本命令齐全而重新转成长文。旧的“先生成卡片，再作为原生长文下一步图片”的通用默认已淘汰。

1. 从已确认发布包提取标题、长文正文、发布页描述和话题。可用：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/extract_frontmatter.py \
  "<publish_file>" --save-dir /tmp
```

`valid=false`时先修缺字段；不要把提取器成功当页面填写成功。

2. 在已确认账号的同机会话中，已有命令可以分步填写：

```bash
$XHS_PY $XHS_CLI --account <ACCOUNT> long-article \
  --title-file '<title_file>' --content-file '<body_file>'
$XHS_PY $XHS_CLI --account <ACCOUNT> next-step \
  --content-file '<desc_file>' --topics '<topic1>' '<topic2>'
```

`XHS_PY`/`XHS_CLI`为上方实际引擎路径。选择模板及下一步需检查当前页面，不能仅凭日志连续推进；`--images`仅在本条明确需要替换封面图片时提供已确认文件，`--original`仅用于确认原创的素材。

3. 核对描述、原生话题、封面与权限，并保存三项现场证据。需要补字段或模板控件不适配时在原页操作。
4. 测试停在提交前；正式提交按统一质量门和最新授权单独执行。收尾只记录本项目发布状态，不能自动发送飞书消息、删除制作物料或创建后续定时任务。

## 登录与只打开页面的检查

已知账号可用 `--account <ACCOUNT> check-login` 检查本机会话；需扫码时显示平台二维码并等待负责人验证，`wait-login`只负责等待，不代替身份确认。远程profile身份以实际页面读回为准，不以本地账号列表代替。

只验证发布入口、尚未上传且没有待保留编辑页时，可用：

```bash
$XHS_PY $XHS_CLI --account <ACCOUNT> open-publish-page \
  --kind video --screenshot-out '<evidence.png>'
```

`--kind`可选`note`、`video`、`long-article`。该探针可能关闭自己打开的页；不要用它接管已有上传现场。页面可达不代表上传或发布验证通过。

---

## 图文发布流程

默认由脚本在可见图文页逐条上传填写，再由Agent检查呈现。以下是同机填表命令；远程和现存页遵守上方工具边界。

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

**超长处理（禁止机械截断）**：保留当前发布页，交给 `content-package-create` 根据原标题核心含义重写并更新发布包，再回原页填写。目标 19–20 单位；不要只改页面、不改已交付文件。

### 正文格式

- 正文保留分段，简体中文；关键词单独传入话题步骤，在正文末尾选择平台原生话题，不将普通井号文本混入正文文件。

### 用户确认

沿用会话已确认的标题、正文、图片；缺少内容确认时再通过对话展示并确认，不重复索要已具备的授权。注意：需要用户对齐的图片/封面/卡片必须在对话中用 Markdown 图片直接渲染，不能只写文件路径或"使用某张封面"。

### 写入临时文件

将标题和正文写入 UTF-8 文本文件，不在命令行参数中内联中文。

### 同机CLI填表入口

```bash
# 步骤 1: 填写图文表单
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py \
  --account <ACCOUNT> fill-publish \
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
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py \
  --account <ACCOUNT> save-draft
```

填写完成先由Agent核对实际字段与画面。测试保留原页；用户要求自行提交时才交接按钮，已有agent-submit授权则按质量门独立提交，不把技术检查默认转交用户。

> ⚠️ 仅填表分支不得调用 `click-publish` 或 `publish`。最终点击由本次 `manual-submit` / `agent-submit` 契约决定。

> ⚠️ 用户要求取消时，先按用户意图判断是否保留草稿；需要保留且平台可保存时在当前页面保存并核对结果，不因取消就直接关闭未保存的 tab。已确认同机会话可用 `save-draft`，执行后核对保存结果。

---

## 视频发布流程

脚本驱动可见视频页逐步执行，Agent核对视频处理、字段和封面。远程场景先落实发布机文件路径与精确会话；本机CLI不是通用远程启动器。

**输入需求**：标题 + 正文 + 视频（本地绝对路径，`.mp4`/`.mov` 等）+ 封面图（本地绝对路径，`.jpg`/`.png` 等）

### 稳定性门槛与发布顺序

- 小红书视频链路不稳定时，只能使用 `测试号` 做复现和修复；在本次使用的发布机与执行方式下，用 `测试号` 完成真实素材的「视频上传进度推进并完成 → 标签联想全部插入 → 封面上传通过 → 发布按钮可点击」前，禁止对真实账号自动点击最终发布按钮。
- 多条待发布笔记必须逐条处理：一次只处理一条视频；填表完成记“待提交”，平台接受提交后才记“已提交/已定时”。该条到达本次授权停止点并留证后，再进入下一条。禁止写后台循环一次性提交所有真实账号笔记，禁止同时打开多条发布页并行上传，禁止“先把所有笔记都开始上传再回来检查”。
- 批量计划只是队列，不是并发发布许可。即使用户说"这个账号其他笔记都发掉"，也要按队列一条一条跑，并在每条失败时停止后续真实发布，先诊断失败原因。

### 必做约束

- 没有视频不得发布；没有封面图也不得发布。视频和封面图都是必填。
- 标题长度 ≤ 20（规则同图文）。
- 发布前沿用已确认的标题、正文、视频和封面；缺少确认的才向用户展示。封面必须在对话中直接发图给用户看；视频至少给出可打开的绝对路径/预览，不能只引用发布包文件名。
- 所有路径必须绝对路径。

### 同机CLI填表入口

```bash
# 步骤 1: 填写视频表单
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py \
  --account <ACCOUNT> fill-publish-video \
  --title-file /tmp/xhs_title.txt \
  --content-file /tmp/xhs_content.txt \
  --video "/abs/path/video.mp4" \
  --cover "/abs/path/cover.png" \
  [--tags "标签1" "标签2"] \
  [--visibility "公开可见"] \
  [--no-original]
```

说明：
- `--video` 会自动解析软链到真实文件路径。
- `--cover` 必填；会在同一发布页完成「修改封面 → 上传图片 → 确定」，并等待最终发布按钮可点击后才返回成功；不再调用临时外挂脚本。
- 视频默认声明原创；如果素材不是原创，显式加 `--no-original`。
- 成功 JSON 必须包含 `pre_publish_screenshot`、`pre_publish_full_screenshot`、`pre_publish_audit_json`。发布前必须同时检查首屏截图、全页截图和审计 JSON，确认视频、封面、标题、正文、话题、原创声明、发布按钮可点击状态都正确。
- 如果 `pre_publish_audit_json` 显示页面自动关联了活动，先向用户明确：当前关联了哪个活动、是否与内容匹配、建议保留还是取消。不能因为页面自动带出活动就静默发布。
- 话题联想失败时，保留当前发布页并按 `xiaohongshu-faq.md #10` 处理：先读取正文编辑器内已有 `a.tiptap-topic`，只对缺失话题追加重试；已经关联成功的话题必须跳过，不要整组重插导致重复。

填写完成后由Agent完成三项证据检查，报告实际阶段与未验证项；测试保留原页，正式提交单独判断。

> ⚠️ 填表预览流程禁止调用 `click-publish`。只有用户明确授权“正式发布/定时发布”、质量检查通过时才可提交；在原会话中将最终提交作为独立动作执行，不运行填表提交合一的入口。

> ⚠️ 用户要求取消时，先按用户意图判断是否保留草稿；需要保留且平台可保存时在当前页面保存并核对结果。已确认同机会话可用 `save-draft`，执行后核对保存结果。

### 已淘汰的执行默认

| 旧做法 | 当前处理 |
|---|---|
| 屏幕共享逐项鼠标键盘先做，脚本只作最后补救 | 脚本操作可见浏览器为主，Agent检查，屏幕共享局部补救 |
| `publish-video`一键从上传到最终提交 | 不再作为本Skill执行入口；使用分步填写、验收、独立提交，避免跳过质量门 |
| 提交后固定等待便宣布成功 | 等平台实际接受回执；未知结果先查重 |
| 取消/测试结束强制`save-draft` | 按用户明确要求决定是否保存；没有保存授权则保留原页 |
| 长文完成自动发消息、加复盘定时任务 | 仅在用户另有明确授权时执行 |

旧代码可能仍保留这些命令，不表示当前工作流允许调用。保留本条发布页、逐条处理、原生组件和最新提交权限继续有效。

---

## CLI 子命令总表

| 子命令 | 用途 | 适用流程 |
|--------|------|---------|
| `list-accounts` | 获取账号列表 | 共用（前置） |
| `check-login` | 检查登录状态 | 长文 |
| `wait-login` | 等待扫码登录 | 长文 |
| `long-article` | 填写长文编辑器 | 长文 |
| `next-step` | 进入发布页填描述+图片+话题 | 长文 |
| `click-publish` | 独立点击发布；所有类型均需质量通过及最新提交授权 | 长文/共用 |
| `fill-publish` | 填写图文表单 | 图文 |
| `fill-publish-video` | 填写视频表单 | 视频 |
| `save-draft` | 保存草稿 | 图文/视频 |

---

## 指定账号与远程Chrome

同机账号使用真实slot，例如 `--account <ACCOUNT>`；不能省略账号后默认落到测试号或个人号。

远程按 [_remote-publishing.md](_remote-publishing.md) 建立加密控制通道，调试接口留在发布机loopback。**废弃直接使用 `--host <局域网IP> --port 9222` 暴露/连接未认证Chrome端口的旧示例。**

当前CLI的账号处理会决定端口，连接函数还可能先启动本机Chrome；文件检查也按脚本主机执行。因此不能只给CLI换一个`--host`便宣称远程可用。先检查实际连接逻辑、路径适配及精确target绑定，使用已验证的浏览器分步能力。没有适配时如实标明能力缺口，保留原页；不能从正式账号试发验证。运行配置归项目维护，不能硬编码本次设备IP、Cookie或临时脚本路径到共享Skill。

---

## 处理输出

- **Exit code 0**：命令已返回，仍须结合 JSON 和平台页面判断阶段，不能直接认定发布成功。
  - `fill-publish` / `fill-publish-video` 成功必须同时包含 `pre_publish_screenshot`、`pre_publish_full_screenshot`、`pre_publish_audit_json`。
  - 正式点击发布前必须读这些产物；如果缺字段、路径不存在或页面证据不一致，按失败处理。
- **Exit code 1**：登录检查未通过，先核对实际profile和可用授权登录态；需要本人认证时再请求扫码（参考 xhs-auth）。
- **Exit code 2**：错误，报告 JSON 中的 `error` 字段。
  - `fill-publish` / `fill-publish-video` 失败必须优先查看 `page_preserved` 和 `failure_screenshot`。若 `page_preserved: true`，当前 Chrome 页面就是待诊断现场，不得先关闭重来。

---

## 失败处理

> 更细的踩坑速查见 `references/xiaohongshu-faq.md`。

| 情况 | 处理 |
|------|------|
| 视频/图片传不上去、上传卡死超时 | 先确认素材路径、文件大小、浏览器登录态和页面错误提示；必须保留当前页面，查看 `failure_screenshot` / 当前 Chrome 现场，不要直接宣称已发布 |
| 成功 JSON 缺少截图或审计 JSON | 停止；补截图 / 审计后再进入人工确认，不得点击发布 |
| 页面自动关联活动 | 读 `pre_publish_audit_json` 和全页截图，向用户说明活动名称和保留建议；默认先研究关联是否准确 |
| 上传报文件错误/传空 | 路径若是软链先 `realpath` 解析成真实文件再传（faq #2） |
| 登录失败 | 先区分SSH连接、浏览器profile及平台身份；检查已有授权Cookie，确需平台认证才请求扫码 |
| 图片下载失败 | 提示更换图片 URL 或改用本地图片 |
| 标题过长 | 保留原页，交给 `content-package-create` 重写、校验并更新发布包，再继续填写 |
| 视频处理超时 | 保留页面查看当前进度/错误；不因等待超时自动重传 |
| 长文 Step 4 未到发布页 | 失败，不宣称"测试通过"，报告给用户 |
| 用户取消或要求不发布 | 立即停止提交；按是否明确要求保存决定草稿动作，保留未保存页 |
| `extract_frontmatter.py` valid=false | 停止执行，将 errors 报告给用户 |

## 原页补救与字段检查

脚本和浏览器补救操作同一个真实页面，账号与权限沿用当前项目和会话。下面是已验证的字段规则，不代表所有整条CLI入口稳定。
- 正文按段落输入；关键词逐个选择精确话题联想，再检查真实话题实体数量/名称（本次观察为 a.tiptap-topic）。
- `source.url` 与 `copy.source_credit` 只用于核对来源。仅当负责人明确要求本条关联原笔记时，才用“引用笔记 → 他人笔记”搜索原链接并核对作者/标题；未要求时不打开或确认引用组件。来源署名不拼进正文，平台必填的转载/来源字段仍按要求填写。
- 文件选择接口受权限限制时可用系统原生文件框；确认封面保存和比例预览后再进入质量门。
- 平台接受提交即为流程成功；尚未到点公开单独记录。原生页面/控件会变，选择器只是本次观察。

### 发布页原位维护命令（2026-09-16）

已上传视频或填好正文时，优先补救当前页面，避免重新执行完整 fill 丢失现场。以下两个命令不会点击最终发布，也不会关闭页面：

```bash
# target-id 必须来自当前账号 Chrome 的真实页面清单，不猜、不跨账号复用。
$XHS_PY $XHS_CLI --account 测试号 inspect-publish --target-id '<当前发布页target-id>'
$XHS_PY $XHS_CLI --account 测试号 set-video-cover --target-id '<当前发布页target-id>' --cover '/绝对路径/cover.png'
```

`XHS_PY` 为引擎 `.venv/bin/python`，`XHS_CLI` 为引擎 `scripts/cli.py`。两条命令要求精确现存发布页，目标失效就报错，不新开空白页、不回退到其它页。成功返回 `submitted:false`、`page_preserved:true` 和审计证据；这只是步骤完成，不等于公开发布或质量门通过。

新版封面链路：悬停真实缩略图 → 编辑封面 → 原生图片 input → 等待平台上传完成（最多180秒）→ 按上传时读取的原图尺寸切换3:4/1:1/4:3 → 编辑器“完成” → 等待弹窗关闭（最多180秒）。已有自定义封面时使用编辑器自带清除控件替换；正在上传则保留现场，不并行追加文件。非标准比例会选最接近的原生比例，仍需截图检查裁切。

审计约束：`activity.associated` 是 true / false / null 三态；null 表示控件不认识，必须网页补查。推荐卡的“关联”按钮不代表已关联；“活动中心”等导航不作为证据。正文 `content_text` 保留换行，发布按钮读取原生组件属性。`open_dialogs` 非空时先解决或交接弹窗。

全页截图会临时展开内部滚动区域、把吸底发布栏移回文档流，截图后恢复样式和滚动位置；因此它是表单内容证据，原始布局同时看普通截图。截图失败返回空路径，不得当作已有证据。人工/agent 仍须核对封面文字、必填来源字段、可选关联、话题、定时及未关联活动，禁止凭 `success:true` 直接提交。


三平台视频包的现有菜单、上传与封面能力见 [执行器说明](../../../engines/platform-video/README.md)。2026-10-05远程GG的逐步真实验证补充见 `_remote-publishing.md`；不把这次测试升级为整条CLI、其他平台或最终提交E2E通过。
