# Video Slicer

本地优先的视频切片 CLI。输入已经下载好的长视频和带时间轴的字幕或逐字稿，输出短视频片段。

## 快速开始

本仓库的文档默认使用中文。命令示例优先使用当前环境可运行的 `python3 -m video_slicer.cli`；如果已经安装包，也可以使用 `video-slicer` 入口。

手动切片：

```bash
python3 -m video_slicer.cli render \
  --video input.mp4 \
  --transcript subtitles.en.vtt \
  --clip 00:12:30-00:13:45 \
  --out-dir outputs
```

AI 生成剪辑方案：

凭证从工具根目录的 `.env` 读取（本机上 `.env` 是指向共享 `knowledge_base/.env`
的软链，MiniMax/Kimi 密钥只存一份）。Provider 选择沿用 knowledge_ingest 的写法：
`LLM_PROVIDER`（默认 `minimax`）→ `LLM_FALLBACK`（默认 `kimi`）→ OpenAI 兜底。
详见 `.env.example`。配好后无需再带环境变量：

```bash
python3 -m video_slicer.cli plan \
  --video input.mp4 \
  --transcript subtitles.en.vtt \
  --mode query \
  --query "找出关于 AI 产品管理的精彩片段。" \
  --out clip_plan.json
```

渲染可复用的剪辑方案：

```bash
python3 -m video_slicer.cli render \
  --video input.mp4 \
  --transcript subtitles.en.vtt \
  --clip-plan clip_plan.json \
  --out-dir outputs
```

验证输入文件：

```bash
python3 -m video_slicer.cli validate \
  --video input.mp4 \
  --transcript subtitles.en.vtt
```

## 当前能力

- 输入视频下载或导入不在当前工具范围内。
- 渲染需要 VTT、SRT 等带时间轴的字幕或逐字稿。
- `render` 支持直接传入 `--clip`，也支持传入 `--clip-plan`。
- `plan` 支持 `manual`、`query`、`auto` 三种模式。
- 布局支持 `original`、`vertical`、`square`。
- 字幕模式支持 `auto`、`none`、`soft`、`burned`、`bilingual`。
- `--subtitle auto` 会把可见字幕烧录进输出视频，并写出旁路字幕文件。
- 英文视频使用 `--subtitle auto` 时会优先输出中英双语字幕。可以提供 `--zh-transcript`，也可以配置 OpenAI 兼容提供方进行翻译。

## 本地验证

```bash
python3 -m pytest -q
```
