# coding=utf-8
"""wechat 模块测试（含 wewe-rss 实际服务集成测试）"""

import sys

WeweRss_BASE = "http://localhost:4000"
WeweRss_AUTH = "123567"


def test_config_loading():
    print("=" * 60)
    print("TEST 1: wechat 配置加载")
    print("=" * 60)

    from trendradar.core.loader import load_config

    config = load_config()
    wechat = config.get("WECHAT", {})

    assert wechat is not None, "WECHAT config is None"
    assert "ENABLED" in wechat
    assert "WEWE_RSS_URL" in wechat
    assert "AUTH_CODE" in wechat
    assert "AUTO_START" in wechat
    assert "ACCOUNTS" in wechat

    assert wechat["ENABLED"] is False
    assert wechat["WEWE_RSS_URL"] == "http://localhost:4000"
    assert wechat["AUTO_START"] is False
    assert isinstance(wechat["ACCOUNTS"], list)

    print(f"  ENABLED:      {wechat['ENABLED']}")
    print(f"  WEWE_RSS_URL: {wechat['WEWE_RSS_URL']}")
    print(f"  AUTH_CODE:    {wechat['AUTH_CODE']}")
    print(f"  AUTO_START:   {wechat['AUTO_START']}")
    print(f"  ACCOUNTS:     {wechat['ACCOUNTS']}")
    print("  PASSED\n")


def test_service_health_check_unreachable():
    print("=" * 60)
    print("TEST 2: WeWeRssService 健康检查 (不可达端口)")
    print("=" * 60)

    from trendradar.crawler.wechat import WeWeRssService

    svc = WeWeRssService(base_url="http://localhost:19999", auth_code="test")

    result = svc.health_check(timeout=2)
    assert result is False
    print("  health_check (port 19999) -> False  PASSED\n")


def test_service_auto_start():
    print("=" * 60)
    print("TEST 3: WeWeRssService ensure_available (auto_start=True)")
    print("=" * 60)

    from trendradar.crawler.wechat import WeWeRssService

    svc = WeWeRssService(
        base_url="http://localhost:19999", auth_code="test", auto_start=True
    )

    result = svc.ensure_available(max_retries=1, retry_interval=1)
    assert result is False
    print("  ensure_available (auto_start=True, bad port) -> False  PASSED")

    svc.stop_service()
    print("  stop_service -> no crash  PASSED\n")


def test_discovery_unit():
    print("=" * 60)
    print("TEST 4: WeChatFeedDiscovery 单元测试")
    print("=" * 60)

    from trendradar.crawler.wechat import WeChatFeedDiscovery

    disc = WeChatFeedDiscovery(base_url="http://localhost:19999", auth_code="test")

    feeds = disc.discover_feeds([])
    assert feeds == []
    print("  discover_feeds (empty) -> []  PASSED")

    feeds2 = disc.discover_feeds(
        [{"name": "test", "feed_id": "auto", "enabled": False}]
    )
    assert feeds2 == []
    print("  discover_feeds (disabled) -> []  PASSED")

    feeds3 = disc.discover_feeds(
        [{"name": "test-mp", "feed_id": "abc123", "enabled": True}]
    )
    assert len(feeds3) == 1
    assert feeds3[0]["id"] == "wechat-abc123"
    assert feeds3[0]["url"] == "http://localhost:19999/feeds/abc123.rss"
    assert feeds3[0]["name"] == "微信: test-mp"
    print(f"  discover_feeds (manual) -> url={feeds3[0]['url']}  PASSED\n")


def test_name_to_feed_id():
    print("=" * 60)
    print("TEST 5: _name_to_feed_id")
    print("=" * 60)

    from trendradar.crawler.wechat.discovery import WeChatFeedDiscovery

    assert WeChatFeedDiscovery._name_to_feed_id("abc") == "abc"
    assert WeChatFeedDiscovery._name_to_feed_id("a b c") == "a_b_c"
    assert WeChatFeedDiscovery._name_to_feed_id("") == "unknown"
    assert len(WeChatFeedDiscovery._name_to_feed_id("x" * 100)) <= 50
    print("  all assertions PASSED\n")


def test_bridge():
    print("=" * 60)
    print("TEST 6: WeChatBridge")
    print("=" * 60)

    from trendradar.crawler.wechat import WeChatBridge

    bridge = WeChatBridge(wewe_rss_url=WeweRss_BASE)

    merged = bridge.merge_with_rss_feeds([], None)
    assert merged == []
    print("  merge (empty + None) -> []  PASSED")

    merged2 = bridge.merge_with_rss_feeds(
        [{"id": "wechat-test", "name": "W", "url": "http://x", "enabled": True}],
        [{"id": "rss-1", "name": "R", "url": "http://y", "enabled": True}],
    )
    assert len(merged2) == 2
    print(f"  merge (1+1) -> {len(merged2)} feeds  PASSED")

    result_none = bridge.fetch_wechat_feeds([])
    assert result_none is None
    print("  fetch (empty) -> None  PASSED\n")


