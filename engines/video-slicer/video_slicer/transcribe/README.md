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
| 上传通道 | **公网托管**（`uploader=public`，uguu→0x0；上传站已走本地分流） | 阿里 OSS（`uploader=oss`）⚠ **2026-06 凭证已过期、暂不可用**，续期前用 public |

句级线（腾讯会议 minutes）**不走本模块**。

## 网络分流：转录走本地出口（复用发布的 route-bypass）

整机挂海外 Tailscale exit node 时，转录链路从海外 IP 绕行——慢、且易触发地域限制。
所以 CLI 转录前**自动**跑一次 route-bypass，把**整条转录链路**钉到本地网关出口
（与 `platform-publish` 同一套机制），其余流量照旧走海外：

- **国内 ASR API**：`openspeech.bytedance.com`（火山）/ `dashscope.aliyuncs.com`（阿里）。
- **public 上传站**：`uguu.se` / `0x0.st`——"上传公域音频"这一步也走本地。这等价于
  **手动关代理**那条能跑通的路径（上传 + 调 API 全本地），但 VPN 照开、不影响 LLM 翻墙。
  实测：上传站走海外出口时，45MB/2.2h 大音频 8 次重试全空传不上去；走本地才稳。
- OSS 域名也钉着（`--uploader oss` 用），但⚠ 2026-06 OSS 凭证已过期，该通道暂不可用。

- 入口在 `cli.py: _route_bypass_preflight()`，调
  `engines/route-bypass/scripts/publish-network-preflight.zsh transcribe apply`，需要时弹一次
  管理员授权框。
- **路由是优化项不是硬前置**：钉不上只告警、不挡转录（与发布"失败即停"不同——发布上传会卡
  0%，转录失败只是慢）。
- `--skip-route-bypass`：跳过前置（路由已钉过、或纯 `--audio-url` 不在意国内出口时用）。
- **路由是优化项不是硬前置**：钉不上只告警、不挡转录。

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
- `cli.py` / `__main__.py` —— 命令行入口；转录前自动 route-bypass 前置（`--skip-route-bypass` 可关）。

> 去口水/承接句的**判断知识**在 `engines/video-slicer/references/字级去口水与承接句保护.md`；
> 本模块只负责"把声音变成带字级时间戳的词表"，不做删词决策。
