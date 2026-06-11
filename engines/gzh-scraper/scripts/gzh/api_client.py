"""HTTP 客户端，封装 wechat-article-exporter API。"""

from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import get_auth_key, get_exporter_url

logger = logging.getLogger("gzh-api")

# 微信限流，默认请求间隔
REQUEST_INTERVAL = 3  # 秒


class APIError(Exception):
    """API 调用错误。"""

    def __init__(self, message: str, code: int = -1):
        super().__init__(message)
        self.code = code


class ExporterClient:
    """wechat-article-exporter HTTP 客户端。"""

    def __init__(self, base_url: str = "", auth_key: str = ""):
        self.base_url = (base_url or get_exporter_url()).rstrip("/")
        self.auth_key = auth_key or get_auth_key()
        self._last_request_time = 0.0

    def _throttle(self) -> None:
        """请求限流，避免微信封号。"""
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_INTERVAL:
            time.sleep(REQUEST_INTERVAL - elapsed)

    def _request(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """发送 GET 请求到 exporter 服务。"""
        self._throttle()

        url = f"{self.base_url}{path}"
        if params:
            url += "?" + urlencode(params)

        req = Request(url)
        req.add_header("X-Auth-Key", self.auth_key)
        req.add_header("Accept", "application/json")

        try:
            self._last_request_time = time.time()
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            raise APIError(f"HTTP {e.code}: {e.reason}", e.code) from e
        except URLError as e:
            raise APIError(f"连接失败: {e.reason}（exporter 服务是否在运行？）") from e
        except json.JSONDecodeError as e:
            raise APIError(f"JSON 解析失败: {e}") from e

        # 检查微信 API 错误
        base_resp = data.get("base_resp", {})
        ret = base_resp.get("ret", 0)
        if ret != 0:
            err_msg = base_resp.get("err_msg", "未知错误")
            raise APIError(err_msg, ret)

        return data

    def check_auth(self) -> dict[str, Any]:
        """检查登录状态，返回用户信息。"""
        try:
            data = self._request("/api/web/mp/info")
            nick_name = data.get("nick_name", "")
            if not nick_name and data.get("error"):
                return {"authenticated": False, "error": data["error"]}
            return {
                "authenticated": bool(nick_name),
                "nick_name": nick_name,
                "head_img": data.get("head_img", ""),
            }
        except APIError as e:
            return {"authenticated": False, "error": str(e)}

    def search_accounts(
        self, keyword: str, begin: int = 0, size: int = 5
    ) -> list[dict[str, Any]]:
        """搜索公众号。"""
        data = self._request(
            "/api/web/mp/searchbiz",
            {"keyword": keyword, "begin": begin, "size": size},
        )
        raw_list = data.get("list", [])
        return raw_list

    def list_articles(
        self,
        fakeid: str,
        keyword: str = "",
        begin: int = 0,
        size: int = 5,
    ) -> dict[str, Any]:
        """获取指定公众号的文章列表。

        返回 {"articles": [...], "total": int}
        """
        data = self._request(
            "/api/web/mp/appmsgpublish",
            {"id": fakeid, "keyword": keyword, "begin": begin, "size": size},
        )

        # appmsgpublish 返回的数据结构较复杂，需要解析 publish_page
        publish_page = data.get("publish_page", {})
        if isinstance(publish_page, str):
            publish_page = json.loads(publish_page)

        publish_list = publish_page.get("publish_list", [])
        total = publish_page.get("total_count", 0)

        articles = []
        for item in publish_list:
            publish_info = item.get("publish_info", {})
            if isinstance(publish_info, str):
                publish_info = publish_info.strip()
                if not publish_info:
                    continue
                try:
                    publish_info = json.loads(publish_info)
                except json.JSONDecodeError:
                    continue
            appmsgex = publish_info.get("appmsgex", [])
            for msg in appmsgex:
                articles.append({
                    "aid": msg.get("aid", ""),
                    "title": msg.get("title", ""),
                    "link": msg.get("link", ""),
                    "cover": msg.get("cover", ""),
                    "digest": msg.get("digest", ""),
                    "create_time": msg.get("create_time", 0),
                    "update_time": msg.get("update_time", 0),
                })

        return {"articles": articles, "total": total}

    def download_article_html(self, url: str) -> str:
        """下载文章 HTML 内容（分块读取，避免大文章 IncompleteRead）。"""
        req = Request(url)
        req.add_header(
            "User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        try:
            with urlopen(req, timeout=60) as resp:
                chunks = []
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                return b"".join(chunks).decode("utf-8")
        except Exception as e:
            raise APIError(f"下载文章失败: {e}") from e
