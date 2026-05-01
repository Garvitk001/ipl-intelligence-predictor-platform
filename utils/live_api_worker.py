import time
import json
import os
import pandas as pd
import joblib
import subprocess
import requests
import re
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime , timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))
# 🔑 8-CYLINDER DYNAMIC KEY LOADER
API_KEYS = []
# range(1, 9) checks numbers 1 through 8!
for i in range(1, 9): 
    key = os.getenv(f'CRICBUZZ_KEY_{i}')
    if key:
        API_KEYS.append(key)

print(f"🔋 Engine started with {len(API_KEYS)} API Keys loaded!")
current_key_index = 0
print("Starting Live API Worker (Production + Weather + Auto-Alerts + Gen AI)...")

# 1. Load API Keys
load_dotenv('../.env')
CRICBUZZ_KEY = os.getenv("CRICBUZZ_KEY")
WEATHER_KEY = os.getenv("WEATHER_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Configure Gemini (Auto-Selecting Model) ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Automatically find a valid model that supports text generation
    selected_model_name = None
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                selected_model_name = m.name
                # If we find a 'flash' or 'pro' model, prioritize it and break the loop
                if 'flash' in m.name.lower() or 'pro' in m.name.lower():
                    break
                    
        if selected_model_name:
            print(f"🤖 Auto-selected Gemini Model: {selected_model_name}")
            llm = genai.GenerativeModel(selected_model_name)
        else:
            print("⚠️ No valid text generation models found for this API key.")
            llm = None
    except Exception as e:
        print(f"⚠️ Failed to fetch Gemini models: {e}")
        llm = None
else:
    print("⚠️ No Gemini API Key found. AI Commentary disabled.")
    llm = None

def send_telegram_alert(message):
    """Sends a markdown formatted message to your Telegram Channel."""
    # 🔍 Now looking for the exact variable names you used!
    bot_token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("⚠️ Telegram credentials missing. Skipping alert.")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,      # This will pass "@ai_cricket_alerts" perfectly
        "text": message,
        "parse_mode": "Markdown" # Lets us use bold and italic text!
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"⚠️ Telegram Error: {response.text}")
    except Exception as e:
        print(f"⚠️ Telegram Connection Error: {e}")

def get_live_weather(city):
    if not WEATHER_KEY:
        return None
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city},IN&appid={WEATHER_KEY}&units=metric"
        response = requests.get(url).json()
        if response.get('cod') == 200:
            humidity = response['main']['humidity']
            return {
                'temp': response['main']['temp'],
                'humidity': humidity,
                'condition': response['weather'][0]['main'],
                'dew_warning': True if humidity > 65 else False 
            }
    except Exception as e:
        pass
    return None

