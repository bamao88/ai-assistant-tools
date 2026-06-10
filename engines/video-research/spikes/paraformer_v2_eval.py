#!/usr/bin/env python3
"""paraformer-v2 字级（逐字）时间戳评测 spike。

目的：评估阿里云百炼 paraformer-v2「录音文件识别」对中文的识别准确率 + 字级时间戳精度，
      作为是否接入 video-research 引擎的依据。本脚本是一次性评测，不是正式工具原子。

流程：
  本地音频 --(OSS presigned URL)--> paraformer-v2 异步识别 --> 下载结果JSON
        --> 提取字级时间戳 --> 打印文本/前30字 --> 存 json + 逐字 srt --> 大白话评估

依赖：
  pip install dashscope oss2

鉴权（不硬编码；优先读环境变量，其次读 --env-file / var/credentials/aliyun.env）：
  DASHSCOPE_API_KEY        百炼 API Key（鉴权用）
  OSS_ACCESS_KEY_ID        OSS AccessKey（与 DashScope key 不是同一个）
  OSS_ACCESS_KEY_SECRET
  OSS_BUCKET               已创建的 bucket 名，如 my-bucket
  OSS_ENDPOINT             如 oss-cn-shanghai.aliyuncs.com（带不带 https:// 均可）

用法：
  python paraformer_v2_eval.py --audio /path/test-audio-3min.mp3
  python paraformer_v2_eval.py --audio-url https://host/a.mp3   # 已有公网直链则跳过 OSS
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from http import HTTPStatus
from pathlib import Path

# 仓库根：engines/video-research/spikes/ -> 上溯 3 层
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ENV_FILE = REPO_ROOT / "var" / "credentials" / "aliyun.env"
DEFAULT_OUT_DIR = REPO_ROOT / "var" / "output" / "paraformer-eval"


# ---------- 配置加载 ----------

def load_env_file(path: Path) -> None:
    """读 KEY=VALUE 文件注入 os.environ（已存在的环境变量优先，不覆盖）。"""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


def require_env(keys: list[str]) -> dict[str, str]:
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        sys.exit(
            "缺少环境变量：" + ", ".join(missing)
            + f"\n请在 {DEFAULT_ENV_FILE} 里按 KEY=VALUE 填好，或 export 后重试。"
        )
    return {k: os.environ[k] for k in keys}


# ---------- OSS 上传（拿公网直链）----------

def upload_to_oss(audio: Path) -> tuple[str, callable]:
    """上传本地音频到 OSS，返回 (presigned_url, cleanup())。用签名URL免去公读ACL。"""
    import oss2  # 延迟导入，便于 --audio-url 路径无需装 oss2

    cfg = require_env(["OSS_ACCESS_KEY_ID", "OSS_ACCESS_KEY_SECRET", "OSS_BUCKET", "OSS_ENDPOINT"])
    endpoint = cfg["OSS_ENDPOINT"]
    if not endpoint.startswith("http"):
        endpoint = "https://" + endpoint
    auth = oss2.Auth(cfg["OSS_ACCESS_KEY_ID"], cfg["OSS_ACCESS_KEY_SECRET"])
    bucket = oss2.Bucket(auth, endpoint, cfg["OSS_BUCKET"])

    key = f"paraformer-eval/{int(time.time())}-{audio.name}"
    print(f"[OSS] 上传 {audio} -> oss://{cfg['OSS_BUCKET']}/{key}", file=sys.stderr)
    bucket.put_object_from_file(key, str(audio))
    url = bucket.sign_url("GET", key, 3600, slash_safe=True)  # 1h 内有效，足够任务拉取

    def cleanup() -> None:
        try:
            bucket.delete_object(key)
            print(f"[OSS] 已清理临时对象 {key}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"[OSS] 清理失败（可忽略，24h 自行无效）：{e}", file=sys.stderr)

    return url, cleanup


# ---------- paraformer-v2 调用 ----------

def _attr(obj, key, default=None):
    """兼容 dashscope 返回对象既支持属性又支持下标访问。"""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def transcribe(url: str, model: str, langs: list[str]) -> dict:
    """提交 paraformer 异步任务，等待完成，下载并返回结果 JSON。"""
    import dashscope
    from dashscope.audio.asr import Transcription

    dashscope.api_key = os.environ["DASHSCOPE_API_KEY"]

    print(f"[ASR] 提交任务 model={model} langs={langs}", file=sys.stderr)
    task = Transcription.async_call(model=model, file_urls=[url], language_hints=langs)
    task_id = _attr(_attr(task, "output"), "task_id")
    if not task_id:
        sys.exit(f"提交失败：{getattr(task, 'message', task)}")
    print(f"[ASR] task_id={task_id} 等待完成…（排队+识别，通常数分钟内）", file=sys.stderr)

    resp = Transcription.wait(task=task_id)
    if getattr(resp, "status_code", None) != HTTPStatus.OK:
        sys.exit(f"任务失败：status={getattr(resp, 'status_code', '?')} msg={getattr(resp, 'message', resp)}")

    results = _attr(_attr(resp, "output"), "results") or []
    if not results:
        sys.exit(f"无识别结果：{_attr(resp, 'output')}")

    first = results[0]
    if _attr(first, "subtask_status") not in (None, "SUCCEEDED"):
        sys.exit(f"子任务未成功：{first}")
    trans_url = _attr(first, "transcription_url")
    if not trans_url:
        sys.exit(f"结果缺少 transcription_url：{first}")

    print(f"[ASR] 下载识别结果 JSON：{trans_url[:80]}…", file=sys.stderr)
    with urllib.request.urlopen(trans_url, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


# ---------- 结果解析 ----------

def extract_words(result_json: dict) -> tuple[str, list[dict]]:
    """从 paraformer 结果 JSON 取整段文本 + 字级时间戳列表。

    结构：transcripts[0].sentences[].words[]，word 含 text/begin_time/end_time(ms)/punctuation。
    """
    transcripts = result_json.get("transcripts") or []
    if not transcripts:
        sys.exit(f"结果无 transcripts：{list(result_json)}")
    t0 = transcripts[0]
    full_text = t0.get("text", "")
    words: list[dict] = []
    for sent in t0.get("sentences", []):
        for w in sent.get("words", []):
            words.append(
                {
                    "text": w.get("text", ""),
                    "begin_time": w.get("begin_time"),
                    "end_time": w.get("end_time"),
                    "punctuation": w.get("punctuation", ""),
                }
            )
    if not full_text:
        full_text = "".join(w["text"] + w["punctuation"] for w in words)
    return full_text, words


def ms_to_srt(ms: int) -> str:
    ms = int(ms)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(words: list[dict], path: Path) -> None:
    """逐字 SRT：每个字一条 cue，方便拖进剪辑软件看对齐。"""
    blocks = []
    for i, w in enumerate(words, start=1):
        if w["begin_time"] is None or w["end_time"] is None:
            continue
        blocks.append(
            f"{i}\n{ms_to_srt(w['begin_time'])} --> {ms_to_srt(w['end_time'])}\n"
            f"{w['text']}{w['punctuation']}"
        )
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


# ---------- 大白话评估 ----------

def assess(full_text: str, words: list[dict]) -> None:
    n = len(words)
    timed = [w for w in words if w["begin_time"] is not None and w["end_time"] is not None]
    bad_order = sum(1 for w in timed if w["end_time"] <= w["begin_time"])
    overlaps = sum(
        1 for a, b in zip(timed, timed[1:]) if b["begin_time"] < a["end_time"]
    )
    total_ms = (timed[-1]["end_time"] - timed[0]["begin_time"]) if timed else 0
    avg_dur = (sum(w["end_time"] - w["begin_time"] for w in timed) / len(timed)) if timed else 0

    print("\n========== 大白话评估 ==========")
    print(f"· 识别出 {n} 个字，带时间戳 {len(timed)} 个；音频跨度约 {total_ms/1000:.1f} 秒。")
    print(f"· 平均每个字时长 {avg_dur:.0f} 毫秒（正常说话约 150–300ms/字，过大可能有粘连/停顿）。")
    print(f"· 时间戳健康度：起止颠倒 {bad_order} 处，前后重叠 {overlaps} 处（越少越好）。")
    print("· 准不准（错别字）：请人眼读一遍上面的『完整识别文本』，重点看专有名词/同音字。")
    print("· 对不对得齐：把 aliyun_words.srt 拖进剪辑软件，逐字看字幕是否压在对应发音上。")
    print("================================\n")


# ---------- 主流程 ----------

def main() -> None:
    ap = argparse.ArgumentParser(description="paraformer-v2 字级时间戳评测")
    ap.add_argument("--audio", help="本地音频文件（会上传 OSS 取公网直链）")
    ap.add_argument("--audio-url", help="已有的公网音频直链（给了就跳过 OSS）")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="输出目录")
    ap.add_argument("--model", default="paraformer-v2")
    ap.add_argument("--lang", default="zh,en", help="language_hints，逗号分隔")
    ap.add_argument("--env-file", default=str(DEFAULT_ENV_FILE), help="KEY=VALUE 凭证文件")
    args = ap.parse_args()

    load_env_file(Path(args.env_file))
    require_env(["DASHSCOPE_API_KEY"])
    langs = [s.strip() for s in args.lang.split(",") if s.strip()]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cleanup = None
    if args.audio_url:
        url = args.audio_url
    elif args.audio:
        audio = Path(args.audio).expanduser().resolve()
        if not audio.exists():
            sys.exit(f"音频文件不存在：{audio}")
        url, cleanup = upload_to_oss(audio)
    else:
        sys.exit("必须给 --audio 或 --audio-url 之一")

    try:
        result_json = transcribe(url, args.model, langs)
    finally:
        if cleanup:
            cleanup()

    full_text, words = extract_words(result_json)

    # 1) 完整文本
    print("\n========== 完整识别文本 ==========")
    print(full_text)

    # 2) 前 30 个字的字级时间戳
    print("\n========== 前 30 字字级时间戳 [开始ms - 结束ms] 字 ==========")
    for w in words[:30]:
        print(f"[{w['begin_time']} - {w['end_time']}]  {w['text']}{w['punctuation']}")

    # 3) 存 json
    json_path = out_dir / "aliyun_words.json"
    json_path.write_text(
        json.dumps(
            {"model": args.model, "source_url": url, "full_text": full_text, "words": words},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    # 4) 逐字 srt
    srt_path = out_dir / "aliyun_words.srt"
    write_srt(words, srt_path)
    print(f"\n已保存：{json_path}\n已保存：{srt_path}")

    # 5) 评估
    assess(full_text, words)


if __name__ == "__main__":
    main()
