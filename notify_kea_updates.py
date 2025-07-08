import requests
from bs4 import BeautifulSoup
from telegram import Bot
import csv
import time
import os

BOT_TOKEN = "8040176695:AAE5LGSITWbN7ewlEIwlRgQo6MaEPZ4OwWs"
KEA_URL = "https://cetonline.karnataka.gov.in/kea/"
LAST_UPDATE_FILE = "last_kea_update.txt"
USER_DB = "pgcet_users.csv"

# Get latest update text from KEA website
def get_latest_update():
    try:
        response = requests.get(KEA_URL, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        marquee = soup.find("marquee")
        if marquee:
            return marquee.get_text(strip=True)[:200]
    except Exception as e:
        print("Error fetching KEA site:", e)
    return None

# Load last saved update from file
def get_saved_update():
    if not os.path.exists(LAST_UPDATE_FILE):
        return ""
    with open(LAST_UPDATE_FILE, "r", encoding="utf-8") as file:
        return file.read().strip()

# Save the new update to file
def save_new_update(update_text):
    with open(LAST_UPDATE_FILE, "w", encoding="utf-8") as file:
        file.write(update_text)

# Load all user IDs from your CSV
def get_user_ids():
    ids = set()
    try:
        with open(USER_DB, "r") as file:
            reader = csv.reader(file)
            for row in reader:
                if row:
                    ids.add(int(row[0]))
    except Exception as e:
        print("Error reading users:", e)
    return list(ids)

# Send update message to users
def notify_users(bot, message):
    user_ids = get_user_ids()
    for user_id in user_ids:
        try:
            bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            print(f"❌ Could not notify {user_id}: {e}")

# Main check function
def check_for_updates():
    print("🔄 Checking KEA updates...")
    latest = get_latest_update()
    if not latest:
        return

    previous = get_saved_update()
    if latest != previous:
        print("✅ New update found!")
        save_new_update(latest)
        bot = Bot(token=BOT_TOKEN)
        notify_users(bot, f"📢 New KEA Update:\n\n{latest}\n\nVisit: {KEA_URL}")
    else:
        print("ℹ️ No new updates.")

# Schedule: Run every hour
if __name__ == "__main__":
    while True:
        check_for_updates()
        time.sleep(3600)  # Wait 1 hour
