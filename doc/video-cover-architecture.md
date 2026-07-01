# 视频封面架构：两套并列 kit

张和视频封面有**两套并列风格**，共用同一批品牌人像底图，但渲染管线与配置各自独立。

## 两套 kit 对照

| 维度 | 黑块黄字（9:16） | evc 宋体渐变（3:4） |
|---|---|---|
| 归属 | `platform-publish` skill 的 assets（无独立触发入口） | 独立 skill **`zh-video-cover`**（`scope: assistant_zh`） |
| kit 配置 | `skills/platform-publish/assets/video-cover/zhanghe/cover-kit.json` | `skills/zh-video-cover/assets/cover-kit-evc.json` |
| 生成器 | `.../zhanghe/generate_video_cover.py` | `skills/zh-video-cover/assets/generate_evc_cover.py` |
| 画幅 | 9:16 底图原尺寸 + 可选后裁 3:4 | 直接 3:4 = 1242×1660（成品即画布） |
| 底部遮罩 | `block` 纯黑矩形，底边锚 `bottom_frac=0.875` | `gradient` 素材(白顶黑底)转 alpha=255−L 叠加 |
| 字体 | 阿里巴巴普惠体 Heavy | 思源宋体 Heavy（衬线） |
| 字色/描边 | 黄字无描边 | 白字 + 2px 黑描边 |
| 文字位置 | 贴 block 顶往上排 | 垂直中心 y=0.75·H |
| 字号 | frac-of-H 反推 | 最长行像素宽驱动（≤1060px，绝对 px 上下限 132/78） |
| 人物上移 | 无 | lift=3/16 裁切 |
| 底图 | 全池 frame-01..06 | frame-01..05（**排除 frame-06** 贴脸自拍） |
| 轮换游标 | `.rotation_state.json` | `.rotation_state_evc.json`（独立，互不干扰） |
| 批量 | 无 | 有（manifest：按发布顺序轮换、相邻不撞、各写 item cover.png + 总览图） |

## 共享品牌资产（单一真源，留 platform-publish 原地）

- 底图池 `skills/platform-publish/assets/video-cover/zhanghe/covers/`（frame-01..06）
- 渐变素材 `.../zhanghe/gradient-3x4-bottom-black.png`

`zh-video-cover` 的 `cover-kit-evc.json` 用 `shared_assets_dir` 字段按绝对路径引用这两项，**不复制底图池**。字体 evc 侧 bundled 一份在自己 assets（自包含）。

## 为什么 evc 独立成 skill

evc 是张和唯一认可的口播切片封面样式，过去只是 media/ 里硬编码临时脚本、参数靠对话现调、反复沟通。2026-07-01 固化：全部参数进 `cover-kit-evc.json`，生成器零硬编码，单张/批量一条命令。黑块黄字那套已 kit 驱动、暂不动，故先只固化 evc、并列不合并。

设计稿：`assistant_zh/claude_md_design/video_cover_evc_kit_design.md`。回退 tag：`pre-evc-cover-skill`。
