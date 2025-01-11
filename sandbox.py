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

def get_portfolio_news(driver, url):
    """
    Navigates to the Yahoo Finance portfolios page, parses the news items,
    and returns a list of dictionaries with keys: title, description, url, publisher, and when.
    """
    # Go to the given URL
    driver.get(url)
    time.sleep(5)

    # Parse page source
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    portfolio_news_section = soup.find('section', class_='container yf-1ce4p3e hideOnPrint', attrs={'data-testid': 'port-news'})

    # If the portfolio news section is found, parse the news stories
    news_list = []
    if portfolio_news_section:
        # Convert the found section to a new soup to isolate its content
        soup_news_only = BeautifulSoup(portfolio_news_section.prettify(), 'html.parser')
        news_items = soup_news_only.find_all('section', class_='container', attrs={'data-testid': 'storyitem'})

        # Extract relevant fields from each news item
        for item in news_items:
            # Extract title
            title_tag = item.find('a', {'aria-label': True})
            title = title_tag['aria-label'] if title_tag else None

            # Extract URL
            news_url = title_tag['href'] if title_tag else None
            
            # Extract description
            description_tag = item.find('p', class_='clamp')
            description = description_tag.text.strip() if description_tag else None

            # Extract publisher and timestamp
            footer_tag = item.find('div', class_='footer')
            if footer_tag:
                publisher_tag = footer_tag.find('div', class_='publishing')
                publisher = publisher_tag.contents[0].strip() if publisher_tag else None
                timestamp = publisher_tag.contents[-1].strip() if (publisher_tag and len(publisher_tag.contents) > 1) else None
            else:
                publisher = None
                timestamp = None

            # Add to the list
            news_list.append({
                'title': title,
                'description': description,
                'url': news_url,
                'publisher': publisher,
                'when': timestamp
            })
    else:
        print("Portfolio news section not found.")

    return news_list

def get_full_article(driver, article_url):
    """
    Navigates to the individual news article page, attempts to find the "Story Continues" button.
    If not found, prints 'External Article, skipping...' and returns None.
    If found, clicks the button and returns the text content of the article.
    """
    # Go to the specific article URL
    driver.get(article_url)
    time.sleep(3)

    # Attempt to click the "Story Continues" button
    # If not found, we assume it’s an external page or no expand needed
    try:
        story_continues_button = driver.find_element(
            By.CSS_SELECTOR,
            "div.readmore.yf-103i3cu button.secondary-btn.fin-size-large.readmore-button.rounded.yf-15mk0m"
        )
        story_continues_button.click()
        time.sleep(2)
    except NoSuchElementException:
        print("External Article, skipping...")
        return None

    # After expanding, parse the page again
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Locate the main article content container
    article_div = soup.find('div', class_='article yf-l7apfj')

    if not article_div:
        print("Article div not found or different structure.")
        return None

    # Extract the text; you can fine-tune based on how you want to handle newlines
    article_text = article_div.get_text(separator='\n', strip=True)

    return article_text