def test_crawl_disabled_and_no_accounts():
    print("=" * 60)
    print("TEST 7: _crawl_wechat_data (disabled / no accounts)")
    print("=" * 60)

    from trendradar.core.loader import load_config
    from trendradar.__main__ import NewsAnalyzer

    config = load_config()
    config["WECHAT"]["ENABLED"] = False
    analyzer = NewsAnalyzer(config=config)
    items, new_items, raw_items, new_urls = analyzer._crawl_wechat_data()
    assert (
        items is None and new_items is None and raw_items is None and new_urls == set()
    )
    print("  disabled -> (None, None, None, set())  PASSED")

    config["WECHAT"]["ENABLED"] = True
    config["WECHAT"]["ACCOUNTS"] = []
    analyzer2 = NewsAnalyzer(config=config)
    items2, _, _, urls2 = analyzer2._crawl_wechat_data()
    assert items2 is None and urls2 == set()
    print("  no accounts -> (None, None, None, set())  PASSED\n")


def test_wewerss_service_live():
    print("=" * 60)
    print("TEST 8: wewe-rss 实际服务连通性")
    print("=" * 60)

    import requests

    try:
        r = requests.get(f"{WeweRss_BASE}/", timeout=5)
        assert r.status_code == 200, f"GET / -> {r.status_code}"
        print(f"  GET / -> {r.status_code}  PASSED")
    except Exception as e:
        print(f"  wewe-rss 服务不可达: {e}")
        print("  SKIPPED (wewe-rss not running)\n")
        return

    r2 = requests.get(f"{WeweRss_BASE}/feeds", timeout=5)
    assert r2.status_code == 200, f"GET /feeds -> {r2.status_code}"
    feeds = r2.json()
    print(f"  GET /feeds -> {r2.status_code}, data={feeds}  PASSED")

    r3 = requests.get(
        f"{WeweRss_BASE}/feeds",
        headers={"Authorization": f"Bearer {WeweRss_AUTH}"},
        timeout=5,
    )
    assert r3.status_code == 200
    print(f"  GET /feeds (auth) -> {r3.status_code}  PASSED\n")


def test_wewerss_discovery_live():
    print("=" * 60)
    print("TEST 9: WeChatFeedDiscovery 实际 API 连接")
    print("=" * 60)

    from trendradar.crawler.wechat import WeChatFeedDiscovery
    import requests

    try:
        requests.get(f"{WeweRss_BASE}/", timeout=3)
    except Exception:
        print("  SKIPPED (wewe-rss not running)\n")
        return

    disc = WeChatFeedDiscovery(base_url=WeweRss_BASE, auth_code=WeweRss_AUTH)

    api_feeds = disc._fetch_api_feeds()
    print(f"  _fetch_api_feeds() -> {api_feeds}")

    if api_feeds:
        print(f"  已订阅公众号数量: {len(api_feeds)}")
        for name, fid in list(api_feeds.items())[:5]:
            print(f"    - {name} (id={fid})")
    else:
        print("  当前无已订阅公众号（需要通过 wewe-rss Web 界面添加微信账号并订阅）")

    feeds = disc.discover_feeds(
        [
            {"name": "test-not-exist", "feed_id": "auto", "enabled": True},
        ]
    )
    print(f"  discover_feeds (auto, no match) -> {feeds}")
    assert feeds == [], "auto mode with no matching feed should return []"
    print("  PASSED\n")


def test_wewerss_service_health_check_live():
    print("=" * 60)
    print("TEST 10: WeWeRssService 健康检查 (实际服务)")
    print("=" * 60)

    from trendradar.crawler.wechat import WeWeRssService
    import requests

    try:
        requests.get(f"{WeweRss_BASE}/", timeout=3)
    except Exception:
        print("  SKIPPED (wewe-rss not running)\n")
        return

    svc = WeWeRssService(base_url=WeweRss_BASE, auth_code=WeweRss_AUTH)
    result = svc.health_check(timeout=5)
    assert result is True, f"health_check should return True, got {result}"
    print(f"  health_check -> True  PASSED")

    result2 = svc.ensure_available(max_retries=1, retry_interval=1)
    assert result2 is True
    print(f"  ensure_available -> True  PASSED\n")


if __name__ == "__main__":
    tests = [
        test_config_loading,
        test_service_health_check_unreachable,
        test_service_auto_start,
        test_discovery_unit,
        test_name_to_feed_id,
        test_bridge,
        test_crawl_disabled_and_no_accounts,
        test_wewerss_service_live,
        test_wewerss_discovery_live,
        test_wewerss_service_health_check_live,
    ]

    passed = 0
    failed = 0
    skipped = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"  FAILED: {e}\n")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {e}\n")
            import traceback

            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)
