"""Simple tests of the WebsiteCrawler class, using http.server and a few files served on localhost.
"""
import sys

import http.server
import logging
import os
import socketserver
import threading

from tests.website_crawler_tests.website_crawler import WebsiteCrawler

logger = logging.getLogger("website_crawler_test")
logger.setLevel(logging.INFO)
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(stdout_handler)


class ThreadedHTTPServer:
    def __init__(self, directory, host="127.0.0.1", port=0):
        handler = http.server.SimpleHTTPRequestHandler
        self._cwd = os.getcwd()
        self.directory = directory
        self.host = host
        self.port = port
        self.httpd = socketserver.TCPServer((host, port), lambda *args, **kwargs: handler(*args, directory=directory, **kwargs))
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join()


if __name__ == '__main__':
    TEST_DIRECTORY = "data/test_site"
    HOST = "127.0.0.1"
    srv = ThreadedHTTPServer(directory=TEST_DIRECTORY, port=8080)
    srv.start()
    print(f'{__file__} - simple tests on https://{HOST}:{srv.port}')
    url_page1 = f"http://{HOST}:{srv.port}/our/page1.html"
    own_site = f"http://{HOST}:{srv.port}/our"
    wc = WebsiteCrawler(initial_backlog=[url_page1], own_site_url_stems=[own_site], logger=logger, log_sampling=1)

    wc.crawl()
    logger.info("All Pages:")
    for url in sorted(wc.backlog.keys()):
        logger.info(f"{url:50} -> {wc.backlog[url]}")
    pages404 = wc.get_web_pages_for_status_code(404)
    logger.info("404 Pages:")
    for page in pages404:
        logger.info(page)
    logger.info("Done.")
    srv.stop()
