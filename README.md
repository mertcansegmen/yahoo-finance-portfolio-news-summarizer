# Yahoo Finance Portfolio News Summarizer

This project automates the scraping and summarizing of news from Yahoo Finance portfolios. It uses Selenium and BeautifulSoup to extract article details, with interactive prompts for users to select which articles to summarize. Outputs, including JSON and Markdown files, are organized in timestamped folders for easy reference.

This project automates the process of:

1. Fetching news from [Yahoo Finance Portfolios page](https://finance.yahoo.com/portfolios), which is the page that shows the news related to your portfolios.
2. Clicking on each news item to retrieve the full article.
3. Interacting with the user to decide which articles to summarize.
4. Using an LLM to summarize the selected articles in Turkish.
5. Saving the summaries as a markdown file for easy reading.

---

## Features and Flow

1. **Automated Web Scraping**  
   - Utilizes **Selenium** and **BeautifulSoup** to navigate and parse Yahoo Finance news items.

2. **Infinite Scroll Handling**  
   - Scrolls down the page to trigger the loading of more articles.

3. **Article Parsing**  
   - Attempts to click the “Story Continues” button to load the full article text.
   - Collects the article’s title, author, publisher, publication date/time, related stocks, and full content.

4. **User Interaction**  
   - Prompts you for each parsed article:
     - **(y)** Summarize the current article
     - **(n)** Skip the current article
     - **(q)** Skip all remaining articles

5. **Summaries via DeepSeek**  
   - Uses the DeepSeek Chat API to generate Turkish summaries of the selected articles.

6. **Timestamped Output Folder**  
   - Each run creates a new folder named after the current date and time (e.g., `2025-01-12 14.32.09`), storing:
     - `news_list.json`  
     - `final_news_list.json`  
     - `selected_articles.json`  
     - `summarized_articles.json`  
     - `summaries.md` (a Markdown file of all summarized articles)

---

## Requirements

1. **Python 3.7+**  
2. **Chrome Browser** (or a Chromium-based browser supported by [ChromeDriver](https://chromedriver.chromium.org/))
3. **Dependencies** listed in `requirements.txt`.
You also need a **DeepSeek** API key to enable article summarization. Please see **[DeepSeek’s documentation](https://api.deepseek.com)** for instructions on how to obtain an API key.

---

## Installation & Setup

1. **Clone or download** this repository:

   ```bash
   git clone https://github.com/mertcansegmen/yahoo-finance-portfolio-news-summarizer.git
   ```

2. **Install dependencies**:

   ```bash
   cd yahoo-finance-portfolio-news-summarizer
   pip install -r requirements.txt
   ```

3. **Create a `.env` file** in the project root (same directory as `main.py`), containing:

   ```plaintext
   DEEPSEEK_API_KEY=<your_deepseek_api_key>
   ```

4. **Adjust script settings** (optional):
   - `SCROLL_DOWN_ATTEMPTS` in the code to change how many times the script scrolls to load more news. You can play around with this value to change the number of the news fetched initially.
   - `SCROLL_DOWN_PAUSE_TIME` in the code to change how long the script will wait before scrolling again to load more news. You may need to change this if your internet connection is slow or for some reason it takes longer to load the news on scroll.
   - `chrome_options.add_argument('--headless')` if you wish to run Chrome in headless mode. But this will be mandatory initially as the user must login to yahoo finance the first time.

---

## Usage

1. **Run the script**:

   ```bash
   python main.py
   ```

   Where `main.py` is the entry point file.

2. **Wait for browser to open**:
   - If you are not already logged in to Yahoo, the script will pause to let you log in.
   - After logging in, press **Enter** in the terminal to let the script continue.

3. **Script workflow**:
   1. It scrapes the Yahoo Finance portfolios page to gather news items and saves the raw data to `news_list.json`.
   2. It opens each article, clicks the “Story Continues” button when present, and extracts the content.  
   3. Results of this step are saved to `final_news_list.json`.
   4. The script asks you (in the terminal) for each parsed article:
      - **(y)** to summarize,
      - **(n)** to skip,
      - **(q)** to skip all further articles.
   5. The chosen articles are saved to `selected_articles.json`.
   6. Summaries are requested from the DeepSeek API for each selected article. Summaries are saved in `summarized_articles.json`.
   7. A `summaries.md` file is created with the summary info in Markdown format.

4. **All files** are stored in a **date-time stamped folder** for easy reference. For example:  

   ```plaintext
   2025-01-12 14-32-09/
   ├── news_list.json
   ├── final_news_list.json
   ├── selected_articles.json
   ├── summarized_articles.json
   └── summaries.md
   ```

---

## Troubleshooting

- **Login Issue**:  
  If the script can’t find any news after scraping, you might not be logged in to Yahoo. The script will ask you to manually log in. If you close the browser before the script finishes, you may need to re-run and log in again.

- **Browser Not Found**:  
  Make sure you have a version of Google Chrome installed that matches your installed [ChromeDriver](https://chromedriver.chromium.org/) version. The script uses [WebDriver Manager](https://pypi.org/project/webdriver-manager/) to automatically manage ChromeDriver.

- **DeepSeek Errors**:  
  Verify your `.env` file has `DEEPSEEK_API_KEY` set correctly. Confirm your API plan usage or tokens remain valid.

---

## Contributing

1. **Fork the repository** on GitHub.
2. **Create a new feature branch**:

   ```bash
   git checkout -b feature/my-new-feature
   ```

3. **Commit your changes**:

   ```bash
   git commit -am 'Add some feature'
   ```

4. **Push to the branch**:

   ```bash
   git push origin feature/my-new-feature
   ```

5. **Open a Pull Request** on GitHub.

---

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT). See the [LICENSE](LICENSE) file for details.
