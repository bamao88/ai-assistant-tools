> 历史维护资料，非活动执行流程。2026-10-22起统一本机已有Chrome；不得据此新开配置、导Cookie、连接远端或调用直传。当前流程以主Skill和_local-chrome.md为准。

# Skill: gzh-publish

## 触发条件

当用户提到以下任意关键词时激活此 Skill：
- "发布公众号"、"发布到公众号"、"发布微信"、"微信公众号"
- "排版发布"、"公众号排版"、"gzh"
- "上传文章"、"创建草稿"（公众号相关语境）
- "公众号贴图"、"小绿书"、"图片消息"、"newspic"（公众号相关语境）

## 先确定内容形态

- 普通文章（`news`）：按下文文章流程，Markdown → HTML，使用账号固定主题与独立封面。
- 原生贴图（`newspic`）：按本节执行，纯文本说明 + 有序图片；不把图片嵌入文章正文，不套文章主题和封面 kit。

### 原生贴图发布包与命令

发布包由 `content-package-create` 按 [贴图模板](../assets/templates/publish_gongzhonghao_newspic.md)准备。`article_type: newspic`、`title` 和有序 `images` 是核心字段，正文只放实际发布的纯文本说明。`images` 第一张就是封面，总数1–20张；路径相对发布包，支持本地 JPG/PNG/GIF/BMP，非空且小于10MB。标题按当前[官方新增草稿文档](https://developers.weixin.qq.com/doc/subscription/api/draftbox/draftmanage/api_draft_add.html)不超过32个字。空说明传空 `content`，不自动补字。2026-10-07 小助理真实更新草稿已验证32字标题和空说明可接受；其他账号按实际权限与返回判断。

评论选项用 `need_open_comment` / `only_fans_can_comment`（0/1或布尔）。可选 `cover_info.crop_percent_list` 设置裁切，比例支持 `1_1`、`16_9`、`2.35_1`，坐标0–1且最多6位小数。不要同时传 `cover`、`theme` 或 `--style-config`。

小助理发布身份仍为 `wxp-ai`；账号表中的 `coral` 与封面 kit 只用于普通文章。先明确本次账号，不能因默认 profile 存在而省略账号选择。

```bash
# 本地发布包校验；不联网
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/publish-prep/check.py <publish_file.md> --platform gongzhonghao --form newspic

# 本地预检查，输出请求预览；不会获取令牌、上传或创建草稿
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts <publish_file.md> --profile wxp-ai --dry-run

# 上传永久图片、创建或更新原生贴图草稿，然后读回核对
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts <publish_file.md> --profile wxp-ai
```

也可显式传 `--form newspic`；它不能与 `article_type: news` 冲突。上例 `wxp-ai` 只适用于小助理任务，其他账号按本次身份更换。

成功 JSON 的 `status: draft_verified` 表示官方草稿读回确认类型、标题、说明、图片数量/顺序、评论及已指定裁切；`action` 为 `created`、`reused` 或 `updated`。提供 `media_id`、`image_media_ids` 和 `state_file`，不能将其报告为公开发表或手机效果验收。引擎操作记录在 `var/gzh-publish/newspic/`，不写入凭据，按账号和文件路径隔离。

同一账号、同一路径再次执行会复用图片素材；未变化的草稿只读回，文字、顺序、评论或裁切变化时更新原草稿。不删除草稿或素材。不要移动发布包、清空记录后当作“重试”，这会失去原草稿关联。

创建超时/网络结果不明时，下一次执行先在最近60篇草稿中按原始请求匹配。无法唯一确认就保留记录并停止；核对确切草稿后，用同一命令追加 `--draft-id <media_id>` 接回。已有草稿被删除、发表或改成其他类型时不会自动另建。进程被强制终止留下 `.lock` 时，先确认对应 PID 已结束及草稿状态，再清理该锁，不能盲目重跑。

### 贴图公开发表边界

默认只创建草稿。只有明确授权自动公开发表，才在同一命令追加 `--publish`。引擎先核验草稿，再调用 `freepublish/submit` 并查询结果；`status: publishing` 仍是处理中，只有 `status: published` 和官方成功状态才是发表成功。发表结果不明不重提；已有任务 ID 时重跑只查询。此接口不是给粉丝群发的授权。

官方当前将公众号发表接口列为企业主体已认证可调用。具体账号权限与 `newspic` 发表需真实核验，不能以普通文章历史成功或离线测试代替。小助理本次测试仅授权草稿；自动公开发表/群发不在本次真实验证范围。

**验证层级（2026-10-07）：**logic/contract回归通过；小助理（`wxp-ai`）真实API replay完成两图创建、读回、重复复用、顺序更新、32字标题、空说明和显式1:1封面裁切，再恢复原测试稿。草稿API的E2E agent loop完成；后台浏览器检查被站点安全策略阻止，手机product acceptance未完成，公开发表E2E未验证。证据在 `var/gzh-publish/tests/20261007-wxp-ai/`。

## 工具路径

```
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts
```

运行命令格式：
```bash
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts <file.md> [options]
```

## 可用主题

**经典系列：** claude(Claude，直觉机器漫谈 / MiaoDX 固定风格), medium(Medium), minimal(极简)

**更多风格：** openai(OpenAI), cards-claude(卡片 Claude), coral(粉红/珊瑚系，AI PM 小助理固定风格), monograph_all_both(黑白书页)

## 账号样式映射（按账号匹配 profile + 主题 + 封面）

每个公众号账号绑定一套固定的发布身份：发布用哪个 `--profile`、排版用哪个主题、封面用哪套 cover kit。做该账号的公众号发布时直接按这张表取，不要每次重新问。

| 账号 | 作者 / 发布身份 | `--profile` | 固定主题 | 封面 cover kit |
|---|---|---|---|---|
| AI PM 小助理 | AI PM超级小助理 | `wxp-ai` | `coral`（粉红/珊瑚系） | `assets/gongzhonghao/ai-pm-assistant/` |
| 直觉机器漫谈 | MiaoDX | `mdx` | `claude` | 使用文章 frontmatter 的 `cover`，不要套用 AI PM 封面 |

封面和模板按账号专属化。`coral`（粉红/珊瑚系）是 AI PM 小助理 / `wxp-ai` 的固定主题；`claude` 是 直觉机器漫谈 / MiaoDX / `mdx` 的固定主题。AI PM 小助理这套封面只用于 `wxp-ai`，不要混用到直觉机器漫谈或其他公众号账号。

config 里 `~/.gzh-publish/config.json` 现有 profile：`mdx`(default) / `wxp-ai` / `wxp-self`。其中 `mdx` = 直觉机器漫谈 / MiaoDX，`wxp-ai` = AI PM 小助理号。

## 公众号封面交接

封面图在发布前由 [`content-package-create` 的公众号封面说明](../../content-package-create/references/gongzhonghao-cover.md)制作或选择。这里仅核对 frontmatter 的 `cover` 路径、账号专属样式与平台裁切结果，不在发布页面临时生成封面。

## 普通文章执行流程

### 1. 检查文件

确认用户提供了 Markdown 文件路径，文件存在且有效。

### 2. 确认主题（如未指定）

先按账号样式映射取固定主题，不要把账号专属主题当成通用推荐：
- AI PM 小助理 / `wxp-ai` → 固定用 `coral`（粉红/珊瑚系）。
- 直觉机器漫谈 / MiaoDX / `mdx` → 固定用 `claude`。

如果用户明确要求非固定账号或实验主题，再询问主题。通用备选主题：
- 技术/开发文章 → `openai`
- 卡片感公众号长文 → `cards-claude`
- 黑白书页/专著感长文 → `monograph_all_both`
- 零干扰极简排版 → `minimal`

### 3. 检查 frontmatter

确认文件有：
- `title`：文章标题
- `cover`：封面图路径（**必填**，否则无法上传）
- `theme`（可选，frontmatter 中指定会覆盖 CLI 参数）

如果已确定公众号账号，frontmatter 里的 `theme` 必须与账号固定主题一致；不一致时先改 frontmatter，再 dry-run。`wxp-ai` 固定 `coral`，`mdx` 固定 `claude`。

### 4. 预览（可选）

运行 dry-run 先预览 HTML：
```bash
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts <file.md> --theme <id> --dry-run
```

若用户明确选择排版编辑器保存的公众号样式，用 `--style-config <公众号样式.json>` 替代 `--theme <id>`；配置中的底稿主题优先于文章 frontmatter 的 `theme`。先 dry-run 检查真实 HTML，再用同一配置创建草稿。不要自动将自定义样式应用到其他账号。

### 5. 执行上传

**仅创建草稿（推荐）：**
```bash
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts <file.md> --theme <id>
```

**指定账号 profile 发布：**
```bash
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts <file.md> --profile mdx
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts <file.md> --profile wxp-ai
```

按账号固定主题发布示例：

```bash
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts <file.md> --profile mdx --theme claude
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts <file.md> --profile wxp-ai --theme coral
```

**创建草稿并直接发布：**
```bash
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts <file.md> --theme <id> --publish
```

### 6. 报告结果

告知用户：
- ✓ 草稿已创建 + media_id
- ✓ frontmatter 已更新 `published: draft`
- 如果发布：✓ 已发布 + publish_id

## Markdown frontmatter 格式

```yaml
---
title: "文章标题"
theme: monograph_all_both # 可选，覆盖 CLI 参数；不填则使用工具默认主题
cover: cover.png        # 必填，相对于 .md 文件的路径
author: 作者名          # 可选
digest: 文章摘要描述    # 可选，最多120字
published: false        # false=未发布, draft=草稿, true=已发布
---
```

## 配置要求

需要设置微信公众号凭证（任选一种方式）：

1. **环境变量**：`WECHAT_APP_ID` + `WECHAT_APP_SECRET`
2. **配置文件（多账号）**：`~/.gzh-publish/config.json` 使用 profiles 格式：
   ```json
   {
     "profiles": {
       "mdx": { "WECHAT_APP_ID": "wx...", "WECHAT_APP_SECRET": "..." },
       "wxp-ai": { "WECHAT_APP_ID": "wx...", "WECHAT_APP_SECRET": "..." }
     },
     "default": "mdx"
   }
   ```
   使用时加 `--profile mdx` 或 `--profile wxp-ai`，不加则用 `default` 指定的账号。
3. **配置文件（单账号，兼容旧格式）**：`~/.gzh-publish/config.json` 包含 `WECHAT_APP_ID` 和 `WECHAT_APP_SECRET`
4. **本地 .env 文件**：在文章所在目录创建 `.env` 文件

验证凭证：

```bash
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts --check-auth
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts --check-auth --profile mdx
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts --check-auth --profile wxp-ai
```

## 注意事项

- 已标记 `published: true` 的文章会被跳过
- 正文开头的同名一级标题会自动作为公众号标题处理，不会写入正文
- 普通文章封面图必填；原生贴图使用图片列表首图，不要求独立封面
- 草稿创建后需在微信公众号后台审核后手动发布（或使用 --publish 直接发布）
- `--dry-run` 模式生成 HTML 文件便于预览，不会调用微信 API