def fetch_cricbuzz_live_data():
    """Fetches live match data, handles upcoming schedules, and runs the ML engines."""
    global current_key_index  # 👈 REQUIRED FOR THE 8-CYLINDER ROTATOR
    
    # 1. Check if keys loaded properly
    if not API_KEYS:
        print("❌ CRITICAL ERROR: No API keys found in .env file!")
        return None

    # 2. Grab the current active key
    active_key = API_KEYS[current_key_index]
    
    url = "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/live"
    headers = {"X-RapidAPI-Key": active_key, "X-RapidAPI-Host": "cricbuzz-cricket.p.rapidapi.com"}
    
    # Initialize a clean state with the current timestamp!
    base_payload = {
        'match_active': False,
        'todays_matches': [],
        'timestamp': time.strftime('%I:%M:%S %p')
    }
    
    try:
        response = requests.get(url, headers=headers).json()
        
        # =========================================================
        # 🚨 THE 8-CYLINDER AUTO-SWAPPER
        # =========================================================
        if 'message' in response and 'exceeded' in str(response.get('message', '')).lower():
            print(f"🚨 Key {current_key_index + 1} exhausted! Attempting rotation...")
            
            # Move to the next key in the list
            current_key_index += 1
            
            # Check if we are completely out of all 8 keys
            if current_key_index >= len(API_KEYS):
                print("💀 ALL API KEYS EXHAUSTED! System going to sleep.")
                return None 
                
            print(f"🔄 Swapping to Key {current_key_index + 1} and retrying instantly...")
            # Recursively call the function again so it instantly tries the next key!
            return fetch_cricbuzz_live_data() 
        # =========================================================

        live_payload = None
        
        for match_type in response.get('typeMatches', []):
            for series in match_type.get('seriesMatches', []):
                series_name = series.get('seriesAdWrapper', {}).get('seriesName', '')
                if 'Indian Premier League' not in series_name and 'IPL' not in series_name: 
                    continue 
                    
                for match in series.get('seriesAdWrapper', {}).get('matches', []):
                    match_info = match.get('matchInfo', {})
                    match_score = match.get('matchScore', {})
                    
                    state = match_info.get('state', '')
                    # SAFE EXTRACTION: Prevents crashing if team names aren't set yet!
                    team1 = match_info.get('team1', {}).get('teamName', 'TBA')
                    team2 = match_info.get('team2', {}).get('teamName', 'TBA')
                    city = match_info.get('venueInfo', {}).get('city', 'Stadium')
                    venue = match_info.get('venueInfo', {}).get('ground', 'Unknown Stadium')
                    status = match_info.get('status', 'Scheduled')
                    
                    # --- GRAB LIVE BATTER AND BOWLER ---
                    striker = "Unknown"
                    current_bowler = "Unknown"
                    if 'batsman' in match_score and len(match_score['batsman']) > 0:
                        striker = match_score['batsman'][0].get('batName', 'Unknown')
                    if 'bowler' in match_score and len(match_score['bowler']) > 0:
                        current_bowler = match_score['bowler'][0].get('bowlName', 'Unknown')
                    
                    # 1. ALWAYS ADD TO TODAY'S SCHEDULE
                    base_payload['todays_matches'].append({
                        'team1': team1, 'team2': team2, 
                        'state': state, 'status': status, 'city': city,
                        'venue': venue,
                        'match_info': match_info
                    })
                    
                    # 2. IS IT CURRENTLY LIVE? (FIXED: Added Timeouts and Breaks to the Whitelist!)
                    if state in ['In Progress', 'Strategic Timeout', 'Innings Break', 'Toss'] and live_payload is None:
                        weather_data = get_live_weather(city)
                        if 'team2Score' in match_score:
                            target = match_score['team2Score']['inngs1']['target'] if 'target' in match_score.get('team2Score', {}).get('inngs1', {}) else 180
                            inngs1_score = match_score['team2Score']['inngs1']
                            cur_score = inngs1_score.get('runs', 0)
                            wickets = inngs1_score.get('wickets', 0)
                            overs = float(inngs1_score.get('overs', 0.0))
                            balls_bowled = int(overs) * 6 + int(round((overs % 1) * 10))
                            balls_left = 120 - balls_bowled
                            runs_req = max(0, target - cur_score)
                            crr = (cur_score / max(1, balls_bowled)) * 6
                            rrr = (runs_req / max(1 / 6, balls_left / 6))

                            live_payload = {
                                'match_active': True, 'innings': 2, 'city': city, 'weather': weather_data,
                                'batting_team': team2, 'bowling_team': team1, 'target': target, 'cur_score': cur_score,
                                'wickets': wickets, 'overs': overs, 'runs_required': runs_req, 'balls_left': balls_left,
                                'wickets_in_hand': 10 - wickets, 'crr': crr, 'rrr': rrr,
                                'striker': striker, 'current_bowler': current_bowler
                            }
                        
                        elif 'team1Score' in match_score:
                            inngs1_score = match_score['team1Score']['inngs1']
                            cur_score = inngs1_score.get('runs', 0)
                            wickets = inngs1_score.get('wickets', 0)
                            overs = float(inngs1_score.get('overs', 0.0))
                            
                            balls_bowled = int(overs) * 6 + int(round((overs % 1) * 10))
                            balls_left = 120 - balls_bowled
                            crr = (cur_score / max(1, balls_bowled)) * 6
                            
                            # --- DYNAMIC PAR SCORE ALGORITHM ---
                            base_proj = cur_score + (crr * (balls_left / 6))
                            expected_wickets = (balls_bowled / 120) * 8
                            wicket_factor = 1.0 - ((wickets - expected_wickets) * 0.05)
                            
                            acceleration = 1.0
                            if balls_left <= 30:
                                if wickets <= 4:
                                    acceleration = 1.30
                                elif wickets >= 7:
                                    acceleration = 0.80
                                    
                            projected_score = int(base_proj * wicket_factor * acceleration)
                            projected_score = max(cur_score, projected_score)

                            live_payload = {
                                'match_active': True, 'innings': 1, 'city': city, 'weather': weather_data,
                                'batting_team': team1, 'bowling_team': team2, 'cur_score': cur_score,
                                'wickets': wickets, 'overs': overs, 'crr': crr, 'projected_score': projected_score,
                                'striker': striker, 'current_bowler': current_bowler # FIXED: Added to Innings 1!
                            }
                            
                    # 3. DID IT JUST FINISH? (Run our new ETL Pipeline)
                    elif state == 'Complete':
                        try:
                            log_completed_match({
                                'team1': team1, 'team2': team2,
                                'status': status, 'city': city,
                                'match_info': match_info
                            })
                        except:
                            pass
        
        # --- JSON SAVE FIX ---
        if live_payload:
            live_payload['todays_matches'] = base_payload['todays_matches']
            live_payload['timestamp'] = base_payload['timestamp']
            final_payload = live_payload
        else:
            final_payload = base_payload

        # ✅ PERMANENT FIX: Force it into the main project folder
        save_dir = os.path.join(BASE_DIR, 'data', 'processed')
        os.makedirs(save_dir, exist_ok=True)
        
        state_file = os.path.join(save_dir, 'live_match_state.json')
        with open(state_file, 'w') as f:
            json.dump(final_payload, f)
            
        return final_payload
            
    except Exception as e:
        print(f"❌ API Error: {e}")
        return None

