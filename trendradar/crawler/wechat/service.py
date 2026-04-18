# coding=utf-8
"""
wewe-rss 服务管理

负责 wewe-rss 服务的健康检查和自动启动。
"""

import subprocess
import time
from pathlib import Path
from typing import Optional

import requests


class WeWeRssService:
    """wewe-rss 服务管理器"""

    def __init__(self, base_url: str, auth_code: str = "", auto_start: bool = False):
        self.base_url = base_url.rstrip("/")
        self.auth_code = auth_code
        self.auto_start = auto_start
        self._process: Optional[subprocess.Popen] = None

    def health_check(self, timeout: int = 5) -> bool:
        """
        检查 wewe-rss 服务是否可达

        Args:
            timeout: 请求超时时间（秒）

        Returns:
            服务是否可达
        """
        try:
            url = f"{self.base_url}/feeds"
            headers = {}
            if self.auth_code:
                headers["Authorization"] = f"Bearer {self.auth_code}"
            response = requests.get(url, headers=headers, timeout=timeout)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def ensure_available(self, max_retries: int = 3, retry_interval: int = 3) -> bool:
        """
        确保 wewe-rss 服务可用

        如果服务不可达且 auto_start 为 True，尝试自动启动服务。
        如果服务不可达且 auto_start 为 False，输出警告但不中断。

        Args:
            max_retries: 健康检查最大重试次数
            retry_interval: 重试间隔（秒）

        Returns:
            服务是否最终可用
        """
        if self.health_check():
            print("[微信] wewe-rss 服务连接成功")
            return True

        if not self.auto_start:
            print(f"[微信] wewe-rss 服务不可达 ({self.base_url})，auto_start=false，跳过微信公众号数据获取")
            return False

        print("[微信] wewe-rss 服务不可达，尝试自动启动...")
        if not self._start_service():
            print("[微信] wewe-rss 服务自动启动失败")
            return False

        print("[微信] 等待 wewe-rss 服务就绪...")
        for attempt in range(1, max_retries + 1):
            time.sleep(retry_interval)
            if self.health_check():
                print(f"[微信] wewe-rss 服务已就绪（第 {attempt} 次检查成功）")
                return True
            print(f"[微信] 等待中...（{attempt}/{max_retries}）")

        print("[微信] wewe-rss 服务启动超时，跳过微信公众号数据获取")
        return False

    def _start_service(self) -> bool:
        """
        尝试启动 wewe-rss 服务

        Returns:
            是否成功发起启动
        """
        wewe_rss_dir = Path(__file__).resolve().parent.parent.parent.parent / "wewe-rss"
        if not wewe_rss_dir.exists():
            print(f"[微信] wewe-rss 目录不存在: {wewe_rss_dir}")
            print("[微信] 请执行: git submodule update --init --recursive")
            return False

        try:
            self._process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=str(wewe_rss_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, 'CREATE_NEW_PROCESS_GROUP') else 0,
            )
            return True
        except FileNotFoundError:
            print("[微信] 未找到 npm 命令，请确保已安装 Node.js")
            return False
        except OSError as e:
            print(f"[微信] 启动 wewe-rss 服务失败: {e}")
            return False

    def stop_service(self) -> None:
        """停止 wewe-rss 服务（仅限自动启动的服务）"""
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            print("[微信] wewe-rss 服务已停止")
            self._process = None
