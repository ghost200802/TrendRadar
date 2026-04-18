# coding=utf-8
"""
微信公众号 RSS Feed 自动发现

通过 wewe-rss API 获取已订阅公众号的 RSS feed 列表，
并转换为 TrendRadar 可用的 RSS feed URL。
"""

from typing import Dict, List, Optional, Tuple

import requests


class WeChatFeedDiscovery:
    """微信公众号 RSS Feed 发现器"""

    def __init__(self, base_url: str, auth_code: str = ""):
        self.base_url = base_url.rstrip("/")
        self.auth_code = auth_code

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.auth_code:
            headers["Authorization"] = f"Bearer {self.auth_code}"
        return headers

    def discover_feeds(self, accounts: List[Dict]) -> List[Dict]:
        """
        从 wewe-rss 服务发现公众号 RSS feed

        对于 feed_id="auto" 的公众号，通过 API 自动发现；
        对于指定了 feed_id 的公众号，直接构造 URL。

        Args:
            accounts: 公众号配置列表，每个包含 name, feed_id, enabled

        Returns:
            可用 feed 列表，每项包含 id, name, url, enabled
        """
        if not accounts:
            return []

        results = []

        # 首先尝试通过 API 获取所有已订阅的 feed 列表
        api_feed_map: Dict[str, str] = {}
        try:
            api_feeds = self._fetch_api_feeds()
            if api_feeds:
                api_feed_map = api_feeds
        except Exception as e:
            print(f"[微信] 获取 wewe-rss feed 列表失败: {e}")

        for account in accounts:
            if not account.get("enabled", True):
                continue

            name = account.get("name", "")
            feed_id = account.get("feed_id", "auto")

            if not name:
                continue

            if feed_id == "auto":
                # 自动发现模式：从 API 返回的列表中匹配
                discovered_url = self._match_feed_by_name(name, api_feed_map)
                if discovered_url:
                    safe_id = self._name_to_feed_id(name)
                    results.append({
                        "id": f"wechat-{safe_id}",
                        "name": f"微信: {name}",
                        "url": discovered_url,
                        "enabled": True,
                    })
                    print(f"[微信] 自动发现: {name} -> {safe_id}")
                else:
                    print(f"[微信] 未找到公众号 '{name}' 的 RSS feed（请确认已在 wewe-rss 中订阅）")
            else:
                # 手动指定 feed_id 模式
                url = self._build_feed_url(feed_id)
                safe_id = feed_id
                results.append({
                    "id": f"wechat-{safe_id}",
                    "name": f"微信: {name}",
                    "url": url,
                    "enabled": True,
                })
                print(f"[微信] 手动配置: {name} -> {safe_id}")

        return results

    def _fetch_api_feeds(self) -> Optional[Dict[str, str]]:
        """
        从 wewe-rss API 获取已订阅公众号的 feed 列表

        Returns:
            {公众号名称: feed_id} 映射字典，失败返回 None
        """
        try:
            url = f"{self.base_url}/feeds"
            headers = self._get_headers()

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            feed_map = {}

            feeds = data if isinstance(data, list) else data.get("data", data.get("feeds", []))

            for feed in feeds:
                if isinstance(feed, dict):
                    feed_name = feed.get("mpName", "") or feed.get("name", "")
                    feed_id = str(feed.get("id", ""))
                    if feed_name and feed_id:
                        feed_map[feed_name] = feed_id

            return feed_map if feed_map else None

        except requests.RequestException as e:
            print(f"[微信] API 请求失败: {e}")
            return None
        except (ValueError, KeyError) as e:
            print(f"[微信] API 响应解析失败: {e}")
            return None

    def _match_feed_by_name(self, name: str, feed_map: Dict[str, str]) -> Optional[str]:
        """
        按公众号名称匹配 feed

        Args:
            name: 公众号名称
            feed_map: {公众号名称: feed_id} 映射

        Returns:
            匹配到的 feed URL，未匹配返回 None
        """
        # 精确匹配
        if name in feed_map:
            return self._build_feed_url(feed_map[name])

        # 模糊匹配：包含关系
        for feed_name, feed_id in feed_map.items():
            if name in feed_name or feed_name in name:
                return self._build_feed_url(feed_id)

        return None

    def _build_feed_url(self, feed_id: str) -> str:
        """构造 RSS feed URL"""
        return f"{self.base_url}/feeds/{feed_id}.rss"

    @staticmethod
    def _name_to_feed_id(name: str) -> str:
        """将公众号名称转换为安全的 feed ID"""
        import re
        safe = re.sub(r'[^\w\u4e00-\u9fff]', '_', name).strip('_')
        return safe[:50] if safe else "unknown"
