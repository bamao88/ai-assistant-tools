---
name: Agent-Publish
description: |
  内容发布与多平台分发入口。接收已确认的发布包，在目标平台核对账号与权限、
  上传素材、填写和读回页面、创建草稿或按授权提交。支持小红书、微信公众号文章及原生贴图（小绿书/newspic）、
  视频号、B站视频、抖音视频，以及知乎、掘金、CSDN、百家号、思否、今日头条等文章平台。
  用户明确要求“发布”“发到”“同步”“分发”“排版发布”“创建草稿”“上传文章/视频”
  或处理已有发布页时使用。发布包缺失时先调用 content-package-create 制作和校验，再回到本技能执行。
  单独起标题、写正文、做封面文案、生成公众号封面或准备发布物料，
  使用 content-package-create；仅提到目标平台不触发本技能。
  当用户说"发B站""发布到B站""投稿B站""B站视频""bilibili 投稿""发视频到B站"并给出本地视频时，也使用本 skill，并路由到 references/bilibili-video.md。
  当用户说"发抖音""发布到抖音""抖音视频""投稿抖音""抖音图文/笔记"并给出本地视频/图片时，也使用本 skill，并路由到 references/douyin.md。
  当用户说"发视频号""发布到视频号""视频号助手""微信视频号""测试视频号发布流程""视频号没有登录状态""视频号扫码登录"时，也使用本 skill，并路由到 references/shipinhao.md。
  独立抓取/调研用 platform-fetch，博主报告用 content-creator-research，互动用 xhs-interact，独立小红书认证用 xhs-auth。发布中的账号选择和登录恢复留在本 skill；卡片生成由 content-package-create 调用 markdown-to-cards。
---

# Agent-Publish：本机现有Chrome发布

接收已经确认的发布包，在**本台电脑、负责人已打开并登录的日常Chrome**中完成平台操作。2026-10-22用户明确取消其它电脑发布及脚本独立配置路线。此要求覆盖所有平台和项目的旧机器偏好；没有登录时请用户在同一Chrome登录。

```text
目标账号、发布包、最新提交权限
→ 枚举本机已有Chrome，锁定正确的日常profile与扩展实例
→ 运行会话hook（before_connect），通过后接管现有浏览器
→ 在同一Chrome直接打开平台，读回真实身份
   ├─ 未登录/身份不符：保留原页，请用户登录，暂停该平台
   └─ 身份正确：hook（before_upload）→ 上传/填写/封面/排期 → 页面检查
→ 最新授权允许提交且质量通过：hook（before_submit）→ 单独提交 → 确认回执
→ 独立记录平台结果，保留未完成页，只关闭本条已成功发布页
```

## 执行环境与必经hook

先读 [本机Chrome接管与hook](references/_local-chrome.md) 和 [账号与会话](references/_accounts-and-sessions.md)。**本机已有Chrome是唯一活动执行路线**，通过当前工具提供的Chrome扩展入口接管；浏览器内可新开平台标签页，不创建新的浏览器配置或上下文。

会话检查脚本是本Skill的发布入口hook：`scripts/guard_existing_chrome.py`。在接管、上传/填写、最终提交前分别运行，使用本轮真实浏览器清单与当前连接记录，失败即停止后续操作，展示错误码和原因。不得为了得到通过结果伪造观察或修改已锁定绑定。详细JSON格式、命令和保护边界集中在上述reference。

不运行会隐式启动Chrome的`check-login`、独立`open-publish-page`、SAU/slot发布命令、`platform-video open`、CDP/Patchright独立启动器。也不导入Cookie、不复制登录态、不启用远程机器、SSH、SMB或屏幕共享发布路线。平台reference里的历史引擎不是替代入口；不得因工具方便、网络慢或“立即发布”而换环境。连接缺项时保留原Chrome并说明缺口。

用户只要求接管/登录验证时，允许不准备发布包；只打开平台、读身份及页面状态，禁止上传、填稿、存草稿和提交。**验证登录直接看当前Chrome的页面**，不是调用检查器。

## 平台路由

一次只读当前平台reference；所有平台先走同一个Chrome会话hook。

| 平台与内容 | reference |
|---|---|
| 小红书图文、长文、视频 | [xiaohongshu.md](references/xiaohongshu.md) |
| 公众号文章、原生贴图/小绿书 | [gongzhonghao.md](references/gongzhonghao.md) |
| 视频号视频 | [shipinhao.md](references/shipinhao.md) |
| B站视频 | [bilibili-video.md](references/bilibili-video.md) |
| 抖音视频、图文 | [douyin.md](references/douyin.md) |
| 知乎、掘金、CSDN、百家号、思否、头条等文章 | [wechatsync.md](references/wechatsync.md) |