# ==========================================
# 🧠 LOAD ML MODELS HERE
# ==========================================
# Finds the directory of this script, then steps up one level
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model_dir = os.path.join(BASE_DIR, 'models')

try:
    live_pp = joblib.load(os.path.join(model_dir, 'live_chase_powerplay.pkl'))
    live_mid = joblib.load(os.path.join(model_dir, 'live_chase_middle.pkl'))
    live_death = joblib.load(os.path.join(model_dir, 'live_chase_death.pkl'))
    print("✅ Live Phase Models loaded successfully.")
except Exception as e:
    print(f"❌ Error loading ML models: {e}")
    live_pp, live_mid, live_death = None, None, None


def predict_win_prob(data):
    global live_pp, live_mid, live_death 
    
    overs = data['overs']
    if overs <= 5: 
        active_model = live_pp
        phase = "Powerplay"
    elif overs <= 14: 
        active_model = live_mid
        phase = "Middle Overs"
    else: 
        active_model = live_death
        phase = "Death Overs"
        
    features = pd.DataFrame({
        'runs_required': [data['runs_required']],
        'balls_left': [data['balls_left']],
        'wickets_in_hand': [data['wickets_in_hand']],
        'crr': [data['crr']],
        'rrr': [data['rrr']]
    })
    
    base_prob = active_model.predict_proba(features)[0][1]
    if data.get('weather') and data['weather'].get('dew_warning'):
        base_prob = min(base_prob + 0.03, 0.99)
        
    return base_prob, phase

def generate_ai_commentary(data):
    """Uses Gemini to write a dynamic, 2-sentence match recap."""
    if not llm: return "AI Commentary offline (Missing API Key)."
    
    try:
        if data['innings'] == 2:
            prompt = (f"Act as a highly energetic, professional IPL cricket commentator like Ian Bishop or Harsha Bhogle. "
                      f"{data['batting_team']} is chasing a target of {data['target']} against {data['bowling_team']}. "
                      f"Current score is {data['cur_score']}/{data['wickets']} in {data['overs']} overs. "
                      f"They need {data['runs_required']} runs off {data['balls_left']} balls. "
                      f"The machine learning model gives them a {data['chasing_win_prob']*100:.1f}% chance of winning. "
                      f"Write exactly TWO thrilling sentences summarizing the current state of the game. Do not use hashtags.")
        else:
            prompt = (f"Act as a highly energetic IPL cricket commentator. "
                      f"{data['batting_team']} is batting first against {data['bowling_team']}. "
                      f"Score: {data['cur_score']}/{data['wickets']} in {data['overs']} overs. "
                      f"Current run rate is {data['crr']:.2f}. "
                      f"Write exactly TWO thrilling sentences summarizing their innings so far. Do not use hashtags.")
        
        response = llm.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "The AI commentator is currently catching their breath..."