if __name__ == "__main__":
    # Your Yahoo Finance portfolios page (or the relevant URL)
    url = "https://finance.yahoo.com/portfolios"
    
    # Path to store Chrome user data (to stay logged in between runs)
    user_data_dir = os.path.join(os.getcwd(), "selenium_profile")

    # Configure Selenium options
    chrome_options = Options()
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    # chrome_options.add_argument('--headless')  # Uncomment if you want headless mode

    # Set up the WebDriver
    service = Service(ChromeDriverManager().install())
    service.log_level = "OFF"
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # NOTE: If not logged in, you may need to log in manually. 
        # The cookie/session state will remain in "selenium_profile" if you do.
        print("Opening the browser with user data directory...")
        driver.get(url)
        time.sleep(5)
        input("If not logged in, please log in, then press Enter to continue...")

        # ---------------------------
        # Fetch the portfolio news
        # ---------------------------
        news_list = get_portfolio_news(driver, url)

        # For debugging: print the raw news list
        print(json.dumps(news_list, indent=2))

        # --------------------------------------
        # Pick the first 5 news items as example
        # --------------------------------------
        for i, news_item in enumerate(news_list[:5]):
            print(f"\n=== News Item #{i+1} ===")
            print(f"Title: {news_item['title']}")
            print(f"URL: {news_item['url']}")
            print(f"Publisher: {news_item['publisher']}")
            print(f"Timestamp: {news_item['when']}")
            print(f"Description: {news_item['description']}")
            
            # If there's a valid URL, attempt to get full article
            if news_item['url']:
                full_article_text = get_full_article(driver, news_item['url'])
                if full_article_text:
                    print("\n--- Article Content (truncated for demo) ---")
                    print(full_article_text)  # Just print the first 500 chars for demo
                else:
                    print("Could not retrieve article content.")
            else:
                print("No URL found for this news item.")

    finally:
        driver.quit()

# user_data_dir = os.path.join(os.getcwd(), "selenium_profile")

# # Configure Selenium options
# chrome_options = Options()
# chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

# # chrome_options.add_argument('--headless')
# chrome_options.add_argument('--disable-gpu')
# chrome_options.add_argument('--no-sandbox')
# chrome_options.add_argument('--disable-dev-shm-usage')

# # Use WebDriverManager to get the ChromeDriver
# service = Service(ChromeDriverManager().install())
# driver = webdriver.Chrome(service=service, options=chrome_options)

# # URL to fetch
# url = "https://finance.yahoo.com/portfolios"

# try:
#     # Open the URL
#     print("Opening the browser with user data directory...")
#     driver.get(url)
#     time.sleep(5)  # Allow the page to load

#     # Log in manually if not already logged in
#     print("If not logged in, please log in manually. The session will be saved for future runs.")
#     input("Press Enter after ensuring you are logged in...")

#     # Reload the target page
#     driver.get(url)
#     time.sleep(5)

#     # Get the page source and parse it with BeautifulSoup
#     html_string = driver.page_source
#     soup = BeautifulSoup(html_string, 'html.parser')

#     portfolio_news_section = soup.find('section', class_='container yf-1ce4p3e hideOnPrint', attrs={'data-testid': 'port-news'})

#     # Extract the HTML of the section
#     if portfolio_news_section:
#         portfolio_news_html = portfolio_news_section.prettify()
#         # print(portfolio_news_html)

#         soup = BeautifulSoup(portfolio_news_html, 'html.parser')

#         # Extract news items
#         news_items = soup.find_all('section', class_='container', attrs={'data-testid': 'storyitem'})

#         # List to store parsed news
#         news_list = []

#         for item in news_items:
#             # Extract title
#             title_tag = item.find('a', {'aria-label': True})
#             title = title_tag['aria-label'] if title_tag else None

#             # Extract URL
#             url = title_tag['href'] if title_tag else None
            
#             # Extract description
#             description_tag = item.find('p', class_='clamp')
#             description = description_tag.text.strip() if description_tag else None

#             # Extract publisher and timestamp
#             footer_tag = item.find('div', class_='footer')
#             if footer_tag:
#                 publisher_tag = footer_tag.find('div', class_='publishing')
#                 publisher = publisher_tag.contents[0].strip() if publisher_tag else None
#                 timestamp = publisher_tag.contents[-1].strip() if publisher_tag and len(publisher_tag.contents) > 1 else None
#             else:
#                 publisher = None
#                 timestamp = None

#             # Append to the list
#             news_list.append({
#                 'title': title,
#                 'description': description,
#                 'url': url,
#                 'publisher': publisher,
#                 'when': timestamp
#             })

#         # Print the parsed news items
#         for news in news_list:
#             print(news)

#         print(json.dumps(news_list, indent=4))
#     else:
#         print("Portfolio news section not found.")

# finally:
#     # Quit the WebDriver
#     driver.quit()
