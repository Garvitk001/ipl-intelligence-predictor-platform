import telebot
import os
import pandas as pd
import joblib
import json
from dotenv import load_dotenv

print("Starting IPL Intelligence Bot...")

# ==========================================
# 1. BULLETPROOF PATHS & ENV
# ==========================================
# This ensures the bot runs perfectly no matter what folder your terminal is in!
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

TOKEN = os.getenv('TELEGRAM_TOKEN')

if not TOKEN:
    print("❌ Error: TELEGRAM_TOKEN not found. Check your .env file.")
    exit()

bot = telebot.TeleBot(TOKEN)

# ==========================================
# 2. LOAD ML ASSETS
# ==========================================
try:
    preprocessor = joblib.load(os.path.join(BASE_DIR, 'models', 'preprocessor.pkl'))
    model = joblib.load(os.path.join(BASE_DIR, 'models', 'weighted_ensemble.pkl'))
    form_df = pd.read_csv(os.path.join(BASE_DIR, 'data', 'processed', 'team_form.csv'))
    dom_df = pd.read_csv(os.path.join(BASE_DIR, 'data', 'processed', 'dominance_matrix.csv'))
    venue_df = pd.read_csv(os.path.join(BASE_DIR, 'data', 'processed', 'venue_intelligence.csv'))
    print("✅ Pre-Match Models and Data loaded successfully.")
except Exception as e:
    print(f"❌ Error loading models/data: {e}")
    exit()

# ==========================================
# 3. COMMAND: /start
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🏏 *Welcome to the IPL Intelligence Bot!*\n\n"
        "I am connected directly to your AI models.\n\n"
        "⚡ *Commands:*\n"
        "👉 `/live` - Instantly get the AI prediction for the current live match.\n"
        "👉 `/predict Team1 vs Team2 at Venue` - Run a pre-match simulation."
    )
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

# ==========================================
# 4. COMMAND: /live (Upgraded with Crease & AI)
# ==========================================
@bot.message_handler(commands=['live'])
def live_match_update(message):
    try:
        # 🎯 FIX: Using the Absolute BASE_DIR ensures we see the SAME file the worker is writing!
        live_file = os.path.join(BASE_DIR, 'data', 'processed', 'live_match_state.json')
        
        if not os.path.exists(live_file):
            bot.reply_to(message, "⚠️ System Error: Live state file not found on server.")
            return

        with open(live_file, 'r') as f:
            live_data = json.load(f)
            
        if live_data and live_data.get('match_active'):
            batting = live_data['batting_team']
            bowling = live_data['bowling_team']
            score = f"{live_data['cur_score']}/{live_data['wickets']}"
            overs = live_data['overs']
            crr = live_data['crr']
            
            # --- WEATHER ---
            weather = live_data.get('weather')
            city = live_data.get('city', 'Stadium')
            weather_block = ""
            if weather:
                dew_alert = "🚨 DEW WARNING (Advantage Chase)" if weather.get('dew_warning') else "🟢 Clear"
                weather_block = f"📍 _{city}_ | 🌡️ {weather['temp']}°C | 💧 {weather['humidity']}%\n🏏 Dew Factor: {dew_alert}\n\n"
            
            # --- SMART CREASE & AI COMMENTARY ---
            striker = live_data.get('striker', 'Unknown')
            bowler = live_data.get('current_bowler', 'Unknown')
            crease_block = ""
            if striker != 'Unknown' and bowler != 'Unknown':
                crease_block = f"\n⚔️ *At The Crease:*\n🏏 {striker}\n⚾ {bowler}\n"
                
            ai_comm = live_data.get('ai_commentary', '')
            if ai_comm:
                short_comm = ai_comm[:200] + "..." if len(ai_comm) > 200 else ai_comm
                crease_block += f"\n🤖 *AI Desk:* {short_comm}"

            # --- IF 1ST INNINGS ---
            if live_data.get('innings') == 1:
                proj = live_data.get('projected_score', 'Calculating...')
                reply = (
                    f"🟡 *LIVE 1ST INNINGS UPDATE*\n"
                    f"{weather_block}"
                    f"🏏 *{batting}* vs *{bowling}*\n"
                    f"📊 Score: {score} ({overs} Overs)\n"
                    f"📈 Current Run Rate: {crr:.2f}\n"
                    f"🎯 Projected Target: ~{proj} runs\n"
                    f"{crease_block}\n"
                    f"_(AI Win Probability Engine activates during the run-chase!)_"
                )
                bot.reply_to(message, reply, parse_mode='Markdown')
                
            # --- IF 2ND INNINGS ---
            elif live_data.get('innings') == 2:
                target = live_data['target']
                req_runs = live_data['runs_required']
                balls_left = live_data['balls_left']
                prob = live_data.get('chasing_win_prob', 0) * 100
                phase = live_data.get('current_phase', 'Calculating...')

                reply = (
                    f"🔴 *LIVE RUN-CHASE UPDATE*\n"
                    f"{weather_block}"
                    f"🏏 *{batting}* vs *{bowling}*\n"
                    f"🎯 Target: {target}\n"
                    f"📊 Score: {score} ({overs} Overs)\n"
                    f"⚡ Runs Needed: {req_runs} off {balls_left} balls\n"
                    f"🧠 *AI Phase Active*: {phase}\n"
                    f"🔮 *{batting} Win Probability*: {prob:.1f}%\n"
                    f"{crease_block}"
                )
                bot.reply_to(message, reply, parse_mode='Markdown')
        else:
            bot.reply_to(message, "⚠️ No active IPL matches found in the live data right now.")
            
    except FileNotFoundError:
        bot.reply_to(message, "⚠️ Live data file not found. Make sure your `live_api_worker.py` is running in the background!")
    except Exception as e:
        bot.reply_to(message, f"❌ Error reading live data: {e}")

