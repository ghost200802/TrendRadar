# coding=utf-8
"""
微信公众号到 RSS 的桥接模块

将微信公众号 feed 注入到 TrendRadar 的 RSS 抓取流程中，
复用 RSSFetcher 进行数据抓取。
"""

from typing import Dict, List, Optional, Tuple

from trendradar.crawler.rss import RSSFetcher, RSSFeedConfig
from trendradar.storage.base import RSSData


class WeChatBridge:
    """
    微信公众号到 RSS 的桥接器

    将 wewe-rss 发现的公众号 feed 转换为 RSSFeedConfig，
    注入到现有的 RSS 抓取流程中。
    """

    def __init__(
        self,
        wewe_rss_url: str,
        auth_code: str = "",
        request_interval: int = 2000,
        timeout: int = 15,
        use_proxy: bool = False,
        proxy_url: str = "",
        timezone: str = "Asia/Shanghai",
        freshness_enabled: bool = True,
        default_max_age_days: int = 1,
    ):
        self.wewe_rss_url = wewe_rss_url
        self.auth_code = auth_code
        self.request_interval = request_interval
        self.timeout = timeout
        self.use_proxy = use_proxy
        self.proxy_url = proxy_url
        self.timezone = timezone
        self.freshness_enabled = freshness_enabled
        self.default_max_age_days = default_max_age_days

    def fetch_wechat_feeds(
        self, discovered_feeds: List[Dict]
    ) -> Optional[RSSData]:
        """
        使用 RSSFetcher 抓取微信公众号 RSS 数据

        Args:
            discovered_feeds: 发现的 feed 列表，每项包含 id, name, url, enabled

        Returns:
            RSSData 对象，失败返回 None
        """
        if not discovered_feeds:
            return None

        feeds = []
        for feed_info in discovered_feeds:
            if not feed_info.get("enabled", True):
                continue

            feed = RSSFeedConfig(
                id=feed_info.get("id", ""),
                name=feed_info.get("name", ""),
                url=feed_info.get("url", ""),
                max_items=50,
                enabled=True,
                max_age_days=None,
            )
            feeds.append(feed)

        if not feeds:
            return None

        fetcher = RSSFetcher(
            feeds=feeds,
            request_interval=self.request_interval,
            timeout=self.timeout,
            use_proxy=self.use_proxy,
            proxy_url=self.proxy_url,
            timezone=self.timezone,
            freshness_enabled=self.freshness_enabled,
            default_max_age_days=self.default_max_age_days,
        )

        try:
            return fetcher.fetch_all()
        except Exception as e:
            print(f"[微信] 抓取微信公众号 RSS 数据失败: {e}")
            return None

    def merge_with_rss_feeds(
        self,
        wechat_feeds: List[Dict],
        existing_feeds: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """
        将微信公众号 feed 合并到现有 RSS feed 列表中

        Args:
            wechat_feeds: 微信公众号 feed 列表
            existing_feeds: 现有 RSS feed 配置列表

        Returns:
            合并后的 feed 配置列表
        """
        if not wechat_feeds:
            return existing_feeds or []

        merged = list(existing_feeds) if existing_feeds else []

        wechat_ids = {f.get("id") for f in wechat_feeds}
        existing_ids = {f.get("id") for f in merged}

        for feed in wechat_feeds:
            feed_id = feed.get("id", "")
            if feed_id and feed_id not in existing_ids:
                merged.append({
                    "id": feed_id,
                    "name": feed.get("name", ""),
                    "url": feed.get("url", ""),
                    "enabled": feed.get("enabled", True),
                    "max_age_days": feed.get("max_age_days"),
                })

        return merged
