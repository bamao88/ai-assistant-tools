# video_slicer.transcribe —— 字级转写模块

字级剪辑线（方案B）的地基：**音频/视频 → 归一化字级词表 JSON**。

## 输出契约（别改，下游依赖）

```json
{"model": "...", "source_url": "...", "full_text": "...",
 "words": [{"text": "你", "begin_time": 1000, "end_time": 1200}, ...]}
```

`begin_time/end_time` 单位**毫秒**，正是 `video_slicer/twostage/resolve.py` 的
`load_paraformer_words()` 消费的形状 —— 转写产出的 `words.json` 直接喂字级吸附。

## 编排策略（用户拍板）

| 维度 | 主 | 备 |
|---|---|---|
| 转写后端 | **火山 seedasr v3**（`backend=volc`） | 阿里 paraformer-v2（`fallback=aliyun`，火山失败/额度用尽**自动切**） |
| 上传通道 | **公网托管**（`uploader=public`，uguu→0x0） | 阿里 OSS（`uploader=oss`，**代码在、默认不用**，公网出问题再切） |

句级线（腾讯会议 minutes）**不走本模块**。

## 用法

```bash
cd engines/video-slicer
python -m video_slicer.transcribe --audio /path/clip.mp4 --out-dir var/zh_main/asr
python -m video_slicer.transcribe --audio-url https://host/a.mp3 --backend aliyun
python -m video_slicer.transcribe --audio a.mp4 --uploader oss     # 切阿里 OSS 上传
```

代码内：

```python
from video_slicer.transcribe import transcribe_audio
result = transcribe_audio(audio="clip.mp4", out_dir="var/zh_main/asr")  # 火山主·阿里兜底·公网上传
```

## 凭证（`var/credentials/aliyun.env`，gitignore）

- `VOLCENGINE_API_KEY` —— 火山「语音技术→录音文件识别·大模型版」key（**不是方舟/Ark key**）。
- `DASHSCOPE_API_KEY` —— 阿里百炼，兜底后端用。
- `OSS_*` —— 仅 `--uploader oss` 时用。

## 依赖

- 火山 + 公网通道：**纯标准库 + curl + ffmpeg**，系统 python 即可，无需 pip。
- 阿里兜底：`pip install dashscope`（延迟导入，不用就不装）。
- OSS 通道：`pip install oss2`（同上）。

## 文件

- `backends.py` —— 火山 / 阿里两后端，统一归一化词表，失败抛 `BackendError`。
- `upload.py` —— 公网 / OSS 两上传通道。
- `__init__.py` —— 编排：抽音频 → 上传 → 主后端→兜底 → 落 words.json。
- `cli.py` / `__main__.py` —— 命令行入口。

> 去口水/承接句的**判断知识**在 `engines/video-slicer/references/字级去口水与承接句保护.md`；
> 本模块只负责"把声音变成带字级时间戳的词表"，不做删词决策。
