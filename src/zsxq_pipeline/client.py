from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin

import requests

from .utils import ensure_dir, normalize_date, read_json, write_json


@dataclass
class FileCandidate:
    channel_id: str
    post_id: str
    file_id: str
    filename: str
    published_at: str
    download_url: str | None = None


@dataclass
class SearchFilesPage:
    candidates: list[FileCandidate]
    next_index: int | None


class SessionStore:
    def __init__(self, state_root: Path) -> None:
        self.path = ensure_dir(state_root) / "session.json"

    def save(self, cookie: str, user_agent: str) -> None:
        write_json(self.path, {"cookie": cookie, "user_agent": user_agent})

    def load(self) -> dict[str, str]:
        return read_json(self.path, {"cookie": "", "user_agent": "Mozilla/5.0"})


class ZsxqClient:
    def __init__(self, config: dict[str, Any], session: dict[str, str]) -> None:
        self.config = config
        self.session = requests.Session()
        self.base_url = config.get("base_url", "https://api.zsxq.com")
        user_agent = session.get("user_agent") or config.get("user_agent", "Mozilla/5.0")
        cookie = session.get("cookie") or config.get("cookie", "")
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Cookie": cookie,
                "Accept": "application/json, text/plain, */*",
            }
        )

    def fetch_group_files(self, group_id: str) -> list[FileCandidate]:
        topics = self.fetch_topics_page(group_id)
        return self._topics_to_file_candidates(group_id, topics)

    def fetch_group_files_since(
        self,
        group_id: str,
        *,
        since_date: str,
        max_pages: int = 100,
    ) -> list[FileCandidate]:
        all_candidates: list[FileCandidate] = []
        end_time: str | None = None
        seen_topic_ids: set[str] = set()

        for _ in range(max_pages):
            topics = self.fetch_topics_page(group_id, end_time=end_time)
            if not topics:
                break

            new_topics = []
            oldest_date_in_page: str | None = None
            for topic in topics:
                topic_id = str(topic.get("topic_id") or topic.get("id") or "")
                if topic_id and topic_id in seen_topic_ids:
                    continue
                if topic_id:
                    seen_topic_ids.add(topic_id)
                new_topics.append(topic)
                published_at = (
                    topic.get("create_time")
                    or topic.get("published_at")
                    or topic.get("time")
                    or ""
                )
                normalized = normalize_date(published_at)
                if normalized is not None:
                    oldest_date_in_page = normalized

            if not new_topics:
                break

            for topic in new_topics:
                published_at = (
                    topic.get("create_time")
                    or topic.get("published_at")
                    or topic.get("time")
                    or ""
                )
                normalized = normalize_date(published_at)
                if normalized is None or normalized >= since_date:
                    all_candidates.extend(self._topics_to_file_candidates(group_id, [topic]))

            last_topic_time = (
                new_topics[-1].get("create_time")
                or new_topics[-1].get("published_at")
                or new_topics[-1].get("time")
            )
            if not last_topic_time:
                break
            end_time = last_topic_time
            if oldest_date_in_page is not None and oldest_date_in_page < since_date:
                break

        return all_candidates

    def fetch_group_files_by_search(
        self,
        group_id: str,
        *,
        keywords: list[str],
        since_date: str,
        max_pages: int = 100,
    ) -> list[FileCandidate]:
        all_candidates: list[FileCandidate] = []
        seen_file_ids: set[str] = set()
        search_page_size = int(self.config.get("search_page_size", 10))

        for keyword in keywords:
            next_index: int | None = None
            seen_indexes: set[int] = set()
            for _ in range(max_pages):
                page = self.fetch_search_group_files_page(
                    group_id,
                    keyword=keyword,
                    count=search_page_size,
                    index=next_index,
                )
                if not page.candidates:
                    break

                for candidate in page.candidates:
                    normalized = normalize_date(candidate.published_at)
                    if normalized is not None and normalized < since_date:
                        continue
                    if candidate.file_id in seen_file_ids:
                        continue
                    seen_file_ids.add(candidate.file_id)
                    all_candidates.append(candidate)

                if page.next_index is None or page.next_index in seen_indexes:
                    break
                seen_indexes.add(page.next_index)
                next_index = page.next_index

        return all_candidates

    def fetch_search_group_files_page(
        self,
        group_id: str,
        *,
        keyword: str,
        count: int,
        index: int | None = None,
    ) -> SearchFilesPage:
        encoded_keyword = quote(keyword)
        path = f"/v2/search/groups/{group_id}/files?keyword={encoded_keyword}&count={count}"
        if index is not None:
            path += f"&index={index}"
        response = self.session.get(
            urljoin(self.base_url, path),
            headers={"Origin": "https://wx.zsxq.com", "Referer": "https://wx.zsxq.com/"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("succeeded"):
            return SearchFilesPage(candidates=[], next_index=None)

        resp_data = payload.get("resp_data", {})
        candidates: list[FileCandidate] = []
        for item in resp_data.get("files", []):
            file_info = item.get("file", {})
            file_id = str(file_info.get("file_id") or "")
            filename = file_info.get("name") or ""
            if not file_id or not filename:
                continue
            candidates.append(
                FileCandidate(
                    channel_id=str(group_id),
                    post_id=str(item.get("topic_id") or item.get("topic_uid") or ""),
                    file_id=file_id,
                    filename=filename,
                    published_at=file_info.get("create_time") or "",
                )
            )
        next_index = resp_data.get("index")
        return SearchFilesPage(candidates=candidates, next_index=next_index)

    def fetch_topics_page(self, group_id: str, *, end_time: str | None = None) -> list[dict[str, Any]]:
        count = self.config.get("topics_page_size", 20)
        template = self.config.get(
            "topics_url_template",
            "/v2/groups/{group_id}/topics?scope=all&count={count}",
        )
        url = urljoin(self.base_url, template.format(group_id=group_id, count=count))
        params = {}
        if end_time:
            params["end_time"] = end_time
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        return self._extract_topics(payload)

    def _topics_to_file_candidates(self, group_id: str, topics: list[dict[str, Any]]) -> list[FileCandidate]:
        candidates: list[FileCandidate] = []
        for topic in topics:
            post_id = str(topic.get("topic_id") or topic.get("id") or "")
            published_at = (
                topic.get("create_time")
                or topic.get("published_at")
                or topic.get("time")
                or ""
            )
            for file_item in self._walk_possible_files(topic):
                file_id = str(file_item.get("file_id") or file_item.get("id") or "")
                filename = (
                    file_item.get("name")
                    or file_item.get("file_name")
                    or file_item.get("title")
                    or ""
                )
                if not file_id or not filename:
                    continue
                candidates.append(
                    FileCandidate(
                        channel_id=str(group_id),
                        post_id=post_id,
                        file_id=file_id,
                        filename=filename,
                        published_at=published_at,
                        download_url=self._resolve_download_url(file_item, file_id),
                    )
                )
        return candidates

    def download_file(self, file_candidate: FileCandidate, destination: Path) -> None:
        download_url = file_candidate.download_url or self._download_url_for_id(file_candidate.file_id)
        response = self.session.get(download_url, timeout=60, stream=True)
        response.raise_for_status()
        ensure_dir(destination.parent)
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    handle.write(chunk)

    def _download_url_for_id(self, file_id: str) -> str:
        template = self.config.get("download_url_template", "/v2/files/{file_id}/download_url")
        response = self.session.get(urljoin(self.base_url, template.format(file_id=file_id)), timeout=30)
        response.raise_for_status()
        payload = response.json()
        for value in self._walk_values(payload):
            if isinstance(value, str) and value.startswith("http"):
                return value
        raise ValueError(f"无法从下载 URL 响应中解析出地址: {json.dumps(payload, ensure_ascii=False)[:200]}")

    def _extract_topics(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, dict):
            for key in ("topics", "list", "records"):
                if isinstance(payload.get(key), list):
                    return payload[key]
            resp_data = payload.get("resp_data")
            if isinstance(resp_data, dict):
                return self._extract_topics(resp_data)
        raise ValueError("无法从 topics 响应中解析主题列表，请检查接口配置。")

    def _walk_possible_files(self, node: Any) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        if isinstance(node, dict):
            if any(key in node for key in ("file_id", "file_name", "name")):
                found.append(node)
            for value in node.values():
                found.extend(self._walk_possible_files(value))
        elif isinstance(node, list):
            for item in node:
                found.extend(self._walk_possible_files(item))
        return found

    def _resolve_download_url(self, file_item: dict[str, Any], file_id: str) -> str | None:
        for key in ("download_url", "url"):
            value = file_item.get(key)
            if isinstance(value, str) and value.startswith("http"):
                return value
        try:
            return self._download_url_for_id(file_id)
        except Exception:
            return None

    def _walk_values(self, node: Any):
        if isinstance(node, dict):
            for value in node.values():
                yield value
                yield from self._walk_values(value)
        elif isinstance(node, list):
            for item in node:
                yield item
                yield from self._walk_values(item)
