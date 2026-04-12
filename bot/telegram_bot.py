import telebot
import os
import pandas as pd
import joblib
import json
from dotenv import load_dotenv

print("Starting IPL Intelligence Bot...")

# 1. Load Environment Variables (Assuming .env is in the root folder)
load_dotenv('../.env')
TOKEN = os.getenv('TELEGRAM_TOKEN')

if not TOKEN:
    print("❌ Error: TELEGRAM_TOKEN not found. Check your .env file.")
    exit()

bot = telebot.TeleBot(TOKEN)

# 2. Load ML Assets (Using relative paths since we are inside the 'bot' folder)
try:
    preprocessor = joblib.load('../models/preprocessor.pkl')
    model = joblib.load('../models/weighted_ensemble.pkl')
    form_df = pd.read_csv('../data/processed/team_form.csv')
    dom_df = pd.read_csv('../data/processed/dominance_matrix.csv')
    venue_df = pd.read_csv('../data/processed/venue_intelligence.csv')
    print("✅ Pre-Match Models and Data loaded successfully.")
except Exception as e:
    print(f"❌ Error loading models/data: {e}")
    print("Make sure you are running this script from inside the 'bot' folder.")
    exit()

# 3. Handle the /start command
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🏏 *Welcome to the IPL Intelligence Bot!*\n\n"
        "I am connected directly to your AI models.\n\n"
        "⚡ *Commands:*\n"
        "👉 `/live` - Instantly get the AI prediction for the current live run-chase.\n"
        "👉 `/predict Team1 vs Team2 at Venue` - Run a pre-match simulation."
    )
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

# 4. Handle the /live command (Now with Weather Engine)
@bot.message_handler(commands=['live'])
def live_match_update(message):
    try:
        with open('../data/processed/live_match_state.json', 'r') as f:
            live_data = json.load(f)
            
        if live_data and live_data.get('match_active'):
            batting = live_data['batting_team']
            bowling = live_data['bowling_team']
            score = f"{live_data['cur_score']}/{live_data['wickets']}"
            overs = live_data['overs']
            crr = live_data['crr']
            
            # Extract Weather Context
            weather = live_data.get('weather')
            city = live_data.get('city', 'Stadium')
            weather_block = ""
            if weather:
                dew_alert = "🚨 DEW WARNING (Advantage Chase)" if weather.get('dew_warning') else "🟢 Clear"
                weather_block = f"📍 _{city}_ | 🌡️ {weather['temp']}°C | 💧 {weather['humidity']}%\n🏏 Dew Factor: {dew_alert}\n\n"
            
            # --- IF IT IS THE 1ST INNINGS ---
            if live_data.get('innings') == 1:
                proj = live_data.get('projected_score', 'Calculating...')
                reply = (
                    f"🟡 *LIVE 1ST INNINGS UPDATE*\n"
                    f"{weather_block}"
                    f"🏏 *{batting}* vs *{bowling}*\n"
                    f"📊 Score: {score} ({overs} Overs)\n"
                    f"📈 Current Run Rate: {crr:.2f}\n"
                    f"🎯 Projected Target: ~{proj} runs\n\n"
                    f"_(AI Win Probability Engine activates during the 2nd Innings run-chase!)_"
                )
                bot.reply_to(message, reply, parse_mode='Markdown')
                
            # --- IF IT IS THE 2ND INNINGS (CHASE) ---
            elif live_data.get('innings') == 2:
                target = live_data['target']
                req_runs = live_data['runs_required']
                balls_left = live_data['balls_left']
                prob = live_data.get('chasing_win_prob', 0) * 100
                phase = live_data['current_phase']

                reply = (
                    f"🔴 *LIVE RUN-CHASE UPDATE*\n"
                    f"{weather_block}"
                    f"🏏 *{batting}* vs *{bowling}*\n"
                    f"🎯 Target: {target}\n"
                    f"📊 Score: {score} ({overs} Overs)\n"
                    f"⚡ Runs Needed: {req_runs} off {balls_left} balls\n\n"
                    f"🧠 *AI Phase Active*: {phase}\n"
                    f"🔮 *{batting} Win Probability*: {prob:.1f}%\n"
                )
                bot.reply_to(message, reply, parse_mode='Markdown')
        else:
            bot.reply_to(message, "⚠️ No active IPL matches found in the live data right now.")
            
    except FileNotFoundError:
        bot.reply_to(message, "⚠️ Live data file not found. Make sure your `live_api_worker.py` is running in the background!")
    except Exception as e:
        bot.reply_to(message, f"❌ Error reading live data: {e}")

