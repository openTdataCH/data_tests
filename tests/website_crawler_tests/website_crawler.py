"""A module to perform web crawler tests on a given website. The main class is the WebsiteCrawler.
The WebsiteCrawler checks a given "backlog" of URLs and checks their http response (status code, size).
WebsiteCrawler initialization parameters:
- initial backlog of URLs.
- initial_backlog: the initial list of URLs to check.
- own_site_url_stems: URLs of our "own" website. Any of your "own" URLs must begin with one of the stems.
  (default: same as initial_backlog).
- ignore_urls: list of URLs that should not be checked.
- logger: a logger for producing logs (info() messages.
- log_sampling: a number n > 1 to log only samples (every n message).

Further hints:
- any URL is canonized and then entered only once.
- only relevant URLs are checked, basically only HTML pages. Images, CSS, etc. are ignored.
- URLs are either "own" (based on URL stems) or "other".
- all URLs in the backlog are visited once, and the response code, size, etc. is recorded.
- for own URLs, the response is parsed and all relevant URLs are entered in the backlog.
- each URL also registers all places it is found in (initial backlog or other pages)
- The backlog is processed until all pages have been visited.
- at the end, detailed statistics can be retrieved from the self.backlog.
"""

import sys
from collections import defaultdict

import logging
import re
import requests
from datetime import datetime as dt
from enum import Enum
from typing import Iterable

NOT_RELEVANT_URL_ENDINGS = [".css", ".js", ".ico", ".svg", ".png", ".jpg", ".gif", ".php", ".jsonld", ".n3", ".ttl",
                         ".xml", ".json", ".zip", ".pdf", ".jpeg", "wp-json", ".xlsx", ".csv", ".txt", "embed",
                         ".woff2", ".ttf"]

NOT_RELEVANT_URL_CONTAINS = ["/resource/"]


class UrlType(Enum):
    OWN = 0
    OTHER = 1
    DO_NOT_FOLLOW = 2


def canonize_url(url: str) -> str:
    while url[-1] in "/&":
        url = url[:-1]
    return url.lower()


def defuse(text: str) -> str:
    text = str(text).replace('\n', ' ').replace('\t', ' ').replace('\r', ' ')
    text = text.replace(r'<', '&lt;').replace(r'>', '&gt;').replace(r'&', '&amp;').replace(r'"', '&quot;').replace("'", "&apos;")
    return text


class WebPage:
    """Class for handling a single webpage to be visited, with it's URL, response exerpt, code, etc."""

    def __init__(self, url: str, own: bool = False, excerpt_length=100):
        self.url_str = canonize_url(url)
        self.own = own
        self.visited = False
        self.response_code = None
        self.bytes = None
        self.found_in = set()
        self.excerpt = None
        self.excerpt_length = excerpt_length

    def add_found_in(self, found_in_url: str):
        self.found_in.add(found_in_url)

    def add_excerpt(self, text: str):
        self.excerpt = defuse(str(text)[0:self.excerpt_length])

    def __str__(self):
        return f"WebPage: url={self.url_str} - own={self.own} - visited={self.visited} - response_code={self.response_code} - bytes={self.bytes} - found_in={len(self.found_in)} - excerpt={defuse(self.excerpt)}"


