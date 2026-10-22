> 历史归档（2026-10-22）：以下为迁移前原文，仅供追溯。旧 CLI、独立配置、Cookie 恢复和远端流程均未启用，不可照抄执行。当前执行入口为上一级同名平台 reference 与 `_local-chrome.md`。原文中的相对路径按迁移前位置理解。

# B站视频投稿（reference）

> 先按 [账号与会话](_accounts-and-sessions.md) 选择目标账号和浏览器：正式已有登录优先，掉线后可在选定正式profile用同账号Cookie恢复，必要时扫码。`item.json` 可复用 [platform-video 分步执行器](../../../engines/platform-video/README.md) 的字段步骤，但其 `open` 会另开专用profile，并非接管日常Chrome；所选环境不匹配时不能直接用它替换。下述引擎登录命令只管理各自凭据，具体能力见README。


把**本地视频文件投稿到哔哩哔哩**。底层 = `vendor/social-auto-upload` 的 `sau bilibili` 子命令，它再封装开源 `biliup`（B站投稿事实标准，自动下载二进制）。

> ⚠️ 这份 reference 只管 **B站视频投稿**。B站**专栏文章**走 `references/wechatsync.md`（完全不同的 API）。

## 引擎路径与前置

```bash
ENGINE=/Volumes/ExtSSD2601/AI_Assistant/tools/vendor/social-auto-upload
SAU="$ENGINE/.venv/bin/sau"      # CLI 入口；等价于 .venv/bin/python -m sau_cli
```

- 账号凭证存在 `tools/var/state/social-auto-upload/cookies/bilibili_<account>.json`（已软链，凭证只放 var/）。
- 首次执行会自动从 GitHub Release 下载 `biliup` 二进制到 `~/.social-auto-upload/tools/biliup/`（需联网 + 能访问 github）。
- 账号白名单见 `vendor/wechatsync/config/project-platforms.json` 的 `assistant_zh.expectedAccounts.bilibili`（当前：`张和`）。此白名单仅适用于 assistant_zh；其他项目使用该项目已确认账号，不重复确认已有授权。
- 账号标识约定：`张和` = 本项目（assistant_zh，负责张和全部自媒体）名下的 B站 号，cookie 落 `bilibili_张和.json`。其 B站 真实昵称 **和哥专业讲AI**（UID `36184382`）。注意：不要与小红书里的 `缪东旭_个人`(MiaoDX) 混淆——那是另一个人，旧白名单曾误填 `MiaoDX`，已纠正。

## 命令

**登录（必须在真实交互终端里跑——agent 不能代扫码）：**
```bash
"$SAU" bilibili login --account 张和
```
- biliup 会在终端显示二维码；若终端显示不全，打开当前目录的 `qrcode.png` 扫码。
- 该CLI非交互登录会要求真实终端；仅当本次确实选用biliup路径时才按此处理。网页任务先复用所选正式浏览器，Cookie恢复或扫码也在该环境进行；不要把CLI凭据缺失说成网页未登录。

**检查并刷新脚本登录态（会改写凭据，不是纯只读）：**
```bash
"$SAU" bilibili check --account 张和     # 底层 biliup renew；返回有效/失效
```

**投稿视频：**
```bash
"$SAU" bilibili upload-video --account 张和 \
  --file /abs/path/video.mp4 \
  --title "标题" \
  --desc "简介" \
  --tid 122 \
  --copyright 1 \
  --tags AI,工具 \
  --schedule "2026-06-10 21:30"     # 可选：定时发布
```
- 必填：`--account --file --title --desc --tid --copyright`。`--copyright 1`自制；转载必须用`--copyright 2 --source <本条来源>`，禁止靠默认值误标原创。
- 支持`--cover <图片文件>`、`--submit web|app|b-cut-android`（默认web）、`--dry-run`。先用dry-run核对本地参数；它不会登录、联网、上传或投稿，也不验证平台效果。移除dry-run后命令执行即投稿，仍需通过质量门并获授权。
- 描述中换行使用结构化参数或安全读取文件保留，不用拼接shell命令。
- `--tid` = B站分区 id（必填）。`--tags` 逗号分隔。`--schedule` 格式 `YYYY-MM-DD HH:MM`，映射到 biliup `--dtime` 定时发布。
- 参数映射：`biliup -u <cookie> upload <file> --title --desc --tid [--tag a,b] [--dtime <epoch>]`。

## 提交边界：CLI直接投稿，网页可停在待检查页

