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
    init(autoreset=True)  # Automatically reset colors after each print
except ImportError:
    # If colorama is not available, we'll define fallback constants
    class Fore:
        GREEN = ''
        RED = ''
    class Style:
        RESET_ALL = ''


def get_portfolio_news(driver, url):
    """
    Navigates to the Yahoo Finance portfolios page, parses the news items,
    and returns a list of dictionaries with:
      count, title, description, url, publisher, and when.
    """
    driver.get(url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    portfolio_news_section = soup.find('section', class_='container yf-1ce4p3e hideOnPrint', 
                                       attrs={'data-testid': 'port-news'})

    news_list = []
    if portfolio_news_section:
        soup_news_only = BeautifulSoup(portfolio_news_section.prettify(), 'html.parser')
        news_items = soup_news_only.find_all(
            'section', class_='container', attrs={'data-testid': 'storyitem'}
        )

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
                timestamp = (publisher_tag.contents[-1].strip()
                             if (publisher_tag and len(publisher_tag.contents) > 1) else None)
            else:
                publisher = None
                timestamp = None

            news_list.append({
                'count': i,  # This is for reference; final_news_list won't use this as final count
                'title': title,
                'description': description,
                'url': news_url,
                'publisher': publisher,
                'when': timestamp
            })
    else:
        print(Fore.RED + "Portfolio news section not found." + Style.RESET_ALL)

    return news_list


def get_full_article(driver, article_url):
    """
    Navigates to the individual news article page, attempts to find the "Story Continues" button.
    If not found, prints 'External Article, skipping...' and returns None.
    If found, clicks the button, then parses the article fields:
      - title (from .cover-title)
      - author (from .byline-attr-author)
      - when (from <time class="byline-attr-meta-time">)
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
    stocks_div = soup.find('div', class_='scroll-carousel yf-r5lvmz', attrs={'data-testid': 'carousel-container'})
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
        driver.get(url)
        time.sleep(5)

        input(Fore.GREEN + "If not logged in, please log in, then press Enter to continue..." + Style.RESET_ALL)

        # 1. Get the 'news_list' from the portfolio page
        news_list = get_portfolio_news(driver, url)
        
        # Save news_list to JSON
        with open("news_list.json", "w", encoding='utf-8') as f:
            json.dump(news_list, f, indent=2, ensure_ascii=False)

        # 2. Build the final news list (first 5 with actual content)
        final_news_list = []
        current_final_count = 1

        for item in news_list:
            article_url = item.get('url')
            if not article_url:
                continue  # skip items without URL

            # Attempt to extract the full article
            article_info = get_full_article(driver, article_url)
            if article_info:
                # We do not reuse the 'count' from news_list; we have our own final count
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