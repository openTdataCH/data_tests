"""Module to handle URLs: collect, sort, manage them, clean them, analyze them.
 """
import re
from enum import Enum
from typing import Iterable
from datetime import datetime as dt
from collections import defaultdict

NOT_RELEVANT_URL_ENDINGS = [".css", ".js", ".ico", ".svg", ".png", ".jpg", ".gif", ".php", ".jsonld", ".n3", ".ttl",
                         ".xml", ".json", ".zip", ".pdf", ".jpeg", "wp-json", ".xlsx", ".csv", ".txt", "embed",
                         ".woff2", ".ttf"]

NOT_RELEVANT_URL_CONTAINS = ["/resource/"]


class UrlType(Enum):
    FOLLOW = 0
    DO_NOT_FOLLOW = 1
    EXTERNAL = 2


class UrlHandler:

    def __init__(self, initial_backlog: list):
        self.created = dt.now().isoformat()
        self.initial_backlog = initial_backlog
        self._base_urls = [self.canonize_url(u) for u in initial_backlog]
        self._backlog = defaultdict(set)
        for url in self._base_urls:
            self._backlog[url].add('initial_backlog')
        self.visited = set()
        self.non200 = defaultdict(set)
        self.n_bytes = 0

    def backlog_pop0(self) -> tuple:
        if len(self._backlog.keys()) == 0:
            return None
        popee_key = sorted(self._backlog.keys())[0]
        popee_value = sorted(self._backlog.pop(popee_key))
        popee_value = popee_value[0] if len(popee_value) == 1 else str(popee_value)
        return popee_key, popee_value

    def backlog_size(self):
        return len(self._backlog.keys())

    def backlog_add_not_yet_visited(self, urls: Iterable, referrer: str):
        count = 0
        for u in urls:
            if self.canonize_url(u) not in self.visited:
                self._backlog[u].add(referrer)
                count += 1
        return count

    def visited_add(self, url) -> (str, UrlType):
        u = self.canonize_url(url)
        t = self.classify(u)
        self.visited.add(u)
        return u, t

    def visited_list(self):
        return sorted(self.visited)

    def visited_size(self):
        return len(self.visited)

    def visited_already(self, url: str):
        return self.canonize_url(url) in self.visited

    def url_starts_with_base_url(self, url: str) -> bool:
        u = self.canonize_url(url)
        return any([u.startswith(b) for b in self._base_urls])

    def non200_add(self, url: str, code):
        self.non200[code].add(url)

    def non200_size(self):
        return sum(len(s) for s in self.non200.values())

    def non200_count(self) -> dict:
        return {k: len(self.non200[k]) for k in sorted(self.non200.keys())}

    def bytes_add(self, n_bytes: int):
        self.n_bytes += n_bytes

    def bytes_count(self):
        return self.n_bytes

    def classify(self, url: str) -> UrlType:
        u = self.canonize_url(url)
        if (any(u.endswith(e) for e in NOT_RELEVANT_URL_ENDINGS) or
            any(f in u for f in NOT_RELEVANT_URL_CONTAINS) or
            re.search(r'./\d+$', u)):  # ending on a 1+ digits
            return UrlType.DO_NOT_FOLLOW
        return UrlType.FOLLOW if self.url_starts_with_base_url(u) else UrlType.EXTERNAL

    def canonize_url(self, url: str) -> str:
        while url[-1] in "/&":
            url = url[:-1]
        return url.lower()

    def parse_relevant_urls(self, text: str) -> set:
        indices_of_urls = [i for i in range(len(text)) if text.startswith('https://', i)]
        urls = set()
        for i in indices_of_urls:
            i_end = min([text.find(token, i) for token in ('"', "'", '"', '?', ' ', ')', '<', '#', '&quot;', '\n', '\r') if text.find(token, i) > 0])
            if i_end > i:
                url = self.canonize_url(text[i:i_end])
                if self.classify(url) in (UrlType.FOLLOW, UrlType.EXTERNAL):
                    urls.add(url)
        return urls

    def __str__(self):
        return f"UrlHandler status - backlog: {self.backlog_size()} - visited: {self.visited_size()} - non200: {self.non200_count()} - {self.n_bytes/1000000:.6f} MB"


if __name__ == '__main__':
    print(f"Simple tests of {__file__}")
    U1, U2, U3, UX = 'https://a.ch', 'https://b.ch', 'https://c.ch', 'https://x.ch'
    uh = UrlHandler(initial_backlog=[U1, U2, U2])
    assert uh.backlog_size() == 2
    assert uh.backlog_pop0() == (U1, "initial_backlog")
    assert uh.backlog_pop0() == (U2, "initial_backlog")
    assert uh.backlog_pop0() is None

    uh.visited_add(U2)
    uh.visited_add(U1)
    uh.visited_add(U1)
    assert uh.visited_size() == 2
    assert uh.visited_list() == [U1, U2]

    assert uh.canonize_url(U1 + '/') == U1
    assert uh.canonize_url(U1 + '/&') == U1

    assert uh.classify(U1 + '/p1') == UrlType.FOLLOW
    assert uh.classify(UX + '/p1') == UrlType.EXTERNAL
    assert uh.classify(U1 + '/p1.png') == UrlType.DO_NOT_FOLLOW
    assert uh.classify(U1 + '/resource/p1') == UrlType.DO_NOT_FOLLOW

    assert uh.parse_relevant_urls(f"a text with {U1} and {U2} but not U3.") == {U1, U2}

    cnt = uh.backlog_add_not_yet_visited([U1, U2, U3, UX], 'ref')
    assert cnt == 2
    assert uh.backlog_size() == 2
    assert uh.backlog_pop0() == (U3, 'ref')
    assert uh.backlog_pop0() == (UX, 'ref')


    print("Done.")
