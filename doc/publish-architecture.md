# 发布线架构

> 最后更新：2026-10-22
> 适用范围：`content-package-create` 内容包制作与 `Agent-Publish` 平台执行；引擎能力以各自README为准

## 内容制作与发布分工

`content-package-create` 根据真实素材制作 `core_brief.md`、标题、正文、封面文案、关键词与各账号 `publish_<account>.md`，完成本地校验后停止。`Agent-Publish` 接收已确认的包，复核账号和字段，操作平台页面，并按本次授权停在待提交页或提交。用户同时要求制作和发布时，按这两个入口顺序执行；只要内容、不要求上传时，不进入发布入口。

`content-production-prep` 负责上游素材、脚本、成片和确认版本；各账号发布字段以 `publish_<account>.md` 为唯一可编辑真源，title.txt/description.txt/tags.txt 如需导出只作派生物，改包后同步重导。底层发布包模板、规则与封面 kit 暂保留原路径，避免破坏现有引擎、项目合同和历史文件；路径归属不改变两个 Skill 的行为边界。

发布入口正式名称为 `Agent-Publish`（2026-10-07 用户指定），取代旧触发名 `platform-publish` / `content-platform-publish`。registry、Skill声明和Claude/Codex安装名一致；源目录仍为 `skills/platform-publish/`，已有素材和相对链接继续使用该路径。旧名称只保留在迁移历史和registry的废弃入口记录中，不保留第二份可触发Skill。

## 当前执行路线：本机日常Chrome

后续所有平台发布固定在当前电脑，直接复用负责人已打开并登录的日常Chrome。Agent在这个已有浏览器里打开平台、检查账号、上传和填表，按最新权限停在检查页或提交。没有登录就保留原页，请本人在同一Chrome登录；不运行check-login，不导Cookie，不启用其它电脑或脚本独立配置。

浏览器入口通过当前Chrome扩展发现，任务开始锁定真实实例/profile。新增`scripts/guard_existing_chrome.py`作为发布入口hook，接管、上传/写入、提交前各检查一次；目录、实例、连接来源或机器不符就返回明确错误并退出2。它只验证当前入口提供的真实连接记录，平台登录和内容质量另看页面。它不是能拦截任意shell工具的宿主全局hook。

活动Skill、七个平台reference、能力声明与默认提示都沿同一入口。旧远程、Cookie和独立CLI命令归档到`references/history/`，只供维护查阅，不能自动降级。历史引擎仍保留自身能力，当前发布Skill不调用这些启动或直传路径。

接管绑定的JSON格式、实际调用与页面保护在`references/_local-chrome.md`；账号核验及人工登录在`_accounts-and-sessions.md`；质量门和原页补救在`_execution-quality.md`。浏览器ID来自当次清单，不永久硬编码；同轮不能静默换实例。控制连接失败与平台掉线分开，正常网页SSO可在同一profile可见导航完成。

用户只要求验证时只读页面，不上传、填稿、建草稿或提交；已接受稿件不用于重复投稿验收。hook的logic/contract、真实Chrome接管、平台身份、上传与最终发布分别记录，不能互相替代。

## 保留的公众号API能力（当前非活动发布路线）

公众号现在有两条官方 API 路径：普通文章把 Markdown 排成 HTML，原生贴图（微信称为 `newspic` 图片消息）把有序图片与纯文本说明直接放进草稿箱。贴图首张图片就是封面，最多20张，不套普通文章主题或独立封面模板。小助理继续使用原有 `wxp-ai` 账号配置。

内容包入口继续负责图片、顺序、标题和说明；当前发布按 `references/gongzhonghao.md` 使用已有Chrome网页。下文保留API引擎的实现与历史证据，不授权自动调用。底层入口不变：`engines/gzh-publish/src/index.ts`；新增 `src/newspic.ts` 管贴图流程，`src/wechat.ts` 管官方请求。贴图模板在 `assets/templates/publish_gongzhonghao_newspic.md`，发布包校验支持 `--form newspic`，或从 `article_type: newspic` 自动识别。

执行前检查全部图片，再依次上传永久素材、创建草稿并读回，核对原生贴图类型、标题、说明、图片顺序与评论；指定裁切时也核对裁切。大白话：不能把“上传成功”当成“草稿内容正确”。原生贴图的 `--dry-run` 输出实际输入与请求预览，不联网，不生成文章 HTML。

每个账号/发布包在 `var/gzh-publish/newspic/` 有自己的操作记录，保存素材与草稿 ID，不保存凭据。重复执行会复用原草稿；改内容则更新它。上传途中失败保留成功素材，创建结果未知先查最近60篇草稿；不能确定时用核对后的 `--draft-id` 接回，不盲目重建。草稿被删或发表不自动另建。记录路径随源文件绝对路径绑定，移动发布包或删除记录会失去关联，应按新任务而非重试判断。

