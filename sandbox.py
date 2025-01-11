import os
import time
import json
import pickle
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# For colored console logs
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    # Fallback if colorama isn't installed
    class Fore:
        GREEN = ''
        RED = ''
    class Style:
        RESET_ALL = ''

def scroll_down_infinite(driver, attempts=5, pause_time=2):
    """
    Scrolls down the page multiple times to trigger infinite scrolling.
    Args:
        driver: The Selenium WebDriver instance.
        attempts: How many times to scroll before giving up.
        pause_time: Seconds to wait after each scroll for content to load.
    """
    last_height = driver.execute_script("return document.body.scrollHeight")

    for i in range(attempts):
        # Scroll to the bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_time)

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            # We've reached the bottom or no more new content is loading
            break
        last_height = new_height


def get_portfolio_news(driver, url):
    """
    Navigates to the Yahoo Finance portfolios page, scrolls to load news items (infinite scroll),
    parses the news items, and returns a list of dictionaries with:
      count, title, description, url, publisher, and when.

    If the news section is not found, returns None.
    """
    driver.get(url)
    time.sleep(5)

    # Scroll to load more news (infinite scroll)
    scroll_down_infinite(driver, attempts=5, pause_time=2)

    # Now parse the loaded page source
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    portfolio_news_section = soup.find('section', class_='container yf-1ce4p3e hideOnPrint', 
                                       attrs={'data-testid': 'port-news'})

    if not portfolio_news_section:
        return None  # Indicate we didn't find the news section at all

    # Parse the news stories
    soup_news_only = BeautifulSoup(portfolio_news_section.prettify(), 'html.parser')
    news_items = soup_news_only.find_all('section', class_='container', attrs={'data-testid': 'storyitem'})

    news_list = []
    for i, item in enumerate(news_items, start=1):
        title_tag = item.find('a', {'aria-label': True})
        title = title_tag['aria-label'] if title_tag else None

        news_url = title_tag['href'] if title_tag else None

        description_tag = item.find('p', class_='clamp')
        description = description_tag.text.strip() if description_tag else None

        footer_tag = item.find('div', class_='footer')
        if footer_tag:
            publisher_tag = footer_tag.find('div', class_='publishing')
            publisher = publisher_tag.contents[0].strip() if publisher_tag else None
            timestamp = (
                publisher_tag.contents[-1].strip()
                if (publisher_tag and len(publisher_tag.contents) > 1)
                else None
            )
        else:
            publisher = None
            timestamp = None

        news_list.append({
            'count': i,  # This is just for reference
            'title': title,
            'description': description,
            'url': news_url,
            'publisher': publisher,
            'when': timestamp
        })

    return news_list


def get_full_article(driver, article_url):
    """
    Navigates to the individual news article page, attempts to find the "Story Continues" button.
    If not found, prints 'External Article, skipping...' and returns None.
    If found, clicks the button, then parses:
      - title (from .cover-title)
      - author (from .byline-attr-author)
      - when (from time.byline-attr-meta-time)
      - content (from .article.yf-l7apfj)
      - stocks (from .scroll-carousel with data-testid="ticker-container")
    """
    driver.get(article_url)
    time.sleep(3)

    try:
        story_continues_button = driver.find_element(
            By.CSS_SELECTOR,
            "div.readmore.yf-103i3cu button.secondary-btn.fin-size-large.readmore-button.rounded.yf-15mk0m"
        )
        story_continues_button.click()
        time.sleep(2)
    except NoSuchElementException:
        print(Fore.RED + "External Article, skipping..." + Style.RESET_ALL)
        return None

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Article title
    cover_title_div = soup.find('div', class_='cover-title yf-1at0uqp')
    article_title = cover_title_div.get_text(strip=True) if cover_title_div else None

    # Author & when
    byline_div = soup.find('div', class_='byline-attr yf-1k5w6kz')
    if byline_div:
        author_div = byline_div.find('div', class_='byline-attr-author yf-1k5w6kz')
        article_author = author_div.get_text(strip=True) if author_div else None

        time_tag = byline_div.find('time', class_='byline-attr-meta-time')
        article_when = time_tag.get_text(strip=True) if time_tag else None
    else:
        article_author = None
        article_when = None

    # Main article content
    article_div = soup.find('div', class_='article yf-l7apfj')
    if not article_div:
        print(Fore.RED + "Article div not found or different structure." + Style.RESET_ALL)
        return None

    article_content = article_div.get_text(separator='\n', strip=True)

    # Stocks
    stocks_div = soup.find(
        'div', class_='scroll-carousel yf-r5lvmz',
        attrs={'data-testid': 'carousel-container'}
    )
    stocks = []
    if stocks_div:
        ticker_links = stocks_div.find_all('a', {'data-testid': 'ticker-container'})
        for link in ticker_links:
            label = link.get('aria-label')
            if label:
                stocks.append(label)

    return {
        'title': article_title,
        'author': article_author,
        'when': article_when,
        'content': article_content,
        'stocks': stocks
    }


if __name__ == "__main__":
    url = "https://finance.yahoo.com/portfolios"
    user_data_dir = os.path.join(os.getcwd(), "selenium_profile")

    chrome_options = Options()
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    # chrome_options.add_argument('--headless')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        print(Fore.GREEN + "Opening the browser with user data directory..." + Style.RESET_ALL)

        # 1. Attempt to fetch news without prompting for login
        news_list = get_portfolio_news(driver, url)

        if not news_list:
            # Could not find the news section => likely not logged in or another problem
            print(Fore.RED + "Could not find the portfolio news. Possibly not logged in." + Style.RESET_ALL)
            input(Fore.GREEN + "Please log in (if not already). After logging in, press Enter to continue..." + Style.RESET_ALL)

            # Try again after manual login
            news_list = get_portfolio_news(driver, url)
            if not news_list:
                print(Fore.RED + "Still cannot find the portfolio news. Exiting." + Style.RESET_ALL)
                driver.quit()
                exit(1)

        # 2. Save the news_list to JSON
        with open("news_list.json", "w", encoding='utf-8') as f:
            json.dump(news_list, f, indent=2, ensure_ascii=False)

        # 3. Build the final list of news articles with content
        final_news_list = []
        current_final_count = 1

        for item in news_list:
            article_url = item.get('url')
            if not article_url:
                print(Fore.ORANGE + f"Skipping item {item['count']} without a valid URL." + Style.RESET_ALL)
                continue  # skip items without a valid URL

            article_info = get_full_article(driver, article_url)
            if article_info:
                final_news_list.append({
                    'count': current_final_count,
                    'url': article_url,
                    'publisher': item.get('publisher'),
                    'title': article_info['title'],
                    'content': article_info['content'],
                    'stocks': article_info['stocks'],
                    'when': article_info['when'],
                    'author': article_info['author']
                })
                current_final_count += 1

                # Stop after 5 items with content
                if len(final_news_list) == 5:
                    break

        # Save final_news_list to JSON
        with open("final_news_list.json", "w", encoding='utf-8') as f:
            json.dump(final_news_list, f, indent=2, ensure_ascii=False)

        # Print minimal logs
        print(Fore.GREEN + f"Collected {len(news_list)} items in news_list." + Style.RESET_ALL)
        print(Fore.GREEN + f"Collected {len(final_news_list)} items in final_news_list (with content)." + Style.RESET_ALL)

    finally:
        driver.quit()