class WebsiteCrawler:

    def __init__(self, initial_backlog: list, own_site_url_stems: list = None, ignore_urls = None, logger: logging.Logger = None, log_sampling=1):
        self.created = dt.now().isoformat()
        self.initial_backlog = list(initial_backlog)
        self.own_site_url_stems = list(own_site_url_stems) if own_site_url_stems else self.initial_backlog
        self.ignore_urls = list(ignore_urls) if ignore_urls else []
        if logger is None:
            logging.basicConfig(stream=sys.stdout, level=logging.INFO)
            self.logger = logging
        else:
            self.logger = logger
        self.log_sampling = log_sampling
        self.backlog = {}
        for url in initial_backlog:
            url_canonized = canonize_url(url)
            kind = self.classify_url(url_canonized)
            web_page = WebPage(url_canonized, own=(kind==UrlType.OWN))
            web_page.add_found_in("initial_backlog")
            self.backlog[url_canonized] = web_page
        if self.logger:
            self.logger.info(f"Website Crawler created with initial_backlog={initial_backlog}, own_site_url_stems={own_site_url_stems}")

    def crawl(self):
        count = 0
        while True:
            next_web_page = self.next_web_page()
            if next_web_page is None:
                break
            self.visit_web_page(next_web_page)
            count += 1
            if self.logger and ((not self.log_sampling) or count % self.log_sampling == 0):
                self.logger.info(f"Visited #{count} web page: {next_web_page}")

        if self.logger:
            self.logger.info(f"Visited #{count} web pages, done crawling.")
            self.logger.info(f"{self}")


    def next_web_page(self) -> WebPage:
        """return the next WebPage in the backlog not yet visited, or None if all are visited"""
        for key in sorted(self.backlog.keys()):
            web_page = self.backlog[key]
            if not web_page.visited:
                return web_page
        return None

    def visit_web_page(self, web_page: WebPage):
        try:
            response = requests.get(web_page.url_str, allow_redirects=True, timeout=5.0)
            web_page.visited = True
            web_page.response_code = response.status_code
            web_page.bytes = len(response.content)
            text = response.content.decode("utf-8")
            web_page.add_excerpt(text)
            if web_page.own:
                urls_in_page = self.parse_for_relevant_urls(text)
                self.add_to_backlog(urls_in_page, web_page.url_str)
        except Exception as e:
            web_page.visited = True
            web_page.response_code = 9999  # for Exception
            web_page.bytes = 0
            web_page.add_excerpt(str(e))

    def parse_for_relevant_urls(self, text: str) -> set:
        indices_of_urls = [i for i in range(len(text)) if text.startswith('http://', i) or text.startswith('https://', i)]
        urls = set()
        for i in indices_of_urls:
            i_end = min([text.find(token, i) for token in ('"', "'", ' ', ')', '<', '#', '&quot;', '\n', '\r') if text.find(token, i) > 0])
            if i_end > i:
                url = canonize_url(text[i:i_end])
                kind = self.classify_url(url)
                if kind == UrlType.OWN or kind == UrlType.OTHER:
                    urls.add(url)
        return urls

    def add_to_backlog(self, urls: Iterable, found_in: str):
        for url in urls:
            if url not in self.ignore_urls:
                web_page = self.backlog.get(url)
                if web_page is None:
                    kind = self.classify_url(url)
                    web_page = WebPage(url, own=(kind==UrlType.OWN))
                    self.backlog[url] = web_page
                web_page.add_found_in(found_in)

    def classify_url(self, url: str) -> UrlType:
        u = canonize_url(url)
        if (any(u.endswith(e) for e in NOT_RELEVANT_URL_ENDINGS) or
            any(f in u for f in NOT_RELEVANT_URL_CONTAINS) or
            re.search(r'./\d+$', u)):  # ending on a 1+ digits
            return UrlType.DO_NOT_FOLLOW
        return UrlType.OWN if self.url_starts_with_base_url(u) else UrlType.OTHER

    def url_starts_with_base_url(self, url: str) -> bool:
        return any([url.startswith(b) for b in self.own_site_url_stems])

    def get_status_code_count(self) -> dict:
        sc_counts = defaultdict(int)
        for web_page in self.backlog.values():
            sc_counts[web_page.response_code] += 1
        return dict(sc_counts)

    def get_web_pages_for_status_code(self, status_code: int) -> list:
        pages = []
        for url in sorted(self.backlog.keys()):
            web_page = self.backlog[url]
            if web_page.response_code == status_code:
                pages.append(web_page)
        return pages

    def get_bytes_total(self) -> int:
        return sum([self.backlog[url].bytes for url in self.backlog.keys()])

    def __str__(self):
        return f"WebsiteCrawler status: backlog size: {len(self.backlog)} - {self.get_bytes_total()/1000000:.6f} MB - status codes: {self.get_status_code_count()}"


if __name__ == '__main__':
    print("a simple test run with a narrow backlog example.")
    backlog = ['https://opentransportdata.swiss/en/cookbook/accessibility-cookbook']
    ignore_urls = ['https://www.linkedin.com/company/systemaufgaben-kundeninformation-ski']
    wc = WebsiteCrawler(backlog, ignore_urls=ignore_urls)
    wc.crawl()