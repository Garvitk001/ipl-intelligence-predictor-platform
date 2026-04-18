import os
import requests
from dotenv import load_dotenv

# Load secrets
load_dotenv()
token = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

print(f"🔍 Found Token: {'Yes' if token else '❌ NO'}")
print(f"🔍 Found Chat ID: {chat_id if chat_id else '❌ NO'}")

if token and chat_id:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": "🏏 *Test Message* from the IPL AI Engine!", 
        "parse_mode": "Markdown"
    }
    
    print("🚀 Sending to Telegram...")
    response = requests.post(url, json=payload)
    print(f"📡 Telegram Response: {response.json()}")