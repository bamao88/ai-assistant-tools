"""转写后端：音频公网 URL → 归一化字级词表。

统一输出 schema（与 twostage/resolve.py 的 load_paraformer_words 对齐，毫秒）：
    {"model","source_url","full_text","words":[{"text","begin_time","end_time"}]}

两个后端：
- volc  ：火山 seedasr v3（大模型录音文件识别，异步 submit/query）。**主用**。
- aliyun：阿里云百炼 paraformer-v2（移植自 video-research spike）。**兜底**（火山额度用尽/失败时）。

后端失败统一抛 BackendError，编排层据此切兜底。
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from http import HTTPStatus


class BackendError(RuntimeError):
    """后端转写失败（含额度用尽、提交失败、轮询超时）——触发编排层切兜底。"""


def _log(m: str) -> None:
    print(m, file=sys.stderr, flush=True)


# ============ 火山 seedasr v3（主）============

_VOLC_BASE = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/"
_VOLC_RESOURCE = "volc.seedasr.auc"


def _volc_post(path: str, reqid: str, body: dict, key: str) -> tuple[str | None, str]:
    """POST submit/query。状态码在响应头 X-Api-Status-Code；返回 (code, body_text)。"""
    req = urllib.request.Request(
        _VOLC_BASE + path,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-api-key": key,
            "X-Api-Resource-Id": _VOLC_RESOURCE,
            "X-Api-Request-Id": reqid,
            "X-Api-Sequence": "-1",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            code = r.headers.get("X-Api-Status-Code")
            payload = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:  # noqa: PERF203
        code = e.headers.get("X-Api-Status-Code") if e.headers else None
        payload = e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        raise BackendError(f"火山请求异常：{e}") from e
    return code, payload


def _volc_extract(result_json: dict) -> tuple[str, list[dict], list[dict]]:
    """result.utterances[] → (整段文本, 字级词表, 原生语义句)。
    保留三样火山原生信息：utterances 语义句(带句级时间戳)、句内带标点的 text、整段 ITN 文本。"""
    result = result_json.get("result") or {}
    words: list[dict] = []
    sentences: list[dict] = []
    for u in result.get("utterances", []):
        su, eu = u.get("start_time"), u.get("end_time")
        tu = (u.get("text") or "").strip()                  # 句子文本（含标点）
        if tu and su is not None and eu is not None and su >= 0:
            sentences.append({"text": tu, "begin_time": int(su), "end_time": int(eu)})
        for w in u.get("words", []):
            st, et = w.get("start_time"), w.get("end_time")
            txt = (w.get("text") or "").strip()
            if st is None or et is None or st < 0 or et < 0 or not txt:  # st<0 = 标点占位，跳过(标点在句 text 里)
                continue
            words.append({"text": txt, "begin_time": int(st), "end_time": int(et)})
    words.sort(key=lambda x: x["begin_time"])
    sentences.sort(key=lambda s: s["begin_time"])
    full_text = result.get("text") or "".join(w["text"] for w in words)  # result.text 已 ITN(数字书面化)
    return full_text, words, sentences


def transcribe_volc(url: str, *, fmt: str = "mp3", poll_secs: int = 5, max_polls: int = 600) -> dict:
    """火山异步转写：submit → 轮询 query → 归一化词表。失败抛 BackendError。"""
    key = os.environ.get("VOLCENGINE_API_KEY")
    if not key:
        raise BackendError("缺 VOLCENGINE_API_KEY（语音服务 key，非方舟 key；填 var/credentials/）")

    reqid = str(uuid.uuid4())  # submit 与 query 必须同一个
    body = {
        "user": {"uid": "videocut"},
        "audio": {"url": url, "format": fmt},
        "request": {"model_name": "bigmodel", "enable_itn": True, "enable_punc": True, "show_utterances": True},
    }
    code = None
    for _ in range(5):
        code, _ = _volc_post("submit", reqid, body, key)
        _log(f"[volc] submit code={code}")
        if code == "20000000":
            break
        time.sleep(6)
    if code != "20000000":
        raise BackendError(f"火山 submit 失败 code={code}")

    _log("[volc] 转写中，轮询 query…")
    fails = 0
    for n in range(max_polls):
        time.sleep(poll_secs)
        code, payload = _volc_post("query", reqid, {}, key)
        if code == "20000000":
            full_text, words, sentences = _volc_extract(json.loads(payload))
            if not words:
                raise BackendError("火山结果无字级词")
            _log(f"[volc] 完成：{len(words)} 字 / {len(sentences)} 句(原生语义)")
            return {"model": _VOLC_RESOURCE, "source_url": url, "full_text": full_text,
                    "words": words, "sentences": sentences}
        if code in ("20000001", "20000002"):  # 排队/处理中
            if n % 12 == 0:
                _log(f"[volc] …处理中 {n * poll_secs}s code={code}")
            fails = 0
            continue
        fails += 1
        _log(f"[volc] query 异常 code={code} (fails={fails})")
        if fails > 40:
            raise BackendError(f"火山 query 连续失败 code={code}")
    raise BackendError("火山轮询超时")


# ============ 阿里 paraformer-v2（兜底）============

def transcribe_aliyun(url: str, *, model: str = "paraformer-v2", langs: tuple[str, ...] = ("zh", "en")) -> dict:
    """阿里云百炼 paraformer-v2 异步识别（移植自 video-research spike）。需 dashscope。"""
    try:
        import dashscope
        from dashscope.audio.asr import Transcription
    except ImportError as e:  # noqa: BLE001
        raise BackendError("阿里兜底需要 `pip install dashscope`") from e

    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise BackendError("缺 DASHSCOPE_API_KEY（填 var/credentials/aliyun.env）")
    dashscope.api_key = api_key

    def _attr(obj, k, d=None):
        if obj is None:
            return d
        return obj.get(k, d) if isinstance(obj, dict) else getattr(obj, k, d)

    _log(f"[aliyun] 提交 paraformer model={model}")
    task = Transcription.async_call(model=model, file_urls=[url], language_hints=list(langs))
    task_id = _attr(_attr(task, "output"), "task_id")
    if not task_id:
        raise BackendError(f"阿里提交失败：{getattr(task, 'message', task)}")
    resp = Transcription.wait(task=task_id)
    if getattr(resp, "status_code", None) != HTTPStatus.OK:
        raise BackendError(f"阿里任务失败 status={getattr(resp, 'status_code', '?')}")
    results = _attr(_attr(resp, "output"), "results") or []
    if not results or _attr(results[0], "subtask_status") not in (None, "SUCCEEDED"):
        raise BackendError(f"阿里无有效结果：{_attr(resp, 'output')}")
    trans_url = _attr(results[0], "transcription_url")
    if not trans_url:
        raise BackendError("阿里结果缺 transcription_url")

    with urllib.request.urlopen(trans_url, timeout=60) as r:
        rj = json.loads(r.read().decode("utf-8"))
    transcripts = rj.get("transcripts") or []
    if not transcripts:
        raise BackendError("阿里结果无 transcripts")
    t0 = transcripts[0]
    words: list[dict] = []
    for sent in t0.get("sentences", []):
        for w in sent.get("words", []):
            b, e = w.get("begin_time"), w.get("end_time")
            txt = (w.get("text") or "").strip()
            if b is None or e is None or not txt:
                continue
            words.append({"text": txt, "begin_time": int(b), "end_time": int(e)})
    if not words:
        raise BackendError("阿里结果无字级词")
    full_text = t0.get("text") or "".join(w["text"] for w in words)
    _log(f"[aliyun] 完成：{len(words)} 字")
    return {"model": model, "source_url": url, "full_text": full_text, "words": words}


def resolve_backend(name: str):
    if name == "volc":
        return transcribe_volc
    if name == "aliyun":
        return transcribe_aliyun
    raise ValueError(f"未知 backend：{name}（volc | aliyun）")