默认只创建草稿。明确授权 `--publish` 才提交公开发表，并查询最后结果；返回任务 ID 是“已提交”，仍在处理则报 `publishing`，最终成功才报 `published`。官方发表权限受主体和认证限制，贴图发表需真实验证；给粉丝群发是另一动作，不能从发表授权推断。普通文章旧发表路径的最终状态查询不在本次改造范围。

验证进度（2026-10-07）：贴图离线 logic/contract 已通过；小助理真实 API replay 与草稿范围的 E2E agent loop 完成，覆盖两图创建/读回、重复复用、更新顺序、32字标题、空说明与显式1:1裁切，最后恢复原测试稿。仅使用两份永久图片素材，同一路径一直关联同一草稿。公众号后台浏览器访问被站点安全策略阻止，界面和手机 product acceptance 未完成；公开发表/群发未执行。调研、实施计划和结果见 [`plan/gongzhonghao-newspic-research.md`](plan/gongzhonghao-newspic-research.md)，实际API证据在 `var/gzh-publish/tests/20261007-wxp-ai/`。

## 现在有哪些部件

| 部件 | 路径 | 做什么 |
|---|---|---|
| 内容包入口 | `skills/content-package-create/SKILL.md` | 根据已确定内容制作并校验 core brief 和各平台发布字段 |
| 发布入口 | `skills/platform-publish/SKILL.md` | 检查已交付发布包，核对账号权限并路由到平台 reference |
| 账号与会话 | `skills/platform-publish/references/_accounts-and-sessions.md` | 管目标身份、现有Chrome归属、页面登录及本人补位 |
| 本机会话 | `skills/platform-publish/references/_local-chrome.md` | 锁定现有Chrome并运行三阶段hook；远程路线已停用 |
| 会话守卫 | `skills/platform-publish/scripts/guard_existing_chrome.py` | 对实际入口元数据检查，错环境返回PUBLISH_SESSION错误 |
| 执行与验收 | `skills/platform-publish/references/_execution-quality.md` | 脚本操作、浏览器检查、原页补救与提交停止点 |
| 全局红线 | `skills/platform-publish/references/_invariants.md` | 写死不能跨平台裁剪、不能机械截断、不能导流 CTA、不能编造 |
| 中间层说明 | `skills/content-package-create/references/_core-brief.md` | 内容包 Skill 使用的 `core_brief.md` 合同；它是不按平台压字数的“原木” |
| 素材规格 | `skills/platform-publish/assets/platform_rules.yaml` | 管每个平台标题、正文、摘要、关键词、封面的规格 |
| 上传能力 | `skills/platform-publish/assets/platform_capabilities.yaml` | 管每个平台能不能草稿、截图、停在发布前、是否可逆 |
| 发布套装 | `skills/platform-publish/assets/recipes.yaml` | 管“口播切片三平台”“长文全网”这类默认组合 |
| 模板 / prompt | `skills/platform-publish/assets/templates/`、`assets/prompts/` | 生成 `publish_<account>.md` 时用的信纸和写作规则 |
| 业务 profile | `skills/platform-publish/profiles/zh_main/keyword_pool.yaml` | 张和主号的固定关键词池；换账号时这里分出去 |
| 引擎 | `engines/publish-prep/` | 内容包 Skill 用于生成和校验；发布 Skill 只调用其校验能力 |

## 接管与登录验证

在现有Chrome直接打开平台，读取真实身份及管理/发布入口。不调用引擎页面探针或登录检查命令，因为它们可能新开自己的profile。只读验收不要求发布包，也不选择文件、填表、写草稿或重投已接受内容。无登录保留原页请本人处理；有主站登录而后台需要SSO时沿同一Chrome正常网页入口核验。

## 五阶段

| 阶段 | 干什么 | 交付物 |
|---|---|---|
| 1 收料 | 素材整理 Skill 确认源稿、已锁定内容和目标平台 | 可追溯素材 |
| 2 建内核 | 内容包 Skill 生成平台无关的 `core_brief.md` | 核心判断、标题种子、封面标题种子 |
| 3 展开包 | 内容包 Skill 为每个平台独立生成并校验 `publish_<account>.md` | 可交付的发布包 |
| 4 上传与验收 | 发布Skill核对账号/权限，hook锁定本机Chrome并原页操作和复核 | 字段/画面证据及待提交页；保存草稿仅按授权 |
| 5 提交 | 用户或 agent 按授权提交 | 发布记录 |

## 两个闸门

- 闸门 A：`core_brief.md` 生成后，定调核心判断、标题种子、封面标题种子。单平台可自动通过，但仍保留文件。
- 闸门 B：上传后、正式提交前，看各平台成品和页面截图。所有平台当前走已绑定Chrome网页；旧B站直接投稿CLI不在活动路径，网页可停在填写页。

小红书的闸门 B 现在有三份固定证据：`pre_publish_screenshot` 是当前屏幕照片，`pre_publish_full_screenshot` 是整页照片，`pre_publish_audit_json` 是页面文字和状态清单。大白话：一个看柜台当前摆放，一个看整张柜台，一个列出系统读到的标题、正文、素材、按钮和活动。