# ==========================================
# 5. COMMAND: /predict (Upgraded with Fuzzy Matching)
# ==========================================
@bot.message_handler(commands=['predict'])
def predict_match(message):
    try:
        text = message.text.replace('/predict ', '')
        teams_part, venue = text.split(' at ')
        team1, team2 = teams_part.split(' vs ')
        
        team1 = team1.strip()
        team2 = team2.strip()
        v_name = venue.strip()
        
        bot.reply_to(message, f"⏳ Analyzing historic data and running ML ensemble for {team1} vs {team2}...")

        # 1. Fallback mapping
        team_mapping = {
            'Delhi Daredevils': 'Delhi Capitals', 'Kings XI Punjab': 'Punjab Kings', 
            'Deccan Chargers': 'Sunrisers Hyderabad', 'Rising Pune Supergiants': 'Rising Pune Supergiant',
            'RCB': 'Royal Challengers Bengaluru', 'CSK': 'Chennai Super Kings', 'MI': 'Mumbai Indians'
        }
        t1_mapped = team_mapping.get(team1, team1)
        t2_mapped = team_mapping.get(team2, team2)

        # 2. Form Lookup
        t1_form_series = form_df[form_df['team'] == t1_mapped]['rolling_5_form']
        t1_form = t1_form_series.iloc[-1] if not t1_form_series.empty else 0.5
        t2_form_series = form_df[form_df['team'] == t2_mapped]['rolling_5_form']
        t2_form = t2_form_series.iloc[-1] if not t2_form_series.empty else 0.5
        
        # 3. Dominance Lookup
        matchup_str = ' vs '.join(sorted([t1_mapped, t2_mapped]))
        dom_val = dom_df[(dom_df['matchup'] == matchup_str) & (dom_df['winner'] == t1_mapped)]['dominance_score']
        dom_val = dom_val.iloc[0] if not dom_val.empty else 0.5

        # 4. Fuzzy Venue Matching (So users don't have to type perfect stadium names)
        v_dna = 50.0 
        mapped_venue = venue_df['venue'].iloc[0] 
        for known_venue in venue_df['venue'].values:
            if str(known_venue).split(' ')[0].lower() in v_name.lower(): 
                v_dna = venue_df[venue_df['venue'] == known_venue]['bat_first_win_pct'].iloc[0]
                mapped_venue = known_venue
                break

        home_stadiums = {'Chennai Super Kings': 'MA Chidambaram Stadium', 'Mumbai Indians': 'Wankhede Stadium', 
                         'Royal Challengers Bengaluru': 'M Chinnaswamy Stadium', 'Kolkata Knight Riders': 'Eden Gardens',
                         'Delhi Capitals': 'Arun Jaitley Stadium', 'Rajasthan Royals': 'Sawai Mansingh Stadium',
                         'Punjab Kings': 'Punjab Cricket Association Stadium, Mohali', 'Sunrisers Hyderabad': 'Rajiv Gandhi International Stadium',
                         'Gujarat Titans': 'Narendra Modi Stadium', 'Lucknow Super Giants': 'Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium'}
                         
        t1_home = 1 if (home_stadiums.get(t1_mapped) and home_stadiums.get(t1_mapped) in mapped_venue) else 0
        t2_home = 1 if (home_stadiums.get(t2_mapped) and home_stadiums.get(t2_mapped) in mapped_venue) else 0

        # Create prediction dataframe
        input_data = pd.DataFrame({
            'team1': [t1_mapped], 'team2': [t2_mapped], 'venue': [mapped_venue], 
            'toss_decision': ['field'],
            'venue_bat_first_win_pct': [v_dna],
            'team1_home': [t1_home], 'team2_home': [t2_home], 'team1_won_toss': [1],
            'form_diff': [t1_form - t2_form], 'team1_dominance': [dom_val]
        })

        input_transformed = preprocessor.transform(input_data)
        probs = model.predict_proba(input_transformed)[0]

        # Format and send the response
        response = (
            f"🏟️ *AI Match Prediction* 🏟️\n"
            f"📍 _{mapped_venue}_\n\n"
            f"🔹 *{t1_mapped}*: {probs[1]*100:.1f}%\n"
            f"🔸 *{t2_mapped}*: {probs[0]*100:.1f}%\n\n"
            f"*(Assuming {t1_mapped} wins toss and fields first)*"
        )
        bot.reply_to(message, response, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, "⚠️ Formatting error. Please make sure you use the exact format:\n`/predict Team1 vs Team2 at Stadium`", parse_mode='Markdown')
        print(f"Prediction Error: {e}")

print("🤖 Bot is currently online and listening for messages...")
bot.infinity_polling()