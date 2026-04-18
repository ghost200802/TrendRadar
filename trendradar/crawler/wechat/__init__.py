# coding=utf-8
"""
微信公众号数据获取模块

通过 wewe-rss 项目将微信公众号文章转换为标准 RSS 格式，
复用 TrendRadar 已有的 RSS 抓取、AI 筛选/分析、多渠道通知推送等能力。
"""

from .service import WeWeRssService
from .discovery import WeChatFeedDiscovery
from .bridge import WeChatBridge

__all__ = ["WeWeRssService", "WeChatFeedDiscovery", "WeChatBridge"]