def log_completed_match(match):
    """ETL Pipeline: Automatically saves completed live matches to our database."""
    csv_path = '../data/raw/matches_current_season.csv'
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    
    match_info = match.get('match_info', {})
    team1 = match['team1']
    team2 = match['team2']
    status = match['status']
    city = match['city']
    venue = match_info.get('venueInfo', {}).get('ground', 'Unknown Stadium')
    
    # Grab Toss Info
    toss_winner = match_info.get('tossResults', {}).get('tossWinnerName', 'Unknown')
    toss_decision = match_info.get('tossResults', {}).get('decision', 'Unknown')
    
    # Parse win_by_runs and win_by_wickets using Regex
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
    
    new_data = pd.DataFrame([{
        'id': match_id,
        'season': '2026',
        'date': time.strftime('%Y-%m-%d'),
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
    }])

    if not os.path.exists(csv_path):
        new_data.to_csv(csv_path, index=False)
        print(f"📁 Created Advanced Database! Logged: {team1} vs {team2}")
    else:
        existing_df = pd.read_csv(csv_path)
        if match_id not in existing_df['id'].values:
            new_data.to_csv(csv_path, mode='a', header=False, index=False)
            print(f"✅ AUTO-PIPELINE: Successfully logged new completed match -> {status}")
            
            try:
                send_telegram_alert(f"💾 *Database Auto-Updated!*\nMatch saved to CSV:\n{status}")
            except:
                pass

# --- GLOBAL MEMORY FOR MLOPS ---
completed_matches_memory = set()



def get_terminal_prediction(team1, team2, venue_name):
    """Runs a quick headless ML prediction for the terminal dashboard"""
    try:
        # Fallback mapping
        team_mapping = {
            'RCB': 'Royal Challengers Bengaluru', 'CSK': 'Chennai Super Kings', 'MI': 'Mumbai Indians', 
            'PBKS': 'Punjab Kings', 'DC': 'Delhi Capitals', 'SRH': 'Sunrisers Hyderabad', 
            'RR': 'Rajasthan Royals', 'KKR': 'Kolkata Knight Riders', 'GT': 'Gujarat Titans', 'LSG': 'Lucknow Super Giants'
        }
        t1 = team_mapping.get(team1, team1)
        t2 = team_mapping.get(team2, team2)

        # Get Form & Dominance
        t1_form = form_df[form_df['team'] == t1]['rolling_5_form'].iloc[-1] if not form_df[form_df['team'] == t1].empty else 0.5
        t2_form = form_df[form_df['team'] == t2]['rolling_5_form'].iloc[-1] if not form_df[form_df['team'] == t2].empty else 0.5
        
        matchup_str = ' vs '.join(sorted([t1, t2]))
        dom_val = dom_df[(dom_df['matchup'] == matchup_str) & (dom_df['winner'] == t1)]['dominance_score']
        dom_val = dom_val.iloc[0] if not dom_val.empty else 0.5

        # Fuzzy Venue Match
        v_dna = 50.0 
        mapped_venue = venue_df['venue'].iloc[0] 
        for known_venue in venue_df['venue'].values:
            if str(known_venue).split(' ')[0].lower() in venue_name.lower(): 
                v_dna = venue_df[venue_df['venue'] == known_venue]['bat_first_win_pct'].iloc[0]
                mapped_venue = known_venue
                break

        # Run Model
        input_data = pd.DataFrame({
            'team1': [t1], 'team2': [t2], 'venue': [mapped_venue], 
            'toss_decision': ['field'], 'venue_bat_first_win_pct': [v_dna],
            'team1_home': [0], 'team2_home': [0], 'team1_won_toss': [1],
            'form_diff': [t1_form - t2_form], 'team1_dominance': [dom_val]
        })

        input_transformed = preprocessor.transform(input_data)
        probs = model.predict_proba(input_transformed)[0]

        if probs[1] > probs[0]:
            return f"🔮 AI Prediction: {t1} ({probs[1]*100:.1f}%) | {t2} ({probs[0]*100:.1f}%)"
        else:
            return f"🔮 AI Prediction: {t2} ({probs[0]*100:.1f}%) | {t1} ({probs[1]*100:.1f}%)"
            
    except Exception as e:
        return "🔮 AI Prediction: Analyzing closer to Toss..."

