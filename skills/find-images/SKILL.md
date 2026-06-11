# find-images

为文章寻找合适的配图。支持直接网页截图、从视频抠帧截图，也支持在登录墙或权限限制场景下，从网络现有教程中搜索并提取准确的界面截图。

**截图工具目录：** `/Volumes/ExtSSD2601/AI_Assistant/tools/engines/screenshot/`

---

## 决策流程

拿到配图需求后，按配图来源判断：

```
配图来自哪？
  ├─ 网页
  │    ├─ 公开页 → 直接截图（screenshot.js）……………………… 方式一
  │    └─ 需登录
  │          ├─ Chrome 有该站 cookies → export_cookies.py → screenshot.js
  │          └─ 无/失效 → 网络搜索教程提取 ……………………… 方式二
  └─ 视频（YouTube 演讲/访谈/产品演示的画面或 PPT）
       → 抠帧 + 裁区域（video_frame.py）……………………… 方式三
```

**不管用哪种方式，拿到候选图片后都必须视觉验证再使用。**

---

## 方式一：直接截图

```bash
node /Volumes/ExtSSD2601/AI_Assistant/tools/engines/screenshot/screenshot.js \
  "<url>" \
  "<output_path>" \
  "<selector_or_text>" \
  [wait_ms]
```

| 参数 | 说明 |
|------|------|
| `url` | 目标网页 URL |
| `output_path` | 输出路径（.png） |
| `selector_or_text` | 可选。`text=关键词` 按文字定位；CSS selector；`xpath=...` |
| `wait_ms` | 可选，额外等待 JS 渲染（默认 2000ms，复杂页面用 4000-5000） |

```bash
# 截特定文字所在区域
node screenshot.js "https://example.com" /tmp/out.png "text=下载" 3000

# 全视口截图
node screenshot.js "https://example.com" /tmp/out.png
```

---

## 方式二：从现有教程提取（登录墙场景）

当目标页面需要登录，且无法获取有效 cookies 时，改用此策略。

### 第一步：搜索含目标界面截图的文章

用 `WebSearch`，关键词组合：**平台名 + 页面名 + 截图 + 教程**，优先找：
- 官方博客 / 官方文档（截图最准确）
- 掘金、知乎、CSDN 的操作教程

示例：
```
Moonshot Kimi API Key 管理 截图 教程
飞书开放平台 凭证与基础信息 App ID App Secret 截图
```

### 第二步：用 browse 列出页面所有图片

```bash
B="$HOME/.claude/skills/gstack/browse/dist/browse"
export PATH="$HOME/.bun/bin:$PATH"

$B goto "<文章URL>"
$B media --images 2>&1 | grep '"src"' | grep -v "svg\|logo\|icon\|avatar\|data:"
```

### 第三步：批量下载候选图片

```bash
mkdir -p /tmp/candidate-imgs
curl -s -L "<图片URL>" -o /tmp/candidate-imgs/img_0.webp

# webp 转 png（macOS）
sips -s format png /tmp/candidate-imgs/img_0.webp --out /tmp/candidate-imgs/img_0.png
```

### 第四步：视觉验证（必须执行）

用 Read 工具逐张查看，判断标准：
- 是否是目标平台的真实界面截图
- 是否包含文章描述的关键元素（按钮、字段、菜单项等）
- 画质是否清晰，信息是否完整

**不要跳过这步。第一张找到的图不一定是最合适的。**

### 第五步：保存到文章 assets

```bash
ASSETS="<文章目录>/assets/<文章slug>/"
mkdir -p "$ASSETS"
cp /tmp/candidate-imgs/img_X.png "$ASSETS/XX-描述.png"
```

---

## 登录状态（方式一专用）

需要登录的平台通过 `storage_state.json` 注入 cookies，从运行中的 Chrome（port 9222）导出。

| 平台 | 状态 |
|------|------|
| x.com / twitter.com | ✅ 已登录 |
| xiaohongshu.com | ✅ 已登录 |
| openai.com | ✅ 有 cookies |

**cookies 过期时刷新：**
```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/screenshot/export_cookies.py
```
> 需要 Chrome (port 9222) 处于运行状态

---

## 输出路径规范

| 场景 | 推荐路径 |
|------|---------|
| 文章配套素材 | `knowledge_base/wiki/assets/<文章slug>/` 或 `longform_write/blog_output/assets/<slug>/` |
| 发布验证截图 | `data_review/<date>/` |
| 临时截图 | `/tmp/screenshot_<timestamp>.png` |

---

## 行为说明（截图工具）

- 自动关闭 cookie 弹窗（Accept / 接受 / 拒绝必要等）
- 定位到目标元素后自动滚动到视口内再截图
- 截图区域：元素上方留 80px，下方留 400px（含上下文）
- deviceScaleFactor=2（Retina 质量）
- 找不到 selector 时报错退出，不静默降级
