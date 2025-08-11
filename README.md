# Roadpolice Exam Slots Telegram Bot

This is a Telegram bot that allows users to find available dates and times for theoretical or practical driving exams in Armenia, by scraping data from the official [roadpolice.am](https://roadpolice.am) website.

## Features
- **/start command & Contact Sharing:** The bot starts with `/start` and prompts the user to share their phone number via a Telegram contact button. This is used to identify the user (the bot only uses it to forward with feedback messages to admin).
- **Interactive Menu:** After receiving the phone number, the bot presents an inline menu for:
  - Selecting the **Exam Center (Subdivision)** by city/branch.
  - Selecting the **Exam Type** – theoretical or practical.
  - Choosing the **Service**:
    - "Find next available slot" – shows the nearest available date and time.
    - "Search by date" – user inputs a date and the bot shows available times on that date.
    - "Search by time" – user inputs a time (HH:MM) and the bot finds upcoming dates that have a slot at that time.
- **Data Fetching from roadpolice.am:** The bot scrapes the roadpolice.am scheduling page for each exam center and exam type to retrieve all available slots. It uses either direct HTTP requests (if an API is available) or falls back to using Selenium with a headless Chrome browser to simulate the booking form and extract free dates and times.
- **Data Caching & Auto-Refresh:** The availability data is cached in memory and automatically refreshed every 2 hours in the background. This ensures that user queries are answered quickly with up-to-date information without scraping the site on every request.
- **Feedback to Admin:** Users can send feedback or messages to the bot admin via a special "Feedback" button. The bot will forward the user's message to the admin (including the user's name and phone number for identification). The user receives a confirmation that their message was sent.

## Technology and Libraries
- Language: **Python 3**
- Telegram Bot Framework: **python-telegram-bot** (asyncio-based version).
- Web Scraping: **Selenium** (using Chrome in headless mode) for dynamic content scraping:contentReference[oaicite:7]{index=7}.
- Scheduling: Using `Application.job_queue` from python-telegram-bot to schedule periodic tasks for data refresh.
- No database is required; data is stored in memory as Python dict.

## Deployment (Free Hosting)
This bot can be deployed on cloud platforms like **Render** or **Railway** which offer free plans for hosting Python applications:contentReference[oaicite:8]{index=8}. Ensure the following:
- The environment has **Google Chrome or Chromium** installed, as well as a matching **ChromeDriver**. On Render, you can use a Dockerfile or add a Build Command to install Chrome (e.g., using apt). On Railway, you may also use a Dockerfile or their buildpacks.
- Set environment variables:
  - `BOT_TOKEN`: Your Telegram bot token from BotFather.
  - `ADMIN_CHAT_ID`: The Telegram chat ID of the admin who should receive feedback messages.
- Install the required Python packages from `requirements.txt`. This includes `selenium` and `webdriver-manager`. `webdriver-manager` will automatically download the appropriate ChromeDriver if not provided.
- Run the bot (for example, `python main.py`). The bot uses polling, so it will keep running and listening for updates. Ensure your service is configured to not sleep or halt, as the bot needs to run continuously.

### Additional Notes:
- **Chrome in Headless Mode:** The bot uses Chrome in headless mode to fetch the exam availability. If you encounter issues running Chrome on the host (for example, missing library dependencies), you may need to install those or use an official Chrome headless Docker image as the base for deployment.
- **Security:** The bot token should be kept secret. Avoid hardcoding it; instead use environment variables. The admin chat ID is used only for forwarding feedback.
- **Usage:** Once deployed, users can start the bot by `/start` in a private chat with the bot, share their contact, then follow the interactive prompts to get exam slot information.

Feel free to modify or extend this code for your specific needs. Good luck!