def run_worker():
    # 🎯 This find the absolute path to the 'ipl-predictor' folder
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 🎯 This forces the file to always be in the main project data folder
    state_file = os.path.join(BASE_DIR, 'data', 'processed', 'live_match_state.json')
    
    os.makedirs(os.path.dirname(state_file), exist_ok=True)
    
    print("📡 Worker is active. Smart Polling, Auto-Alerts, Momentum, & Gen AI ENABLED!")
    
    last_win_prob = None 
    match_history = [] 
    current_innings_tracker = None
    innings_break_alert_sent = False
    highest_over_seen = -1.0
    
    while True:
        try:
            # 1. FETCH DATA (Or Fallback to Fake Test Data if Quota Empty)
            live_data = fetch_cricbuzz_live_data() 
            
            # +++ FORCED FIREBASE TEST FALLBACK +++
            if not live_data:
                live_data = {
                    'match_active': False, 
                    'message': 'API Quota Empty - Forced Test!', 
                    'timestamp': time.strftime('%I:%M:%S %p'),
                    'todays_matches': [
                        {
                            'team1': 'Chennai Super Kings',
                            'team2': 'Kolkata Knight Riders',
                            'venue': 'MA Chidambaram Stadium',
                            'city': 'Chennai',
                            'status': 'Match starts at 07:30 PM',
                            'state': 'Upcoming'
                        }
                    ]
                }
            
            # --- DEFAULT BASELINE POLLING ---
            poll_interval = 300 
            
            # =========================================================
            # 🏏 SCENARIO A: MATCH IS ACTIVELY RUNNING
            # =========================================================
            if live_data and live_data.get('match_active'):
                innings = live_data.get('innings', 1)
                
                # FLAT 3-MINUTE POLLING: No matter if it's a break or timeout!
                print(f"[{time.strftime('%X')}] 🔥 Match Active (Innings {innings}). Polling in 3 minutes...")
                poll_interval = 180  

                # --- MOMENTUM TRACKER & ALERTS ---
                if current_innings_tracker != live_data['innings']:
                    match_history = [] 
                    highest_over_seen = -1.0
                    current_innings_tracker = live_data['innings']
                    if live_data['innings'] == 1:
                        print(f"[{time.strftime('%X')}] 🔔 Alert: 1st Innings Started!")
                    elif live_data['innings'] == 2:
                        print(f"[{time.strftime('%X')}] 🔔 Alert: 2nd Innings Chase Started!")
                        innings_break_alert_sent = False

                match_history.append({'score': live_data.get('cur_score', 0), 'wickets': live_data.get('wickets', 0)})
                if len(match_history) > 4:
                    match_history.pop(0)
                
                runs_last_18 = 0
                wickets_last_18 = 0
                if len(match_history) > 1:
                    oldest = match_history[0]
                    runs_last_18 = max(0, live_data.get('cur_score', 0) - oldest['score'])
                    wickets_last_18 = max(0, live_data.get('wickets', 0) - oldest['wickets'])
                
                live_data['runs_last_18'] = runs_last_18
                live_data['wickets_last_18'] = wickets_last_18

                if innings == 2:
                    try:
                        win_prob, current_phase = predict_win_prob(live_data)
                        live_data['chasing_win_prob'] = float(win_prob)
                        live_data['current_phase'] = current_phase
                    except Exception as e:
                        print(f"⚠️ ML Prediction Error: {e}")

                try:
                    print(f"[{time.strftime('%X')}] 🤖 Generating AI Commentary...")
                    live_data['ai_commentary'] = generate_ai_commentary(live_data)
                except:
                    pass

                # ==========================================
                # 📨 TELEGRAM BROADCAST (SMART ROUTING)
                # ==========================================
                try:
                    is_innings_break = (live_data['innings'] == 1 and (live_data.get('overs', 0) >= 20.0 or live_data.get('wickets', 0) == 10))

                    if is_innings_break:
                        if not innings_break_alert_sent:
                            final_score = live_data.get('cur_score', 0)
                            msg = f"☕ *INNINGS BREAK* ☕\n\n"
                            msg += f"*{live_data.get('batting_team', 'Team')}* finishes with *{final_score}/{live_data.get('wickets', 0)}*\n"
                            msg += f"🎯 *{live_data.get('bowling_team', 'Team')}* will need *{final_score + 1} runs* to win.\n\n"
                            msg += f"⏳ The run-chase will begin in roughly 15-20 minutes.\n"
                            msg += f"🤖 _Our AI Win Probability Engine will lock on to the chase on the very first ball!_"
                            
                            print(f"[{time.strftime('%X')}] 📨 Broadcasting Innings Break to Telegram...")
                            send_telegram_alert(msg)
                            innings_break_alert_sent = True
                        else:
                            print(f"[{time.strftime('%X')}] ☕ Innings Break active. Skipping Telegram spam.")
                    
                    else:
                        t1 = live_data.get('batting_team', 'Team')
                        t2 = live_data.get('bowling_team', 'Team')
                        score = f"{live_data.get('cur_score', 0)}/{live_data.get('wickets', 0)}"
                        overs = live_data.get('overs', 0)
                        crr = live_data.get('crr', 0)
                        striker = live_data.get('striker', 'Unknown')
                        bowler = live_data.get('current_bowler', 'Unknown')
                        
                        msg = f"🏏 *LIVE IPL UPDATE* 🏏\n*{t1} vs {t2}*\n\n"
                        msg += f"📊 *Score:* {score} ({overs} Ov)\n📈 *CRR:* {crr:.2f}\n"
                        
                        if live_data['innings'] == 1:
                            msg += f"🎯 *Projected Score:* {live_data.get('projected_score', 'Calculating...')}\n"
                        else:
                            target = live_data.get('target', 0)
                            req = live_data.get('runs_required', 0)
                            balls = live_data.get('balls_left', 0)
                            win_p = live_data.get('chasing_win_prob', 0) * 100
                            msg += f"🎯 *Target:* {target} | *Need:* {req} in {balls} balls\n"
                            msg += f"🔮 *AI Win Prob:* {win_p:.1f}%\n"

                        # Only add the "At The Crease" section if we actually have player names!
                        if striker != 'Unknown' and bowler != 'Unknown':
                            msg += f"\n⚔️ *At The Crease:*\n🏏 {striker}\n⚾ {bowler}\n"
                        
                        if live_data.get('ai_commentary'):
                            short_comm = live_data['ai_commentary'][:200] + "..." if len(live_data['ai_commentary']) > 200 else live_data['ai_commentary']
                            msg += f"\n🤖 *AI Desk:* {short_comm}"

                        print(f"[{time.strftime('%X')}] 📨 Broadcasting to Telegram...")
                        send_telegram_alert(msg)
                        
                except Exception as e:
                    print(f"⚠️ Failed to build Telegram message: {e}")

            # =========================================================
            # ⏸️ SCENARIO B: NO MATCH RUNNING (MORNING / POST-MATCH)
            # =========================================================
            else:
                last_win_prob = None 
                match_history = []
                current_innings_tracker = None
                
                now = datetime.now()
                all_completed = True
                
                if live_data and 'todays_matches' in live_data and len(live_data['todays_matches']) > 0:
                    for match in live_data['todays_matches']:
                        state = match.get('state', '')
                        match_name = f"{match.get('team1')}_vs_{match.get('team2')}"
                        
                      # --- TRIGGER MLOPS IF A MATCH JUST FINISHED ---
                        if state == 'Complete':
                            if match_name not in completed_matches_memory:
                                print(f"\n[{time.strftime('%X')}] 🏆 MATCH FINISHED: {match_name}")
                                print("⚙️ Triggering Autonomous MLOps Pipeline...")
                                try:
                                    print("   -> Downloading new match data...")
                                    subprocess.run(["python", "utils/backfill_2026.py"]) # <--- IT IS ALREADY HERE!
                                    print("   -> Retraining AI Models...")
                                    subprocess.run(["python", "src/phase2_preprocessing.py"])
                                    subprocess.run(["python", "src/phase4_training.py"])
                                    print("✅ Pipeline Complete! CSVs and Models Updated.")
                                except Exception as e:
                                    print(f"⚠️ MLOps Error: {e}")
                                
                                completed_matches_memory.add(match_name)
                        else:
                            # We found a match that is NOT complete yet
                            all_completed = False
                            
                    # --- DEEP HIBERNATION LOGIC ---
                    if all_completed:
                        print(f"[{time.strftime('%X')}] 🌙 All matches finished! Preparing for Deep Sleep...")
                        
                        print("📅 Fetching tomorrow's schedule before sleeping...")
                        try:
                            subprocess.run(["python", "utils/auto_schedule.py"])
                            subprocess.run(["python", "utils/fetch_squads.py"])
                        except Exception as e:
                            print(f"⚠️ Schedule Auto-Update Failed: {e}")

                        print("💤 System going offline until tomorrow 10:00 AM.")
                        tomorrow = now + timedelta(days=1)
                        target_time = tomorrow.replace(hour=10, minute=0, second=0)
                        poll_interval = int((target_time - now).total_seconds())
                    else:
                        # There are upcoming matches today! Let's calculate the sleep time.
                        if now.hour < 14: # Morning (Before 2 PM)
                            target_time = now.replace(hour=14, minute=45, second=0) # Wake at 2:45 PM for toss
                            poll_interval = int((target_time - now).total_seconds())
                            print(f"[{time.strftime('%X')}] ⏰ Morning Hibernation. Waking up at 2:45 PM.")
                        elif now.hour >= 18 and now.hour < 19: # Break between afternoon/evening match
                            target_time = now.replace(hour=18, minute=45, second=0) # Wake at 6:45 PM for evening toss
                            poll_interval = int((target_time - now).total_seconds())
                            print(f"[{time.strftime('%X')}] 🌅 Evening Nap. Waking up at 6:45 PM.")
                        else:
                            # Close to toss time, check every 5 minutes
                            print(f"[{time.strftime('%X')}] ⏳ Toss approaching. Polling in 5 minutes...")
                            poll_interval = 300
                else:
                    # 🕒 IPL Prime Time Check
                    # If the API is empty but it's between 2:00 PM and 11:00 PM, 
                    # do NOT sleep until tomorrow. Take a 30-minute nap instead!
                    if 14 <= now.hour < 23:
                        print(f"[{time.strftime('%X')}] ⏸️ API is empty (Pre-Toss). Taking a 30-minute nap...")
                        poll_interval = 1800  # 30 minutes
                    else:
                        print(f"[{time.strftime('%X')}] 🌙 No IPL Matches active. Deep sleep until tomorrow 10:00 AM.")
                        tomorrow = now + timedelta(days=1) if now.hour >= 23 else now
                        target_time = tomorrow.replace(hour=10, minute=0, second=0)
                        
                        if target_time > now:
                            poll_interval = int((target_time - now).total_seconds())
                        else:
                            poll_interval = 3600  # Fallback to 1 hour

            # =========================================================
            # 🛡️ TIME-TRAVEL BLOCKER (STALE CACHE PREVENTION)
            # =========================================================
            if live_data and live_data.get('match_active'):
                current_over = float(live_data.get('overs', 0.0))
                
                # If the API sends us backward in time, DELETE the payload!
                if current_over < highest_over_seen and live_data['innings'] == current_innings_tracker:
                    print(f"[{time.strftime('%X')}] 🛡️ STALE CACHE BLOCKED! API sent {current_over} Ov, but we are already at {highest_over_seen} Ov.")
                    live_data = None # Completely nullify the stale data
                else:
                    highest_over_seen = max(highest_over_seen, current_over)

            # =========================================================
            # ☁️ FIREBASE CLOUD SYNC
            # =========================================================
            if live_data:
                live_data['timestamp'] = time.strftime('%I:%M:%S %p')
                FIREBASE_URL = "https://ipl-intel-db-default-rtdb.firebaseio.com/live_match_state.json"
                try:
                    cloud_response = requests.put(FIREBASE_URL, json=live_data)
                    if cloud_response.status_code == 200:
                        print(f"[{time.strftime('%H:%M:%S')}] ☁️ Data synced to Firebase.")
                except Exception as e:
                    print(f"[{time.strftime('%H:%M:%S')}] ⚠️ Firebase Error: {e}")

            # Sleep calculated by the brain
            print(f"💤 Next API call in {poll_interval // 60} minutes and {poll_interval % 60} seconds...\n")
            time.sleep(poll_interval) 
            
        except Exception as e:
            print(f"⚠️ Worker Loop Error: {e}")
            time.sleep(300) # Fallback sleep if something breaks

if __name__ == "__main__":
    run_worker()