小红书如果页面自动关联活动（例如自动带出 `AI新手村`），不能静默发布。发布前要说明“有没有关联、关联了什么、是否建议保留”；默认更稳的判断是先研究关联准确性。

## 校验命令

单个平台发布包：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/publish-prep/check.py <publish_file> --platform <platform> [--form article|video]
```

同一个 item 的多平台发布包：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/publish-prep/check_bundle.py <item_dir>
```

整套工具清单：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/scripts/check-tools.py
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/scripts/sync-skills.py --dry-run
```

## 维护原则

- 改标题字数、关键词数、正文长度：先改 `platform_rules.yaml`。
- 改某个平台能不能截图、草稿、自动提交：改 `platform_capabilities.yaml`。
- 新增平台：先加规格和模板，让它能产发布包；上传能力以后再补。
- 发现上传能力缺口：发布任务里只降级并写反馈，不顺手写新引擎。
- 改发布线结构或行为：同一提交里更新本文档。

## 抖音脚本修复边界（2026-09-17）

正常发布由 `vendor/social-auto-upload/uploader/douyin_uploader/main.py` 执行，网页补救用于定位问题，修复写回正式代码。话题点击后必须读到原生标签，封面按明确比例填写且保存失败即停止；进入编辑页和上传等待均有上限，失败仍保留正式账号现场。这样可以减少填错、假成功和无限等待，但不能替代平台端真实验收。

本轮新增 `tests/test_douyin_dom_regressions.py`，用无网络的本地浏览器页面验证控件操作，属于logic/contract。正式抖音真实重放仍受浏览器工具管理员策略校验不可用阻挡；上传解析及平台封面保存失败未确认根因，完整E2E未通过。不能宣称新任务可稳定自动发布。

发布与维护的时间边界：实际发布期间脚本失败就用原页网页操控补救，不边发布边改代码或重跑测试。本轮收尾记录证据及待修问题；用户明确进入后续独立维护任务后才修改脚本并验证。网页无法补救时保留现场并请求人工补位，不以开发工作代替本轮发布。

## 视频号故障分类与声明（2026-09-23）

视频号能否发表，与登录能否跨多次任务复用分开判断。历史曾成功提交，不代表今天的登录还有效。引擎现在把页面打不开和需要扫码分开；点击后没有收到结果就记“结果未知”，先查后台，避免重复投稿。转载内容不再被自动勾成原创，原创发布需明确传 `--declare-original`。

这次只完成 21 项离线逻辑回归。猫猫电视机账号尚未绑定，真实登录、原页恢复与跨次复用仍待验证；每条命令关闭浏览器的生命周期没有在本轮改造。

## 排版编辑器（2026-10-02）

发布前可以打开 `var/publishing-style-preview/index.html` 调整公众号文章或 Markdown 卡片的排版。网页展示完整的公众号与卡片内置主题及原有精选样式，可调标题、正文、颜色和常用内容块；样张默认隐藏层级标注，需要核对时可临时显示；命名保存后可再次打开，也可导出 JSON 配置让正式排版命令使用。运行 `./engines/gzh-publish/node_modules/.bin/tsx scripts/build-publishing-style-editor.mts` 刷新网页。

编辑器里的即时预览用于选择方向，正式文章 HTML 与卡片图片仍由原有排版引擎生成。部件关系、使用命令和验证边界见 [`publishing-style-editor-architecture.md`](publishing-style-editor-architecture.md)。

字体选项另收录用户指定笔记中的 15 款日系字体。网页会显示实际载入状态；可附带的字体直接预览，受原作者再分发限制的字体通过本机安装或载入文件使用。卡片导出会拒绝缺失的字体；公众号阅读端是否保留特殊字体仍受设备和微信环境影响。

## Agent-Publish 公开发行版

公开仓库为 `bamao88/Agent-Publish`，发行范围是 Skill、通用规则和模板，不包含执行引擎、账号配置、凭据、私人素材或业务记录。公开副本使用独立 Git 历史，引用软链接解析为普通文件，本机路径改成外部工具目录变量；公众号、文章平台的私人白名单和账号人设改为使用者自行配置。

公开版源工作目录在 `var/review/agent-publish-public-export/repo/`；它是单独仓库的本地发行副本，不是共享工具库存的新 Skill，不加入 registry 或全局安装链接。源工作流仍使用 `skills/platform-publish/`，不能把公开版直接覆盖回本机源文件。导出范围、检查与结果见 [`plan/agent-publish-public-export.md`](plan/agent-publish-public-export.md)。公开仓库自己的 `docs/architecture.md`、`references/_dependencies.md` 和 README 共同说明安装及能力边界。

发行检查只证明文本范围、引用、配置格式和敏感内容扫描，再核对 GitHub 提交。它不新增平台真实 replay、E2E agent loop 或产品验收；使用者安装后仍需接入自己的浏览器/引擎并逐平台验证。
