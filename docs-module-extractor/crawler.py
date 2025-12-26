import asyncio
import time
import logging
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import aiohttp
import requests
from bs4 import BeautifulSoup

from config import config
from utils import CacheManager, clean_text, extract_domain, normalize_url

# ---------------- LOGGING SETUP ----------------
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


class AsyncCrawler:
    """Asynchronous web crawler for documentation sites."""

    def __init__(self):
        self.cache = CacheManager()
        self.visited_urls: Set[str] = set()
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore: Optional[asyncio.Semaphore] = None

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
        self.session = aiohttp.ClientSession(
            connector=connector,
            headers={"User-Agent": config.USER_AGENT},
            timeout=aiohttp.ClientTimeout(total=config.REQUEST_TIMEOUT)
        )
        self.semaphore = asyncio.Semaphore(5)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def fetch_page(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        async with self.semaphore:
            try:
                cache_key = self.cache.get_key(url, "crawl")
                cached = self.cache.get(cache_key)

                if cached and config.CACHE_ENABLED:
                    return cached.get("content"), cached.get("html")

                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to fetch {url}: {response.status}")
                        return None, None

                    html = await response.text()
                    soup = BeautifulSoup(html, "lxml")
                    content = self.extract_meaningful_content(soup)

                    if config.CACHE_ENABLED:
                        self.cache.set(
                            cache_key,
                            {
                                "content": content,
                                "html": html,
                                "timestamp": time.time(),
                            },
                        )

                    return content, html

            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                return None, None

    def extract_meaningful_content(self, soup: BeautifulSoup) -> str:
        for selector in config.IGNORE_SELECTORS:
            for element in soup.select(selector):
                element.decompose()

        content_areas = []
        for tag in config.CONTENT_TAGS:
            elements = (
                soup.select(tag) if "." in tag or "#" in tag else soup.find_all(tag)
            )
            for element in elements:
                text = element.get_text(strip=True)
                if len(text) > config.MIN_CONTENT_LENGTH:
                    content_areas.append(text)

        if not content_areas:
            body = soup.find("body")
            if body:
                content_areas.append(body.get_text(strip=True))

        combined = " ".join(content_areas)
        return clean_text(combined)

    async def extract_links(self, url: str, html: str, base_domain: str) -> List[str]:
        soup = BeautifulSoup(html, "lxml")
        links = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]

            if href.startswith("#") or href.startswith("javascript:"):
                continue

            absolute_url = urljoin(url, href)
            normalized_url = normalize_url(absolute_url)

            if self.is_internal_link(normalized_url, base_domain):
                links.append(normalized_url)

        return list(set(links))

    def is_internal_link(self, url: str, base_domain: str) -> bool:
        try:
            parsed = urlparse(url)
            return parsed.netloc == base_domain or parsed.netloc == ""
        except Exception:
            return False

    async def crawl_documentation(
        self,
        start_url: str,
        max_depth: int = 3,
        max_pages: int = 50,
    ) -> Dict[str, Dict]:
        base_domain = extract_domain(start_url)
        results = {}

        async def crawl_recursive(url: str, depth: int, domain: str):
            if (
                depth > max_depth
                or len(results) >= max_pages
                or url in self.visited_urls
            ):
                return

            self.visited_urls.add(url)
            logger.info(f"Crawling: {url} (depth: {depth})")

            content, html = await self.fetch_page(url)

            if content and html:
                results[url] = {
                    "url": url,
                    "content": content,
                    "html": html,
                    "depth": depth,
                    "title": self.extract_title(html),
                }

                if depth < max_depth:
                    links = await self.extract_links(url, html, domain)
                    tasks = [
                        crawl_recursive(link, depth + 1, domain)
                        for link in links[:10]
                        if link not in self.visited_urls
                    ]
                    if tasks:
                        await asyncio.gather(*tasks)

        await crawl_recursive(start_url, 0, base_domain)
        return results

    def extract_title(self, html: str) -> str:
        try:
            soup = BeautifulSoup(html, "lxml")
            title_tag = soup.find("title")
            return clean_text(title_tag.text) if title_tag else "Untitled"
        except Exception:
            return "Untitled"


class SyncCrawler:
    """Synchronous crawler for simpler use cases."""

    def __init__(self):
        self.cache = CacheManager()
        self.visited_urls = set()

    def crawl_documentation(
        self,
        start_url: str,
        max_depth: int = 3,
        max_pages: int = 50,
    ) -> Dict[str, Dict]:
        async def async_crawl():
            async with AsyncCrawler() as crawler:
                return await crawler.crawl_documentation(
                    start_url, max_depth, max_pages
                )

        return asyncio.run(async_crawl())
