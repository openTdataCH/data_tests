"""A test to do a simple crawl of a given website, looking for invalid links.

The test laads a "backlog" of URLs from a data/config.json file.
Going through all the backlog:
- it loads the next HTML page; check status, warn if >= 400
- look for relevant links and add them to the backlog (if not yet visited)

The file ./data/config.json must look like this:
{
  "initial_backlog": [
     "https://url.to_server.example1.com/page1",
     "https://url.to_server.example2.com"
  ],
  "warning_threshold": 10
}


"""
import time

import logging
import requests
from datetime import datetime as dt

from tests.website_crawler_tests.url_handler import UrlHandler, UrlType
from utilities.file_and_path_utilities import get_path
from utilities.json_utilities import load_json_file
from utilities.test_utilities import DataTest

TEST_NAME = "website_crawler_tests"

CONFIG_FILE = f"tests/{TEST_NAME}/data/config.json"
CONFIG = load_json_file(CONFIG_FILE)

LOG_FILE = get_path(f"tests/{TEST_NAME}/data/logs/log{dt.now().isoformat()[:19].replace(':', '-')}.log")
logger = logging.getLogger(__name__)   # module logger
logger.setLevel(logging.INFO)
fh = logging.FileHandler(filename=LOG_FILE, mode='w', encoding='utf-8')
fh.setLevel(logging.INFO)
fh.setFormatter(logging.Formatter('%(asctime)s: %(levelname)s: %(message)s'))
logger.addHandler(fh)
logger.propagate = False

DELAY_IN_SECONDS = 0.1

OK, WARN, NOK, SMILE = "✅", "⚠", "⛔", "😊"


def load_and_analyze_page(uh: UrlHandler, url: str, referrers: dict, data_test: DataTest):
    try:
        url, url_type = uh.visited_add(url)
        response = requests.get(url, allow_redirects=True, timeout=5.0)
        n_bytes = len(response.content)
        uh.bytes_add(n_bytes)
        visit_msg = f"{url} {response.status_code} {response.reason}, {n_bytes} bytes:"
        logger.debug(f"load_and_analyze: {visit_msg}")
        if response.status_code == 200:
            add_to_backlog = []
            if url_type == UrlType.FOLLOW:
                text = response.content.decode(encoding="utf-8")
                urls_in_page = uh.parse_relevant_urls(text)
                n_added = uh.backlog_add_not_yet_visited(urls_in_page, url)
                logger.debug(f"{visit_msg} add_to_backlog: {n_added}, backlog count: {uh.backlog_size()}.")
            else:  # for external links, do not parse for new URLs:
                logger.debug(f"{visit_msg} External page, therefore ignoring links.")
            if response.is_redirect:
                logger.warning(f"{WARN} {visit_msg} redirect={response.url}")
        else:
            sc = response.status_code
            uh.non200_add(url, sc)
            message = f"{visit_msg} {WARN if (sc < 400) or sc in (401, 402, 403) else NOK} - referrer: {str(referrers)}"
            logger.warning(message)
            logger.info(uh)
            if response.status_code == 404:
                data_test.log_info(message)
    except Exception as e:
        logger.error(f"{NOK} Exception at url: {url} - referrer: {str(referrers)} - {str(e)[:100]}...")


def crawl(uh: UrlHandler, data_test: DataTest):
    """Crawl through all web pages given in the pages_backlog dict (key = URL, value = referrer).
    Look for urls which do not respond with 200.
    """
    while uh.backlog_size() > 0:
        next_url, next_referrers = uh.backlog_pop0()
        load_and_analyze_page(uh, next_url, next_referrers, data_test)
        time.sleep(DELAY_IN_SECONDS)

    message = f"Completed crawling, visited: {uh.visited_size()}, non200: {uh.non200_size()} / {uh.non200_count()}, {uh.bytes_count()/1000000:.6f} MB."
    logger.info(message)
    warning_threshold =  CONFIG.get('warning_threshold')
    count_404 = uh.non200_count().get(404)
    if warning_threshold and count_404 >= warning_threshold:
        warning_message = f"Total count of 404 responses is {count_404}, exceeds the given warning_threshold {warning_threshold}!"
        data_test.log_warning(warning_message)
        logger.warning(warning_message)
    data_test.log_info(message)


def run():
    data_test = DataTest(name=TEST_NAME)
    if CONFIG is None:
        raise ValueError(f"Error in {TEST_NAME}: config.json not found, test terminated.")
    message = f"- Initial backlog (base URLs): {CONFIG['initial_backlog']}."
    data_test.log_info(message)
    logger.info(message)
    uh = UrlHandler(CONFIG['initial_backlog'])
    crawl(uh, data_test)
    return data_test


if __name__ == '__main__':
    tr = run()
    print(tr)
