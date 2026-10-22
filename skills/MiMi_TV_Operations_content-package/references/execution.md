# 执行接口

在运营项目根目录运行；`--project` 指向运营项目，所有相对路径相对该项目解析。Python 标准库；剪辑/解码需要 PATH 中的 ffmpeg/ffprobe。不含账号、凭据或网络抓取实现。

## selection.json

```json
{
  "batch_id": "本批唯一名称",
  "requested_count": 7,
  "items": [{"item_json": "content/items/实际目录/item.json"}]
}
```

初选未建 item 时可用内嵌候选替换 item_json：`{"candidate_id":"candidate-01", "content_type":"external_passive_video", "source":{...}, "segment":{...}}`。source 沿用 item 字段：platform、kind、channel、original_title、url、usage_basis、rights_status；已登记时带 material_id，下载后带 local_file、sha256。未知信息不猜填。audit 可在下载前查重，bundle 必须有真实 item。

```bash
python3 .codex/skills/MiMi_TV_Operations_content-package/scripts/content_package.py audit --project /实际/运营项目 --selection /实际/selection.json --output /实际/novelty-audit.json
python3 /Volumes/ExtSSD2601/MiMi_TV_Operations/.codex/skills/MiMi_TV_Operations_content-package/scripts/check_cover_package.py /实际/item.json
python3 /Volumes/ExtSSD2601/MiMi_TV_Operations/.codex/skills/MiMi_TV_Operations_content-package/scripts/check_copy_package.py /实际/item.json
python3 /实际/运营项目/.codex/skills/MiMi_TV_Operations_content-package/scripts/export_publish_packages.py /实际/item.json
python3 .codex/skills/MiMi_TV_Operations_content-package/scripts/content_package.py bundle --project /实际/运营项目 --selection /实际/selection.json --out /实际/新交付目录
```

audit 返回码0表示数量足够且无已知重复/来源缺口，2表示缺口或重复；不表示授权清理或视觉验收。报告保留匹配作品、publication ID/状态与身份依据，不改台账。draft-uploaded 排除，planned 要先核清。按全平台证据判定，未明确取消的旧 item 仍可能在在制队列。

bundle 需本批无重复且达到目标数，拒绝覆盖目录，再核对原片/成片/封面真实哈希、时长尺寸、完整音视频解码、导出一致性和专门封面/文案检查器。它不改 ready、不写台账、不进平台。当前导出接口对应小红书、抖音、B站三平台；只有单个平台的任务直接复用专门内容包导出，不将其它平台视为已验收。输出 index.html、manifest.json、novelty-audit.json、items/ 与 package.zip，ZIP 解压可直接审阅；只收最终媒体、记录、文案与明确引用的封面证据，不递归打入旧稿、原片或其它目录。checks 保留实际检查证据，不自动升级验证层级。

运行 `python3 .codex/skills/MiMi_TV_Operations_content-package/scripts/test_content_package.py` 做去重与交付结构回归。测试使用临时台账和本地产生的测试媒体，属于 logic/contract，不代表真实新素材生产、平台 E2E 或负责人接受；真实批次另存 audit/bundle 报告。

## 修订后的交付同步

用户要求改现有包时，先确认哪些已认可内容保留，再沿实际依赖同步：item／成片／封面 → 受影响的各平台发布文件 → 审阅页与manifest → ZIP → 当前交付入口。改名称同时检查封面字、标题、正文对象、关键词和评论；改片段或叠字同时更新成片元数据与哈希。导出使用文末的显式替换规则，不把已有文件保留当更新成功。

重新打开当前审阅页，并核对ZIP解压后的对应媒体哈希和文案与当前item一致；旧版本可归档，但当前入口应指向新版本。若用户要求周计划不变，保留选题、日期和顺序，交付链接需要时单独更新，不以修物料为由改计划。2026-10-20曾出现当前item已有叠字／CTA而review-v1及ZIP仍是旧版；检查器只看item时不能发现这种交付分叉。

剪辑直接使用既有 video-clip，先读其 SKILL.md、references/atomic-commands.md、references/quality-gates.md 和 engines/video-clip/capabilities.json。简单连续选段使用 rough_cut，时间码显式为源视频轴；不应用口播默认加速、去静音或口播字幕（底部弱提示叠字单独按 overlay.md 处理）。保存原子剪辑账本和 align_check 结果，再写回实际 video 元数据。项目 Skill 的脚本提供查重、字段检查、导出和打包，不再实现另一套剪辑命令。原项目 scripts 及旧全局脚本仅是兼容转发，真实实现都在本 Skill。

## 封面系列检查

```bash
python3 .codex/skills/MiMi_TV_Operations_content-package/scripts/make_contact_sheet.py --output /实际/cover-overview.jpg /实际/旧封面.png /实际/新封面.png
```

将当前稿与 cover.md 要求的实际旧图一起传入，同时检查大图和约120px缩略图。图已生成不代表视觉已接受。

## 精确字段映射

