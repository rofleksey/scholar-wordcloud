from dataclasses import dataclass

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

SCHOLAR_QUERY_INPUT_SELECTOR = '#gs_hdr_tsi'
SCHOLAR_SEARCH_BUTTON_SELECTOR = '#gs_hdr_tsb'
SCHOLAR_NEXT_BUTTON_SELECTOR = '#gs_n > center > table > tbody > tr > td:last-child'

ARTICLE_SELECTOR = '#gs_res_ccl_mid > .gs_scl'
ARTICLE_NAME_SELECTOR = '.gs_ri > .gs_rt > a'
ARTICLE_AUTHOR_SELECTOR = '.gs_ri > .gs_a'
ARTICLE_ANNOTATION_SELECTOR = '.gs_ri > .gs_rs'


@dataclass
class Article:
    """Class representing a single article"""
    name: str
    link: str
    author: str
    annotation: str


def _parse_scholar_articles(content):
    soup = BeautifulSoup(content, "html.parser")
    articles = soup.select(ARTICLE_SELECTOR)
    result = []
    for article_div in articles:
        try:
            name_div = article_div.select_one(ARTICLE_NAME_SELECTOR)
            name = name_div.get_text()
            link = name_div['href']
            author = article_div.select_one(ARTICLE_AUTHOR_SELECTOR).get_text()
            annotation = article_div.select_one(ARTICLE_ANNOTATION_SELECTOR).get_text()
            result.append(Article(name, link, author, annotation))
        except Exception as e:
            print("failed to parse article: " + str(e))
    return result


# playwright usage fixes entering captcha more than 2 times
def fetch_articles(query, max_pages):
    with sync_playwright() as p:
        # some sites refuse to acknowledge headless browsers
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        stealth_sync(page)
        page.goto("https://scholar.google.com/", timeout=600000)
        page.wait_for_timeout(500)
        page.locator(SCHOLAR_QUERY_INPUT_SELECTOR).click()
        page.locator(SCHOLAR_QUERY_INPUT_SELECTOR).type(query, delay=30)
        page.locator(SCHOLAR_SEARCH_BUTTON_SELECTOR).click()
        output_articles = []
        for _ in range(max_pages):
            page.wait_for_selector(ARTICLE_ANNOTATION_SELECTOR, timeout=600000)
            content = page.content()
            output_articles.extend(_parse_scholar_articles(content))
            page.wait_for_timeout(1000)
            page.locator(SCHOLAR_NEXT_BUTTON_SELECTOR).click()
        browser.close()
        return output_articles


def last_names_iterator(article):
    authors_part = article.author.split("-")[0].strip()
    authors = authors_part.split(",")
    for author in authors:
        yield author.strip().split(" ")[-1].strip().capitalize()
