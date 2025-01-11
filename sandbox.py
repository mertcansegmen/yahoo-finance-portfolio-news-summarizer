import os
import time
import json
import pickle
from bs4 import BeautifulSoup
from colorama import Fore, Style, init

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

init(autoreset=True)

def i_print(message: str):
    """Info print."""
    print(Fore.BLUE + "[INFO] " + message + Style.RESET_ALL)

def w_print(message: str):
    """Warning print."""
    print(Fore.YELLOW + "[WARNING] " + message + Style.RESET_ALL)

def d_print(message: str):
    """Danger (error) print."""
    print(Fore.RED + "[DANGER] " + message + Style.RESET_ALL)

def s_print(message: str):
    """Success print."""
    print(Fore.GREEN + "[SUCCESS] " + message + Style.RESET_ALL)

def scroll_down_infinite(driver, attempts=5, pause_time=2):
    """
    Scrolls down the page multiple times to trigger infinite scrolling.
    Args:
        driver: The Selenium WebDriver instance.
        attempts: How many times to scroll before giving up.
        pause_time: Seconds to wait after each scroll for content to load.
    """
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(attempts):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_time)

        new_height = driver.execute_script("return document.body.scrollHeight")
        # If we haven't loaded more content, break early
        if new_height == last_height:
            break
        last_height = new_height

def get_portfolio_news(driver, url):
    """
    Navigates to the Yahoo Finance portfolios page, scrolls to load news items (infinite scroll),
    parses the news items, and returns a list of dictionaries:
      count, title, description, url, publisher, when
    If the news section is not found, returns None.
    """
    driver.get(url)
    time.sleep(5)

    # Scroll to load more news (infinite scroll)
    scroll_down_infinite(driver, attempts=5, pause_time=2)

    # Parse the loaded page
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    portfolio_news_section = soup.find('section', class_='container yf-1ce4p3e hideOnPrint', 
                                       attrs={'data-testid': 'port-news'})

    if not portfolio_news_section:
        return None  # Indicate that the news section was not found

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
        w_print("External Article, skipping...")
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
        d_print("Article div not found or different structure.")
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

    s_print(f"Article parsed: {article_title}")

    return {
        'title': article_title,
        'author': article_author,
        'when': article_when,
        'content': article_content,
        'stocks': stocks
    }

def pick_news(final_news_list):
    """
    Decide which news items from final_news_list we want to summarize.
    Placeholder: returns the entire list right now.
    You can later add custom logic or filters here.
    """
    return final_news_list


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
        i_print("Opening the browser with user data directory...")

        # 1. Attempt to fetch the news without prompting for login
        news_list = get_portfolio_news(driver, url)

        if not news_list:
            w_print("Could not find the portfolio news. Possibly not logged in.")
            input(i_print("Please log in (if not already). Then press Enter to continue...") or "")

            # Try again after manual login
            news_list = get_portfolio_news(driver, url)
            if not news_list:
                d_print("Still cannot find the portfolio news. Exiting.")
                driver.quit()
                exit(1)

        # 2. Save the raw news_list to JSON
        with open("news_list.json", "w", encoding='utf-8') as f:
            json.dump(news_list, f, indent=2, ensure_ascii=False)

        # 3. Build the final list of news articles with content
        final_news_list = []
        current_final_count = 1

        # Attempt to parse all items
        for item in news_list:
            article_url = item.get('url')
            if not article_url:
                w_print(f"Skipping item {item['count']} without a valid URL.")
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

        # 4. Save final_news_list to JSON
        with open("final_news_list.json", "w", encoding='utf-8') as f:
            json.dump(final_news_list, f, indent=2, ensure_ascii=False)

        # 5. Print logs
        s_print(f"Collected {len(news_list)} items in news_list.")
        s_print(f"Collected {len(final_news_list)} items in final_news_list (with content).")

        # 6. Use the pick_news function to decide which articles to summarize
        picked_articles = pick_news(final_news_list)
        s_print(f"Picked {len(picked_articles)} articles to summarize.")

    finally:
        driver.quit()
