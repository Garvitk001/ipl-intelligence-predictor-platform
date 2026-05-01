import requests
import pandas as pd
import os
import time
from datetime import datetime
from dotenv import load_dotenv

# --- BULLETPROOF PATH CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
load_dotenv(os.path.join(BASE_DIR, '.env'))

# We can just use Key 1 for this, it only runs once a day!
CRICBUZZ_KEY = os.getenv("CRICBUZZ_KEY_8") 
API_HOST = "cricbuzz-cricket.p.rapidapi.com"
SCHEDULE_CSV_PATH = os.path.join(BASE_DIR, 'data', 'raw', 'ipl_2026_schedule.csv')

def fetch_upcoming_schedule():
    print("📅 Connecting to API to fetch upcoming IPL schedule...")
    
    if not CRICBUZZ_KEY:
        print("❌ Error: Could not find API Key in .env file!")
        return

    # 🚨 Notice we are hitting the /upcoming endpoint instead of /recent!
    url = "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/upcoming"
    headers = {"X-RapidAPI-Key": CRICBUZZ_KEY, "X-RapidAPI-Host": API_HOST}

    try:
        response = requests.get(url, headers=headers).json()
        upcoming_matches = []
        
        for match_type in response.get('typeMatches', []):
            for series in match_type.get('seriesMatches', []):
                series_name = series.get('seriesAdWrapper', {}).get('seriesName', '')
                
                if 'Indian Premier League' in series_name or 'IPL' in series_name:
                    
                    for match in series.get('seriesAdWrapper', {}).get('matches', []):
                        match_info = match.get('matchInfo', {})
                        
                        team1 = match_info.get('team1', {}).get('teamName', 'TBA')
                        team2 = match_info.get('team2', {}).get('teamName', 'TBA')
                        venue = match_info.get('venueInfo', {}).get('ground', 'Unknown Stadium')
                        
                        # --- THE TIME FIX: Smart API Key Extraction ---
                        # Look for 'startDate' first, then 'matchStartTimestamp'
                        raw_timestamp = match_info.get('startDate') or match_info.get('matchStartTimestamp')
                        
                        if raw_timestamp:
                            # Convert to integer and calculate
                            dt_object = datetime.fromtimestamp(int(raw_timestamp) / 1000)
                            match_date = dt_object.strftime('%Y-%m-%d')
                            match_time = dt_object.strftime('%I:%M %p')
                        else:
                            # Absolute fallback if API hides the time entirely
                            match_date = time.strftime('%Y-%m-%d')
                            match_time = "07:30 PM" # Default IPL time
                        
                        upcoming_matches.append({
                            'Date': match_date,
                            'Team1': team1,
                            'Team2': team2,
                            'Venue': venue,
                            'Time': match_time
                        })

        if not upcoming_matches:
            print("⚠️ No upcoming IPL matches found in the API.")
            return

        # Convert to DataFrame
        new_schedule_df = pd.DataFrame(upcoming_matches)
        
        # Load existing schedule and merge them safely
        os.makedirs(os.path.dirname(SCHEDULE_CSV_PATH), exist_ok=True)
        
        if not os.path.exists(SCHEDULE_CSV_PATH):
            new_schedule_df.to_csv(SCHEDULE_CSV_PATH, index=False)
            print(f"📁 Created new schedule file with {len(new_schedule_df)} upcoming matches.")
        else:
            existing_df = pd.read_csv(SCHEDULE_CSV_PATH)
            
            # Combine old and new, then drop duplicates based on Date and Teams to prevent double-booking!
            combined_df = pd.concat([existing_df, new_schedule_df])
            combined_df = combined_df.drop_duplicates(subset=['Date', 'Team1', 'Team2'], keep='last')
            
            # Sort by date so it looks nice and clean
            combined_df = combined_df.sort_values(by='Date')
            combined_df.to_csv(SCHEDULE_CSV_PATH, index=False)
            
            print(f"✅ Schedule updated! {len(upcoming_matches)} upcoming matches verified/added.")

    except Exception as e:
        print(f"❌ Schedule Fetch Error: {e}")

if __name__ == "__main__":
    fetch_upcoming_schedule()