# 5. Handle the /predict command
@bot.message_handler(commands=['predict'])
def predict_match(message):
    try:
        # Parse the user's text message
        text = message.text.replace('/predict ', '')
        teams_part, venue = text.split(' at ')
        team1, team2 = teams_part.split(' vs ')
        
        team1 = team1.strip()
        team2 = team2.strip()
        venue = venue.strip()
        
        bot.reply_to(message, f"⏳ Analyzing historic data and running ML ensemble for {team1} vs {team2}...")

        # Feature Lookup Logic (Mirroring your Streamlit app)
        t1_form = form_df[form_df['team'] == team1]['rolling_5_form'].iloc[-1]
        t2_form = form_df[form_df['team'] == team2]['rolling_5_form'].iloc[-1]
        
        matchup_str = ' vs '.join(sorted([team1, team2]))
        dom_val = dom_df[(dom_df['matchup'] == matchup_str) & (dom_df['winner'] == team1)]['dominance_score']
        dom_val = dom_val.iloc[0] if not dom_val.empty else 0.5
        
        v_dna = venue_df[venue_df['venue'] == venue]['bat_first_win_pct'].iloc[0] if venue in venue_df['venue'].values else 50.0

        home_stadiums = {'Chennai Super Kings': 'MA Chidambaram Stadium', 'Mumbai Indians': 'Wankhede Stadium', 
                         'Royal Challengers Bengaluru': 'M Chinnaswamy Stadium', 'Kolkata Knight Riders': 'Eden Gardens',
                         'Delhi Capitals': 'Arun Jaitley Stadium', 'Rajasthan Royals': 'Sawai Mansingh Stadium',
                         'Punjab Kings': 'Punjab Cricket Association Stadium, Mohali', 'Sunrisers Hyderabad': 'Rajiv Gandhi International Stadium',
                         'Gujarat Titans': 'Narendra Modi Stadium', 'Lucknow Super Giants': 'Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium'}
                         
        t1_home = 1 if (home_stadiums.get(team1) and home_stadiums.get(team1) in venue) else 0
        t2_home = 1 if (home_stadiums.get(team2) and home_stadiums.get(team2) in venue) else 0

        # Create prediction dataframe
        input_data = pd.DataFrame({
            'team1': [team1], 'team2': [team2], 'venue': [venue], 
            'toss_decision': ['field'], # Default assumption for quick bot reply
            'venue_bat_first_win_pct': [v_dna],
            'team1_home': [t1_home], 'team2_home': [t2_home], 'team1_won_toss': [1],
            'form_diff': [t1_form - t2_form], 'team1_dominance': [dom_val]
        })

        input_transformed = preprocessor.transform(input_data)
        probs = model.predict_proba(input_transformed)[0]

        # Format and send the response
        response = (
            f"🏟️ **AI Match Prediction** 🏟️\n"
            f"📍 _{venue}_\n\n"
            f"🔹 **{team1}**: {probs[1]*100:.1f}%\n"
            f"🔸 **{team2}**: {probs[0]*100:.1f}%\n\n"
            f"*(Assuming {team1} wins toss and fields first)*"
        )
        bot.reply_to(message, response, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, "⚠️ Formatting error. Please make sure you use the exact format:\n`/predict Team1 vs Team2 at Stadium`", parse_mode='Markdown')
        print(f"Prediction Error: {e}")

print("🤖 Bot is currently online and listening for messages...")
bot.infinity_polling()