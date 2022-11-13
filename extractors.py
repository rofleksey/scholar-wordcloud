import re
from urllib.parse import urlparse

from bs4 import Comment, BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

from util import with_timeout

abstract_pattern = re.compile("abstract:?|summary:?", re.IGNORECASE)


def _element_visible(el):
    if el.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(el, Comment):
        return False
    return True


def _text_from_element(el):
    texts = el.findAll(text=True)
    visible_texts = filter(_element_visible, texts)
    return u" ".join(t.strip() for t in visible_texts)


def _has_parent_tag_by_name(el, name):
    if el.parent is None:
        return False
    cur = el.parent
    while True:
        if cur.name == name:
            return True
        if cur.parent is None:
            return False
        cur = cur.parent


@with_timeout(15)
# playwright usage allows the script to parse dynamically generated content
def _get_page_content(url, selector=None, time=600000):
    with sync_playwright() as p:
        # some sites refuse to acknowledge headless browsers
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        stealth_sync(page)
        try:
            page.goto(url, timeout=10000)
        except:
            pass
        if selector:
            page.wait_for_selector(selector, timeout=time)
        content = page.content()
        browser.close()
        return content


def _filter_abstract_tags(el):
    if not abstract_pattern.search(el.text):
        return False
    if not _element_visible(el):
        return False
    return el.name in ["h1", "h2", "h3", "strong"]


def _is_meaningful_abstract(el):
    cleaned_text = abstract_pattern.sub("", _text_from_element(el))
    return len(cleaned_text.split(".")) > 2


def extract_abstract_by_selector(url, selector):
    try:
        content = _get_page_content(url, selector=selector, time=10000)
    except:
        return None
    soup = BeautifulSoup(content, "html.parser")
    element = soup.select_one(selector)
    if element is None:
        return None
    return abstract_pattern.sub("", _text_from_element(element))


def _extract_extract_by_og_description(soup):
    meta = soup.find("meta", property="og:description")
    if meta is None:
        return ""
    return abstract_pattern.sub("", meta["content"])


def _extract_generic_abstract(url):
    try:
        content = _get_page_content(url)
    except:
        return None
    soup = BeautifulSoup(content, "html.parser")
    description = _extract_extract_by_og_description(soup)
    # find visible highlighted elements that contains string "Abstract"
    elements = soup.find_all(_filter_abstract_tags)
    if len(elements) == 0:
        return description
    # select the one with minimal html length
    element = min(elements, key=lambda el: len(str(el)))
    # search at most 2 parents above for valid abstract text (should contain several sentences)
    max_remaining_depth = 2
    while element.parent and not _is_meaningful_abstract(element) and max_remaining_depth >= 0:
        if max_remaining_depth > 0:
            element = element.parent
        max_remaining_depth -= 1
    if max_remaining_depth >= 0:
        return max(description, abstract_pattern.sub("", _text_from_element(element)))
    return description


def extract_abstract(url):
    domain = urlparse(url).netloc
    domain = domain.removeprefix("www.")
    match domain:
        case "sciencedirect.com":
            if "/book" in url:
                return extract_abstract_by_selector(url, "#book-description > div > div.description-desktop")
            return extract_abstract_by_selector(url, ".abstract")
        case "tandfonline.com":
            return extract_abstract_by_selector(url,
                                                "#mainTabPanel > article > div.hlFld-Abstract > div.abstractSection.abstractInFull")
        case "books.google.com":
            return None
        case _:
            return _extract_generic_abstract(url)
