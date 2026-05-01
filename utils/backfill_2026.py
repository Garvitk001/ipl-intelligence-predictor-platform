import requests
import pandas as pd
import os
import time
import re
from dotenv import load_dotenv

# --- BULLETPROOF PATH CONFIGURATION ---
# 1. Get the directory where THIS script (backfill_2026.py) lives (the 'utils' folder)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Go up one level to the main project folder
BASE_DIR = os.path.dirname(SCRIPT_DIR)

# 3. Load the .env file explicitly from the main project folder
load_dotenv(os.path.join(BASE_DIR, '.env'))
CRICBUZZ_KEY_7 = os.getenv("CRICBUZZ_KEY_7") 
API_HOST = "cricbuzz-cricket.p.rapidapi.com"

# 4. Construct the absolute path to the CSV file
MATCHES_CSV_PATH = os.path.join(BASE_DIR, 'data', 'raw', 'matches_current_season.csv')

def run_backfill():
    print(f"📁 Target Database Path: {MATCHES_CSV_PATH}")
    print("🚀 Starting Advanced IPL 2026 Historical Backfill...")
    
    if not CRICBUZZ_KEY_7:
        print("❌ Error: Could not find CRICBUZZ_KEY_7 in .env file!")
        return

    url = "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/recent"
    headers = {"X-RapidAPI-Key": CRICBUZZ_KEY_7, "X-RapidAPI-Host": API_HOST}

    try:
        raw_response = requests.get(url, headers=headers)
        
        if raw_response.status_code != 200:
            print(f"❌ API CRASH! Status Code: {raw_response.status_code}")
            print(f"Details: {raw_response.text}")
            return
            
        response = raw_response.json()
        
        if 'message' in response:
            print(f"⚠️ API EXHAUSTED OR BLOCKED: {response['message']}")
            return

        missed_matches = []
        
        for match_type in response.get('typeMatches', []):
            for series in match_type.get('seriesMatches', []):
                series_name = series.get('seriesAdWrapper', {}).get('seriesName', '')
                
                if 'Indian Premier League' in series_name or 'IPL' in series_name:
                    print(f"✅ Found IPL Series: {series_name}")
                    
                    for match in series.get('seriesAdWrapper', {}).get('matches', []):
                        match_info = match.get('matchInfo', {})
                        if match_info.get('state', '') == 'Complete':
                            
                            team1 = match_info['team1']['teamName']
                            team2 = match_info['team2']['teamName']
                            city = match_info.get('venueInfo', {}).get('city', 'Unknown')
                            venue = match_info.get('venueInfo', {}).get('ground', 'Unknown Stadium')
                            status = match_info.get('status', '')
                            
                            toss_winner = match_info.get('tossResults', {}).get('tossWinnerName', 'Unknown')
                            toss_decision = match_info.get('tossResults', {}).get('decision', 'Unknown')
                            
                            win_by_runs = 0
                            win_by_wickets = 0
                            
                            if 'runs' in status.lower():
                                match_val = re.search(r'(\d+)\s*runs', status, re.IGNORECASE)
                                if match_val: win_by_runs = int(match_val.group(1))
                            elif 'wickets' in status.lower():
                                match_val = re.search(r'(\d+)\s*wickets', status, re.IGNORECASE)
                                if match_val: win_by_wickets = int(match_val.group(1))
                            
                            match_id = f"{team1}_vs_{team2}_{match_info.get('matchEndTimestamp', time.time())}"
                            
                            winner = "Tie/No Result"
                            if team1 in status: winner = team1
                            elif team2 in status: winner = team2
                            
                            missed_matches.append({
                                'id': match_id,  
                                'season': '2026', 
                                'date': time.strftime('%Y-%m-%d', time.localtime(int(match_info.get('matchEndTimestamp', time.time()*1000))/1000)),
                                'team1': team1,
                                'team2': team2,
                                'toss_winner': toss_winner,
                                'toss_decision': toss_decision.lower(),
                                'winner': winner,
                                'win_by_runs': win_by_runs,
                                'win_by_wickets': win_by_wickets,
                                'venue': venue,
                                'city': city,
                                'margin_string': status
                            })

        if not missed_matches:
            print("⚠️ API call succeeded, but no COMPLETED IPL matches were found in the last 48 hours.")
            return

        # Convert to DataFrame
        new_data = pd.DataFrame(missed_matches)
        
        # Ensure the target directory exists
        os.makedirs(os.path.dirname(MATCHES_CSV_PATH), exist_ok=True)
        
        if not os.path.exists(MATCHES_CSV_PATH):
            new_data.to_csv(MATCHES_CSV_PATH, index=False)
            print(f"📁 Created advanced database! Backfilled {len(new_data)} matches.")
        else:
            existing_df = pd.read_csv(MATCHES_CSV_PATH)
            
            if 'id' not in existing_df.columns:
                print("♻️ Old database schema detected. Upgrading...")
                new_data.to_csv(MATCHES_CSV_PATH, index=False)
            else:
                # Find matches that are in new_data but NOT in existing_df
                unique_new_data = new_data[~new_data['id'].isin(existing_df['id'])]
                
                if unique_new_data.empty:
                    print("👍 Database is already fully up-to-date!")
                else:
                    unique_new_data.to_csv(MATCHES_CSV_PATH, mode='a', header=False, index=False)
                    print(f"💾 Successfully appended {len(unique_new_data)} new matches to your master CSV!")

    except Exception as e:
        print(f"❌ Backfill Error: {e}")

if __name__ == "__main__":
    run_backfill()