| item 真源 | 小红书发布包 → 代码 | 抖音发布包 → 代码 | B站发布包 → 代码 |
| --- | --- | --- | --- |
| `copy.post_title` | YAML `title` → extractor `title_file` → `--title-file` | YAML `caption` → `--title` | YAML `title` → `--title` |
| `copy.body` | YAML `description: \|` → extractor `desc_file` → `--content-file` | `## 正文` → 原有 `read_section(md, "正文")` → `--desc` | `## 简介 desc` → 原有 `read_section(md, "简介 desc")` → `--desc` |
| `copy.keywords` | YAML `keywords` 块列表 → extractor `keywords` → `--tags` 多参数 | YAML `tags` 数组，按原顺序前 5 个 → `--tags` 逗号分隔 | YAML `tags` 逗号分隔字符串 → `--tags` |
| `video.file` | `video` → `--video` | `video` → `--file` | `video` → `--file` |
| `cover.file` | `cover` → `--cover` | `cover_portrait` → `--thumbnail-portrait` | `cover` → `--cover` |
| `cover.platform_variants["4:3"]` | 不适用 | `cover_landscape` → `--thumbnail-landscape` | 按平台预览选封面比例 |
| `source.url` / 明确批准的平台覆盖值 | 内部核对来源；不自动操作「引用笔记」 | 转载声明 `--declaration 内容为转载信息`；完整 URL 本地保留 | `source` → `--source`，同时 `copyright: 2` → `--copyright 2` |
| `copy.source_credit` | 独立 `## 来源核对资料（不进正文）`；不生成引用原笔记的指令 | 同左 | 同左 |
| `publication_plans.xiaohongshu.optional_platform_actions.quote_source_note` | `false` 或缺省均不引用；`true` 还需记录 `quote_source_note_authorization`，导出包才写入关联要求 | 不适用 | 不适用 |

相对素材路径均相对发布包所在 item 目录解析为绝对路径，不相对 shell 当前目录。正文传给 CLI 时使用参数数组，保留实际换行，禁止把转义后的 `\\n` 当换行或拼接 shell 字符串。

小红书 `description` 是唯一发布正文入口；`## 正文` 是供校验和人审的同值视图。extractor 的 `body` 包含整个 Markdown 后半部分，`body_file` 甚至是长文占位内容，**两者都不能作为视频发布正文**。`abstract` 为兼容当前 extractor 的必填检查导出相同内容，不用于填正文。

抖音旧模板写“caption 标题正文合一”，但当前 `DouyinVideoUploadRequest` 以及 `upload-video --title / --desc` 已分别接收标题与正文。视频包沿用现有 item-003 的方式：`caption` 放短标题，`## 正文` 放完整分段文案，不拼接来源和话题。

## 最小小红书示例

```yaml
---
platform: xiaohongshu
account: mimi_tv
form: video
title: 给猫看的动画片| 蚱蜢跳跳停停
description: |
  第一段正式正文。

  第二段正式正文。
keywords:
  - 猫
  - 猫咪电视
video: video.mp4
cover: cover.png
published: draft
---
```

这是格式示意；真实包另含兼容字段、完整关键词和独立审阅区。`published: draft` 只表示本地包状态，不写回 publication，也不能据此声称平台草稿已保存。

## 排期、账号与来源

- `proposed_schedule` 仅是建议。发布时确认后，小红书映射 `--schedule-at` ISO 时间，抖音/B站映射 `--schedule "YYYY-MM-DD HH:MM"`，使用 Asia/Shanghai；不把旧测试时间或建议时间自动转成定时任务。
- 账号身份以 `account.yaml` 为准，CLI slot 与平台业务账号 ID 不混用。当前复用 `mimi_tv` slot，不将 `mimi_douyin`、`mimi_bilibili` 等包文件别名当凭据 slot。执行仍核对实际登录账号。
- 外部视频必须显式小红书 `--no-original`、抖音转载声明、B站 `copyright: 2`。平台必填来源字段不全是待处理项，不能回填正文冒充完成；小红书「引用笔记」是可选关联，仅在本条明确授权时使用。
- B站 `tid` 必须是已核实的整数。新 item 暂为 `null`，不能用“动物（网页实时核对）”冒充数字。现有 item-003 的 `218` 和负责人指定来源覆盖保留，不推定其它 item 的分区。
- 封面比例与本条实际需要填写的来源字段仍需真实页面检查；包格式通过不代表这些 UI 功能已完成。


## 通用平台解析与检查

使用 [content-package-create](/Users/xpw/.agents/skills/content-package-create/SKILL.md) 当前的平台模板与规格。现有底层路径保留，只链接调用：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/publish-prep/check.py /实际/publish_file.md --platform xiaohongshu --form video
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/publish-prep/check_bundle.py /实际/item目录 --synchronized-reason "项目AGENTS.md规定同作品同步"
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/extract_frontmatter.py /实际/publish_mimi_xhs.md
```

逐项对比解析后的标题、分段正文、关键词和媒体路径与 item 一致；平台数量适配保持有记录的差异。账号短正文不套其它账号口播模板的最低200字，共用检查器的该项失败原样保留并注明业务例外，其它错误不获豁免。B站缺已核验整数 tid 仍阻止投稿；不能因本地包完成而虚构平台适配通过。已有文件的导出默认 preserved；需更新时先核对历史平台覆盖，再显式 --replace，不能把 preserved 当更新成功。
