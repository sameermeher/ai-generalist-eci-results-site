"""Base scraper with retry, rate-limiting, HTML staging, and structured logging."""

import logging
import random
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import settings

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "curl/8.7.1",
    "Accept": "*/*",
    "Connection": "keep-alive",
}

_RETRYABLE_EXCEPTIONS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
)


class BaseScraper:
    """Thread-safe base class for all ECI page scrapers.

    Provides:
    - HTTP GET with exponential-backoff retry
    - Rate limiting (configurable delay + jitter)
    - Raw HTML staging to disk
    - BeautifulSoup parsing helper
    """

    def __init__(
        self,
        base_url: str = settings.eci_base_url,
        raw_data_dir: Optional[Path] = None,
        rate_limit_delay: float = settings.scraper_rate_limit_delay,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.raw_data_dir = raw_data_dir or settings.raw_data_path
        self.rate_limit_delay = rate_limit_delay
        self._session = requests.Session()
        self._session.headers.update(_HEADERS)
        self._last_request_time: float = 0.0
        self._session_warmed: bool = False

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def _warm_session(self) -> None:
        """Visit the ECI index page once to acquire session cookies."""
        if self._session_warmed:
            return
        try:
            index_url = f"{self.base_url}/index.htm"
            self._session.get(index_url, timeout=settings.scraper_timeout)
            logger.debug("Session warmed via %s", index_url)
        except Exception as exc:
            logger.debug("Session warm-up skipped: %s", exc)
        finally:
            self._session_warmed = True

    def fetch(self, path: str) -> str:
        """Fetch a URL (relative or absolute) and return the HTML body."""
        self._warm_session()
        url = path if path.startswith("http") else f"{self.base_url}/{path.lstrip('/')}"
        self._rate_limit()
        html = self._fetch_with_retry(url)
        logger.debug("Fetched %s (%d bytes)", url, len(html))
        return html

    def fetch_and_stage(self, path: str, stage_path: Path) -> str:
        """Fetch URL, save raw HTML to disk, and return HTML."""
        stage_path.parent.mkdir(parents=True, exist_ok=True)
        if stage_path.exists():
            logger.debug("Cache hit: %s", stage_path)
            return stage_path.read_text(encoding="utf-8")
        html = self.fetch(path)
        stage_path.write_text(html, encoding="utf-8")
        logger.info("Staged: %s", stage_path)
        return html

    @staticmethod
    def parse(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "BaseScraper":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        jitter = random.uniform(0, self.rate_limit_delay * 0.5)
        wait = self.rate_limit_delay + jitter - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_time = time.monotonic()

    @retry(
        retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
        stop=stop_after_attempt(settings.scraper_max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _fetch_with_retry(self, url: str) -> str:
        resp = self._session.get(url, timeout=settings.scraper_timeout)
        # Retry on transient server errors and rate-limit responses
        if resp.status_code in (429, 503):
            raise requests.exceptions.ConnectionError(
                f"Retryable status {resp.status_code} for {url}"
            )
        resp.raise_for_status()
        return resp.text
