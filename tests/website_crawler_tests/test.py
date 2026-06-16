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

import logging
from datetime import datetime as dt

from tests.website_crawler_tests.website_crawler import WebsiteCrawler
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

OK, WARN, NOK, SMILE = "✅", "⚠", "⛔", "😊"


def run():
    data_test = DataTest(name=TEST_NAME)
    if CONFIG is None:
        raise ValueError(f"Error in {TEST_NAME}: config.json not found, test terminated.")
    wc = WebsiteCrawler(CONFIG['initial_backlog'], CONFIG['initial_backlog'], logger=logger, log_sampling=1)
    wc.crawl()
    data_test.log_info(str(wc))
    sc_count = wc.get_status_code_count()
    total = 0
    for status_code in sorted(sc_count.keys()):
        if status_code == 400 or status_code >= 404:
            count = sc_count.get(status_code)
            data_test.log_info(f"http status code {status_code} for {count} page{'s' if count != 1 else ''}:")
            web_pages = wc.get_web_pages_for_status_code(status_code)
            for web_page in web_pages:
                found_in = sorted(web_page.found_in)
                data_test.log_info(f"- status code {status_code} for {web_page.url_str} - excerpt: {web_page.excerpt}... - URL found in these pages (first 10 of a total of {len(found_in)}):\n- {'\n- '.join(found_in[:10])}")
                total += 1
    threshold = CONFIG['warning_threshold']
    if threshold and total >= threshold:
        data_test.log_warning(f"Pages 404: {total} pages found, exceeds threshold of {threshold}")
    return data_test


if __name__ == '__main__':
    tr = run()
    print(tr)