## 1. 锁定任务与提交权限

从本次明确指令、作品账号映射、项目默认依次解析目标平台与真实账号。Google账号、Chrome配置名和平台账号分开核对；不能拿恰好登录的另一个业务账号补位。已有明确归属不重复询问。

- `manual-submit`：填表后保留页面，最终按钮由人点击；只在任务包含保存草稿时保存。
- `agent-submit`：用户明确授权直接发布、定时、投稿或提交审核，Agent才可在质量检查后完成最终动作。

最新“先检查/不要提交”覆盖此前自动提交授权；“用当前Chrome验证接管”不授权重新发布。先查本条各平台已有提交记录；已经接受的内容不重复上传、建稿或提交。结果不明先查原稿。

## 2. 核验发布包

读 [全局约束](references/_invariants.md)。需有`core_brief.md`、每个目标账号的`publish_<account>.md`及素材路径；缺失交`content-package-create`补齐，不在后台临时改标题或正文。

本地集合校验（不打开浏览器）：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/publish-prep/check_bundle.py <item_dir>
```

单文件校验：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/publish-prep/check.py <publish_file> --platform <platform> [--form article|video|newspic]
```

用户要求同步文案时可用集合校验的`--synchronized-reason "用户授权依据"`记录标题相同的例外；平台硬限制与缺必填仍需修复。模板最低字数、人设建议与已确认内容冲突时记录例外，不为模板凑字，不把例外说成校验通过。

## 3. 绑定Chrome并直接检查平台

从当前工具清单发现已运行的Chrome扩展入口，按负责人已确认的日常Google/profile归属锁定本轮连接，运行`before_connect`。hook通过后保持同一连接和profile，优先接回本条现有页面；没有任务页时在该Chrome新开平台标签。

按平台原生ID及昵称读回身份。登录页或身份不符时，记录`human-login-required`，保留该页并请用户在这份Chrome完成登录；不导Cookie、不运行`check-login`、不自动切profile/机器。其它独立平台可继续只读检查。用户完成后在原页重新读身份，不重新上传已有稿件。

## 4. 原页上传、填写和检查

进入写操作前运行`before_upload`，随后仅通过已绑定Chrome的浏览器能力完成上传、标题、分段正文、原生话题、封面、来源/声明和排期。输入或定位失败先读当前页，保留已完成步骤，原位补齐；不能改用会新建浏览器的CLI。

读 [执行与质量检查](references/_execution-quality.md)。核对实际账号、素材上传完成、换行、原生话题、封面每个比例已保存、来源/声明、时区/时间及最新权限。不能用命令退出码、本地参数、普通井号文字或封面评估分数代替页面验收。需要用户审阅时在对话里展示实际标题、正文和图片。

正文保留已确认空行；来源记录不自动追加到正文或关联他人笔记。抖音最多5个话题；小红书声明默认「虚构演绎，仅供娱乐」。小工具等可选关联按本条授权及真实页面检查，不擅自增加活动、推广或付费操作。

## 5. 单独提交与收尾

逐平台、逐条执行；质量通过且最新权限为`agent-submit`，再运行`before_submit`并点击最终按钮。hook通过仅证明会话检查，不代替内容质量或提交授权。平台接受后才记录提交成功；已提交/已定时与公开可见分开，结果未知先查重。

- 成功只关闭本平台本条精确发布页；不关闭浏览器、窗口、标签组或其它平台页面。
- 每轮结束为所有未完成页面重新设置`markHandoff()`；等待用户登录也须保留。
- 保存本机标识、锁定浏览器与扩展实例、profile证据、平台真实身份、tab、hook结果、当前阶段、提交权限及回执。
- 不因本轮验证或规则修改重新提交已有作品。实际复用、上传、提交和公开验证分层报告。

## 维护与职责

内容写作/封面/发布包交`content-package-create`；抓取交`platform-fetch`；互动交`xhs-interact`。发布中登录补位留在当前Chrome，不转交会另开profile的原子登录CLI。

用户明确要求维护时，修正负责该行为的Skill、hook和说明并验证；当前编辑页保持原状。`references/history/`仅供独立维护查阅，不是可回退的发布路线。新增hook不是宿主全局工具拦截器，不能宣称会自动拦住任何绕过Skill的任意shell命令。