- biliup `upload` **执行即投稿**（进审核队列），不像视频号能停在草稿。
- 因此 **upload-video 是对外发布动作**：沿用会话中已确认的素材、账号和提交授权，并满足 `_execution-quality.md` 的提交前质量检查；用户要求先检查时改走网页，不执行本命令。
- 想留缓冲就用 `--schedule` 设一个未来时间（定时投稿），给用户留撤回/改动窗口。
- 投稿成功后把 biliup 返回里的稿件信息/链接（aid/bvid）原样汇报给用户。

## 分区 tid 历史示例（以当前平台为准）

常用（科技/知识向，贴合 AI 内容）：
- `122` 科技 → 野生技术协会
- `201` 知识 → 科学科普
- `188` 数码 → 手机平板 / 科技数码
- `21`  生活 → 日常

分区以当前投稿页或官方投稿接口为准。用户已授权平台适配且内容归属明确时自行选择并记录；确有歧义再询问。旧API细分编号不能直接等同新版网页大类。

## 失败兜底

- 报 `account file is missing` / check 失败 → 区分脚本凭据与网页登录状态；网页已登录可继续网页流程，不据此断言账号掉线。
- biliup 下载失败（github 限流/断网）→ 重试；已下载过会复用本地版本。
- 投稿被风控/分区不符 → 把 biliup 的 stderr 脱敏后给用户，按提示改 tid 或内容。

## 发布包前置（上传前硬门）

B站 CLI `upload-video` 执行即投稿；网页端有“存草稿”且可停在未提交表单。因此进入本 reference 的上传命令前，必须先完成发布包：

1. 核对 `content-package-create` 交付的同 item `core_brief.md`。
2. 核对按 `assets/templates/publish_bilibili.md` 制作的 `publish_<account>.md`，字段至少包含 `title`、`tid`、`tags`、`video` 和 `## 简介 desc`；缺失时回到内容包制作 Skill。
3. 运行单文件校验：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/publish-prep/check.py <publish_file> --platform bilibili --form video
```

4. 如果同一 item 还要发其他平台，再运行集合校验：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/publish-prep/check_bundle.py <item_dir>
```

缺视频字幕/封面/关键帧时，先用 `video-content` 或对应视频链路补素材；这属于发布包生成阶段，不是可跳过的上传后补救。

## 网页与混合路径（2026-09-16 单条 real replay）

遵循 `_execution-quality.md`；本次已验证网页上传/填写，后续提交行为仍按最新授权执行。

- 复用已确认账号页面；系统文件框选视频后观察“上传完成”。若短信验证拦截，保留现场让用户补位。
- 标题、正文分段、来源、标签独立填写。外部转载选择“内容为转载”，来源字段填本条确认URL；不把某次任务URL固定到Skill。
- 删除无关默认标签；逐个输入、回车并确认形成独立标签，连续过快可能漏项。本次8标签成功，不把8当全局数量要求。
- 封面上传后分别检查4:3与16:9，双比例同步不保证视觉合格；竖图横裁可能截字或主体。点击封面编辑的“完成”只保存封面，不是投稿。
- 定时核对开关、日期、UTC+08:00和小时分钟；网页底部仍可能写“立即投稿”，不能凭按钮文案判断定时是否开启。用户要求检查则停在这里，不点最终按钮。
- 网页观察到“存草稿”入口，但本次未实测保存；不能声称草稿路径已验证。

## 脚本能力边界（2026-09-16）

- 2026-09-16 已补 `sau bilibili upload-video` 的封面、转载、来源、接口及dry-run参数，完成logic/contract验证；尚未真实投稿验证。旧调用方需显式补`--copyright`。
- 本地 `biliup upload --help` 已有 `--cover`、`--copyright`（1自制/2转载）、`--source`、`--submit`；先检查当前版本，不把上层缺参数说成底层无能力。不满足提交前质量门时仍走网页。
- 本次网页Cookie真实有效，但转换的biliup凭据缺OAuth令牌，上传前认证返回-400；内置Cookie登录转换也失败，第二种返回502。未验证脚本视频上传或投稿成功。Cookie改JSON结构不能代替令牌获取，不能反复重试同一失败输入。
- 已补本地OAuth缺失诊断，原始Cookie不能直接冒充biliup凭据；认证失败不再直接输出可能含凭据的stderr。命令失败时若无法判断提交状态，必须先核对平台，不能盲目重发。
- 待改进：真实登录兼容、填写/检查/提交分离、结构化平台回执。参数透传和本地诊断已实现，不等于这些待改进项已修好。


2026-09-17 维护补充：当前三平台视频包的菜单、上传、封面恢复按 [执行器固化说明](../../../engines/platform-video/README.md#2026-09-17-网页补救固化) 执行；代码已更新，真实新一轮验证尚未完成。
