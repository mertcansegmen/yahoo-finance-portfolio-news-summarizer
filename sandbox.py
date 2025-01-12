import os
import time
import json
from bs4 import BeautifulSoup
from colorama import Fore, Style, init

import requests
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

SCROLL_DOWN_ATTEMPTS = 1

API_KEY = os.getenv('DEEPSEEK_API_KEY')
API_URL = "https://api.deepseek.com/chat/completions"

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
    scroll_down_infinite(driver, attempts=SCROLL_DOWN_ATTEMPTS, pause_time=2)

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


def user_pick_news(final_news_list):
    """
    Asks the user, for each article, if they want to summarize it.
    User inputs:
      - 'y' -> Summarize the current article
      - 'n' -> Skip the current article
      - 'q' -> Skip all remaining articles
    Returns a list of articles selected for summarization.
    """
    selected_articles = []
    skip_all = False

    for article in final_news_list:
        # If the user already chose to skip all, break out of the loop immediately
        if skip_all:
            break

        i_print("\n\n--- Article Info ---")
        i_print(f"Title: {article['title']}")
        i_print(f"Author: {article['author']}")
        i_print(f"Publisher: {article['publisher']}")
        i_print(f"When: {article['when']}")
        i_print(f"Stocks: {', '.join(article['stocks']) if article['stocks'] else 'None'}")
        i_print(f"Content (first 300 chars): {article['content'][:300]}...")

        # Continuously prompt for valid input ('y', 'n', or 'q')
        while True:
            user_input = input(
                Fore.BLUE + "Press 'y' to summarize, 'n' to skip, or 'q' to skip all remaining articles: "
                + Style.RESET_ALL
            ).strip().lower()

            if user_input == 'y':
                selected_articles.append(article)
                s_print(f"Added article: {article['title']}")
                break
            elif user_input == 'n':
                i_print(f"Skipped article: {article['title']}")
                break
            elif user_input == 'q':
                w_print("Skipping all remaining articles.")
                skip_all = True
                break
            else:
                i_print("Invalid input. Please press 'y', 'n', or 'q'.")

    return selected_articles


def call_deepseek(user_prompt: str, system_prompt: str):
    """
    Internal helper to send prompt + system instructions to DeepSeek Chat.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
    }

    response = requests.post(API_URL, headers=headers, json=data)
    response.raise_for_status()
    return response.json()


def summarize_article(article):
    """
    Summarizes the given article using DeepSeek v3 Chat.
    Returns the summary string.
    """

    user_prompt = f"""
        Aşağıdaki haberi bana türkçe olarak özetler misin?

        Başlık:
        {article['title']}

        İçerik:
        {article['content']}
    """

    system_prompt = "Sen, sana gönderilen finans haberlerini özetleyen bir asistansın."
    
    response_data = call_deepseek(user_prompt, system_prompt)
    
    assistant_content = response_data["choices"][0]["message"]["content"]

    return assistant_content


def summarize_articles(selected_articles):
    """
    Summarizes each article in selected_articles using the summarize_article function.
    Returns a list of dictionaries containing article info + summary.
    """
    summarized_list = []
    for idx, article in enumerate(selected_articles, start=1):
        i_print(f"Summarizing article #{idx}: {article['title']}")
        summary_text = summarize_article(article)

        # Store summarized article info
        summarized_list.append({
            'count': article['count'],
            'title': article['title'],
            'when': article['when'],
            'publisher': article['publisher'],
            'author': article['author'],
            'stocks': article['stocks'],
            'url': article['url'],
            'summary': summary_text
        })

    return summarized_list


def save_summaries_to_markdown(summarized_articles, markdown_filename="summaries.md"):
    """
    Creates a Markdown file containing each article's metadata and summary.
    """
    with open(markdown_filename, "w", encoding="utf-8") as md_file:
        md_file.write("# Summarized Articles\n\n")
        for article in summarized_articles:
            title = article.get("title") or "Untitled"
            when = article.get("when") or "Unknown Date"
            publisher = article.get("publisher") or "Unknown Publisher"
            author = article.get("author") or "Unknown Author"
            stocks = article.get("stocks") or []
            url = article.get("url") or ""
            summary = article.get("summary") or ""

            md_file.write(f"## {title}\n\n")
            md_file.write(f"- **Date**: {when}\n")
            md_file.write(f"- **Publisher**: {publisher}\n")
            md_file.write(f"- **Author**: {author}\n")
            md_file.write(f"- **Related Stocks**: {', '.join(stocks) if stocks else 'None'}\n")
            if url:
                md_file.write(f"- **Original Article**: [{url}]({url})\n\n")
            else:
                md_file.write(f"- **Original Article**: None\n\n")

            md_file.write("**Summary**:\n\n")
            md_file.write(f"{summary}\n\n")
            md_file.write("---\n\n")

    s_print(f"Markdown file '{markdown_filename}' created successfully.")


if __name__ == "__main__":
    url = "https://finance.yahoo.com/portfolios"
    user_data_dir = os.path.join(os.getcwd(), "selenium_profile")

    # 1) Create a unique timestamped folder
    timestamp_str = time.strftime("%Y-%m-%d %H.%M.%S")  
    output_folder = os.path.join(os.getcwd(), "output", timestamp_str)
    os.makedirs(output_folder, exist_ok=True)

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

        # 2) Attempt to fetch the news without prompting for login
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
        
        i_print(f"Found {len(news_list)} portfolio news.")

        # 3) Save the raw news_list to JSON
        news_list_path = os.path.join(output_folder, "news_list.json")
        with open(news_list_path, "w", encoding='utf-8') as f:
            json.dump(news_list, f, indent=2, ensure_ascii=False)

        # 4) Build the final list of news articles with content by scraping each article
        final_news_list = []
        current_final_count = 1

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

        # 5) Save final_news_list to JSON
        final_news_list_path = os.path.join(output_folder, "final_news_list.json")
        with open(final_news_list_path, "w", encoding='utf-8') as f:
            json.dump(final_news_list, f, indent=2, ensure_ascii=False)

        # 6) Print logs
        s_print(f"Collected {len(news_list)} items in news_list.")
        s_print(f"Collected {len(final_news_list)} items in final_news_list (with content).")

        # 7) Ask the user which articles to summarize
        selected_articles = user_pick_news(final_news_list)
        s_print(f"Selected {len(selected_articles)} articles for summarization.")

        # Save selected articles to JSON
        selected_articles_path = os.path.join(output_folder, "selected_articles.json")
        with open(selected_articles_path, "w", encoding='utf-8') as f:
            json.dump(selected_articles, f, indent=2, ensure_ascii=False)

        # 8) Summarize the selected articles
        if selected_articles:
            summarized_articles = summarize_articles(selected_articles)
            s_print(f"Summarized {len(summarized_articles)} articles.")

            # Save summarized articles to JSON
            summarized_articles_path = os.path.join(output_folder, "summarized_articles.json")
            with open(summarized_articles_path, "w", encoding='utf-8') as f:
                json.dump(summarized_articles, f, indent=2, ensure_ascii=False)
            s_print("Summaries saved to summarized_articles.json")

            # Create a Markdown file of the summarized articles
            markdown_path = os.path.join(output_folder, "summaries.md")
            save_summaries_to_markdown(summarized_articles, markdown_filename=markdown_path)

        else:
            w_print("No articles were selected for summarization.")

    finally:
        driver.quit()
