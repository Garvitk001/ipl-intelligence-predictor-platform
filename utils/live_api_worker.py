import time
import json
import os
import pandas as pd
import joblib
import requests
import re
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime

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

def send_telegram_alert(text):
    """Sends an automated push notification to your phone."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Missing Telegram Token or Chat ID in .env")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'parse_mode': 'Markdown'
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"⚠️ Failed to send Telegram alert: {e}")

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
    url = "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/live"
    headers = {"X-RapidAPI-Key": CRICBUZZ_KEY, "X-RapidAPI-Host": "cricbuzz-cricket.p.rapidapi.com"}
    
    # Initialize a clean state with the current timestamp!
    base_payload = {
        'match_active': False,
        'todays_matches': [],
        'timestamp': time.strftime('%I:%M:%S %p')
    }
    
    try:
        response = requests.get(url, headers=headers).json()
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
                    
                    # 2. IS IT CURRENTLY LIVE?
                    if state == 'In Progress' and live_payload is None:
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
                                'wickets': wickets, 'overs': overs, 'crr': crr, 'projected_score': projected_score
                            }
                            
                    # 3. DID IT JUST FINISH? (Run our new ETL Pipeline)
                    elif state == 'Complete':
                        log_completed_match({
                            'team1': team1, 'team2': team2,
                            'status': status, 'city': city,
                            'match_info': match_info
                        })
        
        # --- JSON SAVE FIX ---
        if live_payload:
            live_payload['todays_matches'] = base_payload['todays_matches']
            live_payload['timestamp'] = base_payload['timestamp']
            final_payload = live_payload
        else:
            final_payload = base_payload

        os.makedirs('../data/processed', exist_ok=True)
        with open('../data/processed/live_match_state.json', 'w') as f:
            json.dump(final_payload, f)
            
        return final_payload
            
    except Exception as e:
        print(f"❌ API Error: {e}")
        return None

# ==========================================
# 🧠 THE MISSING FIX: LOAD ML MODELS HERE
# ==========================================
model_dir = '../models/'
try:
    live_pp = joblib.load(os.path.join(model_dir, 'live_chase_powerplay.pkl'))
    live_mid = joblib.load(os.path.join(model_dir, 'live_chase_middle.pkl'))
    live_death = joblib.load(os.path.join(model_dir, 'live_chase_death.pkl'))
    print("✅ Live Phase Models loaded successfully.")
except Exception as e:
    print(f"❌ Error loading ML models: {e}")
    live_pp, live_mid, live_death = None, None, None
# ==========================================

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

def run_worker():
    state_file = '../data/processed/live_match_state.json'
    os.makedirs(os.path.dirname(state_file), exist_ok=True)
    
    print("📡 Worker is active. Smart Polling, Auto-Alerts, Momentum, & Gen AI ENABLED!")
    
    last_win_prob = None 
    match_history = [] 
    current_innings_tracker = None
    
    while True:
        try:
            # --- 1. SMART HIBERNATION (Midnight to 3:00 PM IST) ---
            now = datetime.now()
            if now.hour < 15:
                print(f"[{time.strftime('%X')}] ⏰ Morning Hibernation. Saving API calls... Sleeping for 1 hour.")
                time.sleep(3600)
                continue  
            
            # --- DEFAULT POLLING INTERVAL ---
            poll_interval = 300  
            
            live_data = fetch_cricbuzz_live_data() 
            
            if live_data and live_data.get('match_active'):
                weather_str = f"{live_data['weather']['temp']}°C, Humidity: {live_data['weather']['humidity']}%" if live_data.get('weather') else "Unknown"
                
                # --- MOMENTUM TRACKER & NEW INNINGS ALERT ---
                if current_innings_tracker != live_data['innings']:
                    match_history = [] 
                    current_innings_tracker = live_data['innings']
                    
                    # --- NEW: SEND AUTOMATED MESSAGE TO TELEGRAM ---
                    if live_data['innings'] == 1:
                        start_msg = (f"🏏 *LIVE MATCH TRACKING STARTED* 🏏\n\n"
                                     f"*{live_data['batting_team']}* vs *{live_data['bowling_team']}*\n"
                                     f"Innings 1 is underway! AI analytics and alerts are now active.")
                        send_telegram_alert(start_msg)
                    elif live_data['innings'] == 2:
                        chase_msg = (f"🎯 *THE CHASE IS ON!* 🎯\n\n"
                                     f"*{live_data['batting_team']}* needs {live_data['target']} runs to beat {live_data['bowling_team']}.\n"
                                     f"AI Win Probability Engine is locked in!")
                        send_telegram_alert(chase_msg)
                
                # (Keep the rest of your match_history.append code exactly the same below this...)
                match_history.append({
                    'score': live_data['cur_score'],
                    'wickets': live_data['wickets']
                })
                
                if len(match_history) > 4:
                    match_history.pop(0)
                
                runs_last_18 = 0
                wickets_last_18 = 0
                if len(match_history) > 1:
                    oldest = match_history[0]
                    runs_last_18 = max(0, live_data['cur_score'] - oldest['score'])
                    wickets_last_18 = max(0, live_data['wickets'] - oldest['wickets'])
                
                live_data['runs_last_18'] = runs_last_18
                live_data['wickets_last_18'] = wickets_last_18

                if live_data['innings'] == 2:
                    win_prob, phase = predict_win_prob(live_data)
                    
                    if wickets_last_18 >= 2:
                        win_prob = max(win_prob - 0.05, 0.01) 
                    elif runs_last_18 >= 32:
                        win_prob = min(win_prob + 0.05, 0.99) 
                        
                    live_data['chasing_win_prob'] = float(win_prob)
                    live_data['current_phase'] = phase
                    
                    if last_win_prob is not None:
                        swing = win_prob - last_win_prob
                        if abs(swing) >= 0.15:
                            direction = "📈 SURGED" if swing > 0 else "📉 CRASHED"
                            alert_msg = (
                                f"🚨 *GAME CHANGER ALERT!* 🚨\n\n"
                                f"Win probability for {live_data['batting_team']} just *{direction}* by {abs(swing)*100:.1f}%!\n\n"
                                f"🔥 *Momentum (Last 3 Ov):* {runs_last_18} runs, {wickets_last_18} wkts\n"
                                f"📊 *Score:* {live_data['cur_score']}/{live_data['wickets']} ({live_data['overs']} Ov)\n"
                                f"🔮 *New Win Prob:* {win_prob*100:.1f}%\n"
                            )
                            send_telegram_alert(alert_msg)
                            
                    last_win_prob = win_prob 
                    print(f"[{time.strftime('%X')}] 🟢 INNINGS 2 | Momentum: {runs_last_18}R/{wickets_last_18}W | Win Prob: {win_prob*100:.1f}%")
                else:
                    last_win_prob = None 
                    print(f"[{time.strftime('%X')}] 🟡 INNINGS 1 | Momentum: {runs_last_18}R/{wickets_last_18}W | Projected: {live_data['projected_score']}")
                    
                # --- TRIGGER GEMINI COMMENTARY ---
                print(f"[{time.strftime('%X')}] 🤖 Generating AI Commentary...")
                live_data['ai_commentary'] = generate_ai_commentary(live_data)
                
                # --- 2. ADAPTIVE POLLING (Speed up during Death Overs) ---
                if live_data.get('overs', 0) >= 16:
                    poll_interval = 120  
                else:
                    poll_interval = 300  

            else:
                last_win_prob = None 
                match_history = []
                
                # --- 3. SLOW POLLING WHEN NO MATCH IS ACTIVE ---
                poll_interval = 600  
                
                if live_data and 'todays_matches' in live_data:
                    for match in live_data['todays_matches']:
                        if match.get('state') == 'Complete':
                            # Assuming you have a log_completed_match function defined earlier
                            try:
                                log_completed_match(match)
                            except:
                                pass
                            
                print(f"[{time.strftime('%X')}] ⏸️ No active live match. Scanning for completed matches...")

            # =========================================================
            # ☁️ FIREBASE CLOUD SYNC (RUNS EVERY TIME)
            # =========================================================
            # +++ UPDATED FORCED TEST WITH SCHEDULE +++
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
                            'status': 'Match starts at 07:30 PM'
                        }
                    ]
                }

            if live_data:
                live_data['timestamp'] = time.strftime('%I:%M:%S %p')
                FIREBASE_URL = "https://ipl-intel-db-default-rtdb.firebaseio.com/live_match_state.json"
                
                try:
                    # Notice we are pushing 'live_data' here now!
                    cloud_response = requests.put(FIREBASE_URL, json=live_data)
                    if cloud_response.status_code == 200:
                        print(f"[{time.strftime('%H:%M:%S')}] ☁️ Successfully pushed live data to Firebase!")
                    else:
                        print(f"[{time.strftime('%H:%M:%S')}] ⚠️ Firebase Error: {cloud_response.text}")
                except Exception as e:
                    print(f"[{time.strftime('%H:%M:%S')}] ⚠️ Could not connect to Firebase: {e}")

            print(f"💤 Sleeping for {poll_interval // 60} minutes to conserve API quota.")
            time.sleep(poll_interval) 
            
        except Exception as e:
            print(f"⚠️ Error in worker loop: {e}")
            time.sleep(300) 

if __name__ == "__main__":
    run_worker()