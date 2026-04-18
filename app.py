import streamlit as st
import pandas as pd
import numpy as np
import joblib
import plotly.express as px
import plotly.graph_objects as go
import os
import json
import requests
import time
from streamlit_autorefresh import st_autorefresh

# --- PAGE CONFIG & THEME ---
st.set_page_config(page_title="IPL Intelligence Platform", layout="wide", page_icon="🏏")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b22; border: 1px solid #30363d; border-radius: 5px 5px 0px 0px; padding: 10px 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 1. LOAD MODELS & DATA ---
@st.cache_resource
def load_ml_assets():
    try:
        preprocessor = joblib.load('models/preprocessor.pkl')
        model = joblib.load('models/weighted_ensemble.pkl')
        shap_explainer = joblib.load('models/shap_shadow_explainer.pkl')
        live_pp = joblib.load('models/live_chase_powerplay.pkl')
        live_mid = joblib.load('models/live_chase_middle.pkl')
        live_death = joblib.load('models/live_chase_death.pkl')
        return preprocessor, model, shap_explainer, live_pp, live_mid, live_death
    except FileNotFoundError:
        st.error("Model files not found! Please ensure Phase 4 training is complete.")
        return None, None, None, None, None, None

@st.cache_data
def load_processed_data():
    form_df = pd.read_csv('data/processed/team_form.csv')
    dom_df = pd.read_csv('data/processed/dominance_matrix.csv')
    venue_df = pd.read_csv('data/processed/venue_intelligence.csv')
    return form_df, dom_df, venue_df

@st.cache_data
def load_deliveries_data():
    deliveries = pd.read_csv('data/raw/deliveries.csv')
    matches = pd.read_csv('data/raw/matches.csv')
    return deliveries, matches

# Initialize assets
preprocessor, model, shap_explainer, live_pp, live_mid, live_death = load_ml_assets()
form_df, dom_df, venue_df = load_processed_data()
deliveries_df, matches_df = load_deliveries_data()

home_stadiums = {
    'Chennai Super Kings': 'MA Chidambaram Stadium', 'Mumbai Indians': 'Wankhede Stadium', 
    'Royal Challengers Bengaluru': 'M Chinnaswamy Stadium', 'Kolkata Knight Riders': 'Eden Gardens',
    'Delhi Capitals': 'Arun Jaitley Stadium', 'Rajasthan Royals': 'Sawai Mansingh Stadium',
    'Punjab Kings': 'Punjab Cricket Association Stadium, Mohali', 'Sunrisers Hyderabad': 'Rajiv Gandhi International Stadium',
    'Gujarat Titans': 'Narendra Modi Stadium', 'Lucknow Super Giants': 'Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium'
}

# --- 2. FIREBASE CLOUD DATABASE CONNECTOR ---
FIREBASE_URL = "https://ipl-intel-db-default-rtdb.firebaseio.com/live_match_state.json"

def fetch_firebase_live_data():
    try:
        response = requests.get(FIREBASE_URL)
        if response.status_code == 200:
            data = response.json()
            return data if data else {'match_active': False, 'timestamp': 'Database is empty'}
        else:
            return {'match_active': False, 'timestamp': f'Firebase Error: {response.status_code}'}
    except Exception as e:
        return {'match_active': False, 'timestamp': f'Cloud Connection Error: {str(e)}'}

# --- GLOBAL SYNC ENGINE ---
initial_cloud_state = fetch_firebase_live_data()
global_is_live = initial_cloud_state.get('match_active', False)
global_t1 = initial_cloud_state.get('batting_team')
global_t2 = initial_cloud_state.get('bowling_team')
global_striker = initial_cloud_state.get('striker', 'Unknown')      
global_current_bowler = initial_cloud_state.get('current_bowler', 'Unknown') 

# ADVANCED SYNC: If no match is live, sync to the UPCOMING match today!
if not global_is_live and initial_cloud_state.get('todays_matches'):
    try:
        upcoming_match = initial_cloud_state['todays_matches'][0]
        global_t1 = upcoming_match.get('team1')
        global_t2 = upcoming_match.get('team2')
        st.info(f"📅 **UPCOMING MATCH:** Auto-synced all tabs to {global_t1} vs {global_t2} for Pre-Match Analysis.")
    except:
        pass
elif global_is_live:
    st.success(f"🔴 **LIVE MATCH DETECTED:** {global_t1} vs {global_t2} — All tabs auto-synced!")

def get_team_index(team_name, team_list, default_idx=0):
    if team_name in team_list:
        return team_list.index(team_name)
    return default_idx

team_choices = sorted(form_df['team'].unique())
default_t1_idx = get_team_index(global_t1, team_choices, 0)
default_t2_idx = get_team_index(global_t2, team_choices, 1)

# --- TAB 1: PRE-MATCH ENGINE ---
def render_pre_match():
    st.title("🏟️ Pre-Match Intelligence")
    st.markdown("### Ensemble Win Probability Engine")
    
    with st.container():
        c1, c2 = st.columns(2)
        with c1:
            team1 = st.selectbox("Team 1 (Home/Neutral)", team_choices, index=default_t1_idx)
            venue = st.selectbox("Match Venue", sorted(venue_df['venue'].unique()))
        with c2:
            team2 = st.selectbox("Team 2 (Away/Neutral)", team_choices, index=default_t2_idx)
            toss_dec = st.selectbox("Toss Decision", ["field", "bat"])

    # --- TOSS OPTIMIZER ENGINE ---
    st.divider()
    st.markdown("### 🪙 AI Toss Optimizer")
    st.info("💡 *Analyzing Pitch DNA: Let the AI mathematically determine if the captain should elect to Bat or Bowl first based on historical venue data.*")
    
    if st.button("Analyze Pitch DNA for this Venue", use_container_width=True):
        st.session_state.toss_clicked = True
        
    if st.session_state.get('toss_clicked', False):
        with st.spinner("Analyzing historical venue bias..."):
            venue_matches = matches_df[matches_df['venue'] == venue]
            
            if len(venue_matches) < 5:
                st.warning(f"Not enough historical data for {venue} to make a confident toss prediction.")
            else:
                valid_matches = venue_matches.dropna(subset=['winner']).copy()
                total_matches = len(valid_matches)
                
                if total_matches == 0:
                    st.warning("No valid match results found for this venue.")
                else:
                    bat_first_wins = len(valid_matches[
                        ((valid_matches['toss_winner'] == valid_matches['winner']) & (valid_matches['toss_decision'] == 'bat')) |
                        ((valid_matches['toss_winner'] != valid_matches['winner']) & (valid_matches['toss_decision'] == 'field'))
                    ])
                    
                    chase_wins = total_matches - bat_first_wins
                    bat_first_pct = (bat_first_wins / total_matches) * 100
                    chase_pct = (chase_wins / total_matches) * 100
                    
                    c1_toss, c2_toss = st.columns(2)
                    c1_toss.metric("Win % (Batting First)", f"{bat_first_pct:.1f}%")
                    c2_toss.metric("Win % (Chasing)", f"{chase_pct:.1f}%")
                    
                    if chase_pct > bat_first_pct + 5:
                        st.success(f"🔥 **AI RECOMMENDATION: FIELD FIRST**\n\nHistorically, {venue} heavily favors the chasing team ({chase_pct:.1f}% win rate). If the captain wins the toss, they must elect to bowl. Dew likely makes it easier to bat in the 2nd innings.")
                    elif bat_first_pct > chase_pct + 5:
                        st.success(f"🛡️ **AI RECOMMENDATION: BAT FIRST**\n\nHistorically, {venue} heavily favors the team setting the target ({bat_first_pct:.1f}% win rate). The captain should elect to bat. The pitch likely deteriorates, bringing spinners into the game later.")
                    else:
                        st.warning(f"⚖️ **NEUTRAL PITCH**\n\n{venue} is a highly balanced ground. The toss decision should be based on team strengths rather than pitch bias.")
    st.divider()

    if st.button("🚀 Run Pre-Match Prediction", use_container_width=True):
        st.session_state.prematch_clicked = True
        
    if st.session_state.get('prematch_clicked', False):
        if team1 == team2:
            st.warning("Please select two different teams.")
            return

        t1_form = form_df[form_df['team'] == team1]['rolling_5_form'].iloc[-1]
        t2_form = form_df[form_df['team'] == team2]['rolling_5_form'].iloc[-1]
        
        matchup_str = ' vs '.join(sorted([team1, team2]))
        dom_val = dom_df[(dom_df['matchup'] == matchup_str) & (dom_df['winner'] == team1)]['dominance_score']
        dom_val = dom_val.iloc[0] if not dom_val.empty else 0.5
        v_dna = venue_df[venue_df['venue'] == venue]['bat_first_win_pct'].iloc[0] if venue in venue_df['venue'].values else 50.0

        t1_home = 1 if (home_stadiums.get(team1) and home_stadiums.get(team1) in venue) else 0
        t2_home = 1 if (home_stadiums.get(team2) and home_stadiums.get(team2) in venue) else 0

        input_data = pd.DataFrame({
            'team1': [team1], 'team2': [team2], 'venue': [venue], 
            'toss_decision': [toss_dec], 'venue_bat_first_win_pct': [v_dna],
            'team1_home': [t1_home], 'team2_home': [t2_home], 'team1_won_toss': [1],
            'form_diff': [t1_form - t2_form], 'team1_dominance': [dom_val]
        })

        input_transformed = preprocessor.transform(input_data)
        probs = model.predict_proba(input_transformed)[0]

        st.divider()
        res_col1, res_col2 = st.columns([1, 1])
        with res_col1:
            st.metric(f"{team1} Win %", f"{probs[1]*100:.1f}%")
            st.progress(probs[1])
            st.metric(f"{team2} Win %", f"{probs[0]*100:.1f}%")
            st.progress(probs[0])
        with res_col2:
            prob_fig = px.pie(values=[probs[1], probs[0]], names=[team1, team2], hole=0.4, color_discrete_sequence=['#2E86C1', '#E74C3C'])
            st.plotly_chart(prob_fig, use_container_width=True)

# --- TAB 2: LIVE MATCH ENGINE & DAILY HUB ---
def render_live_match():
    st.title("⚡ Autonomous Live Match Engine")
    
    auto_on = st.toggle("🔄 Enable Live Auto-Refresh", value=False, help="Turn this on to watch the live match update in real-time. Turn it OFF when using the Fantasy or Pre-Match tabs.")
    
    if auto_on:
        st_autorefresh(interval=15000, key="live_match_updater")
        
    live_data = fetch_firebase_live_data()
        
    # --- SMART DAILY MATCH HUB ---
    if not live_data.get('match_active'):
        st.info(f"⏸️ No live match at the moment. Last Synced: {live_data.get('timestamp', 'Unknown')}")
        if 'message' in live_data:
            st.warning(f"System Message: {live_data['message']}")
            
        st.markdown("### 📅 Today's IPL Match Hub")
        
        todays_matches = live_data.get('todays_matches', [])
        if not todays_matches:
            st.warning("No IPL matches scheduled for today.")
        else:
            cols = st.columns(len(todays_matches) if len(todays_matches) < 3 else 3)
            for idx, match in enumerate(todays_matches):
                with cols[idx % 3]:
                    t1_name = match.get('team1', 'TBA')
                    t2_name = match.get('team2', 'TBA')
                    v_name = match.get('venue', 'Unknown Venue')
                    
                    # --- AI PRE-MATCH CALCULATION ON THE FLY ---
                    win_prob_html = ""
                    try:
                        # 1. Fallback mapping in case API names don't match our database perfectly
                        team_mapping = {
                            'Delhi Daredevils': 'Delhi Capitals', 'Kings XI Punjab': 'Punjab Kings', 
                            'Deccan Chargers': 'Sunrisers Hyderabad', 'Rising Pune Supergiants': 'Rising Pune Supergiant',
                            'Royal Challengers Bangalore': 'Royal Challengers Bengaluru', 'Gujarat Lions': 'Gujarat Titans'
                        }
                        
                        t1_mapped = team_mapping.get(t1_name, t1_name)
                        t2_mapped = team_mapping.get(t2_name, t2_name)

                        # 2. Safely grab form (default to 0.5 if team is brand new/missing)
                        t1_form_series = form_df[form_df['team'] == t1_mapped]['rolling_5_form']
                        t1_form = t1_form_series.iloc[-1] if not t1_form_series.empty else 0.5
                        
                        t2_form_series = form_df[form_df['team'] == t2_mapped]['rolling_5_form']
                        t2_form = t2_form_series.iloc[-1] if not t2_form_series.empty else 0.5
                        
                        # 3. Safely grab dominance
                        matchup_str = ' vs '.join(sorted([t1_mapped, t2_mapped]))
                        dom_val = dom_df[(dom_df['matchup'] == matchup_str) & (dom_df['winner'] == t1_mapped)]['dominance_score']
                        dom_val = dom_val.iloc[0] if not dom_val.empty else 0.5
                        
                        # 4. Safely handle Venue mismatches 
                        v_dna = 50.0 
                        # NEW: Give it a safe default stadium just in case it completely fails to match!
                        mapped_venue = venue_df['venue'].iloc[0] 
                        for known_venue in venue_df['venue'].values:
                            if str(known_venue).split(' ')[0] in v_name: 
                                v_dna = venue_df[venue_df['venue'] == known_venue]['bat_first_win_pct'].iloc[0]
                                mapped_venue = known_venue # Save the clean name!
                                break

                        # 5. Check Home Advantage
                        t1_home = 1 if (home_stadiums.get(t1_mapped) and home_stadiums.get(t1_mapped) in v_name) else 0
                        t2_home = 1 if (home_stadiums.get(t2_mapped) and home_stadiums.get(t2_mapped) in v_name) else 0

                        # 6. Run the Prediction (FIXED: Pass 'mapped_venue' instead of 'v_name')
                        input_data = pd.DataFrame({
                            'team1': [t1_mapped], 'team2': [t2_mapped], 'venue': [mapped_venue], 
                            'toss_decision': ['field'], 'venue_bat_first_win_pct': [v_dna],
                            'team1_home': [t1_home], 'team2_home': [t2_home], 'team1_won_toss': [1],
                            'form_diff': [t1_form - t2_form], 'team1_dominance': [dom_val]
                        })

                        input_transformed = preprocessor.transform(input_data)
                        probs = model.predict_proba(input_transformed)[0]
                        prob_t1 = probs[1] * 100
                        prob_t2 = probs[0] * 100

                        # 5. Check Home Advantage
                        t1_home = 1 if (home_stadiums.get(t1_mapped) and home_stadiums.get(t1_mapped) in v_name) else 0
                        t2_home = 1 if (home_stadiums.get(t2_mapped) and home_stadiums.get(t2_mapped) in v_name) else 0

                        # 6. Run the Prediction
                        input_data = pd.DataFrame({
                            'team1': [t1_mapped], 'team2': [t2_mapped], 'venue': [v_name], 
                            'toss_decision': ['field'], 'venue_bat_first_win_pct': [v_dna],
                            'team1_home': [t1_home], 'team2_home': [t2_home], 'team1_won_toss': [1],
                            'form_diff': [t1_form - t2_form], 'team1_dominance': [dom_val]
                        })

                        input_transformed = preprocessor.transform(input_data)
                        probs = model.predict_proba(input_transformed)[0]
                        prob_t1 = probs[1] * 100
                        prob_t2 = probs[0] * 100
                        
                        win_prob_html = f"""
                        <div style="background-color: #0e1117; padding: 10px; border-radius: 5px; margin-top: 10px;">
                            <p style="text-align: center; margin: 0; font-size: 12px; color: #aaaaaa;">AI Win Probability Forecast</p>
                            <div style="display: flex; justify-content: space-between; font-size: 14px; margin-top: 5px; font-weight: bold;">
                                <span style="color: #3498DB;">{prob_t1:.1f}%</span>
                                <span style="color: #E74C3C;">{prob_t2:.1f}%</span>
                            </div>
                            <div style="width: 100%; background-color: #E74C3C; height: 6px; border-radius: 3px; margin-top: 5px; overflow: hidden;">
                                <div style="width: {prob_t1}%; background-color: #3498DB; height: 100%;"></div>
                            </div>
                        </div>
                        """
                    except Exception as e:
                        # Now if it fails, it will print the error in your terminal so we know exactly why!
                        print(f"⚠️ Daily Hub ML Error for {t1_name} vs {t2_name}: {e}")
                        # --- AI PRE-MATCH CALCULATION ON THE FLY ---
                    win_prob_html = ""
                    try:
                        # 1. Fallback mapping in case API names don't match our database perfectly
                        team_mapping = {
                            'Delhi Daredevils': 'Delhi Capitals', 'Kings XI Punjab': 'Punjab Kings', 
                            'Deccan Chargers': 'Sunrisers Hyderabad', 'Rising Pune Supergiants': 'Rising Pune Supergiant',
                            'Royal Challengers Bangalore': 'Royal Challengers Bengaluru', 'Gujarat Lions': 'Gujarat Titans'
                        }
                        
                        t1_mapped = team_mapping.get(t1_name, t1_name)
                        t2_mapped = team_mapping.get(t2_name, t2_name)

                        # 2. Safely grab form (default to 0.5 if team is brand new/missing)
                        t1_form_series = form_df[form_df['team'] == t1_mapped]['rolling_5_form']
                        t1_form = t1_form_series.iloc[-1] if not t1_form_series.empty else 0.5
                        
                        t2_form_series = form_df[form_df['team'] == t2_mapped]['rolling_5_form']
                        t2_form = t2_form_series.iloc[-1] if not t2_form_series.empty else 0.5
                        
                        # 3. Safely grab dominance
                        matchup_str = ' vs '.join(sorted([t1_mapped, t2_mapped]))
                        dom_val = dom_df[(dom_df['matchup'] == matchup_str) & (dom_df['winner'] == t1_mapped)]['dominance_score']
                        dom_val = dom_val.iloc[0] if not dom_val.empty else 0.5
                        
                        # 4. Safely handle Venue mismatches 
                        v_dna = 50.0 
                        for known_venue in venue_df['venue'].values:
                            if str(known_venue).split(' ')[0] in v_name: 
                                v_dna = venue_df[venue_df['venue'] == known_venue]['bat_first_win_pct'].iloc[0]
                                break

                        # 5. Check Home Advantage
                        t1_home = 1 if (home_stadiums.get(t1_mapped) and home_stadiums.get(t1_mapped) in v_name) else 0
                        t2_home = 1 if (home_stadiums.get(t2_mapped) and home_stadiums.get(t2_mapped) in v_name) else 0

                        # 6. Run the Prediction
                        input_data = pd.DataFrame({
                            'team1': [t1_mapped], 'team2': [t2_mapped], 'venue': [v_name], 
                            'toss_decision': ['field'], 'venue_bat_first_win_pct': [v_dna],
                            'team1_home': [t1_home], 'team2_home': [t2_home], 'team1_won_toss': [1],
                            'form_diff': [t1_form - t2_form], 'team1_dominance': [dom_val]
                        })

                        input_transformed = preprocessor.transform(input_data)
                        probs = model.predict_proba(input_transformed)[0]
                        prob_t1 = probs[1] * 100
                        prob_t2 = probs[0] * 100
                        
                        # FIXED: Removed the indentations so Streamlit doesn't think it's a code block!
                        win_prob_html = f"""<div style="background-color: #0e1117; padding: 10px; border-radius: 5px; margin-top: 10px;">
<p style="text-align: center; margin: 0; font-size: 12px; color: #aaaaaa;">AI Win Probability Forecast</p>
<div style="display: flex; justify-content: space-between; font-size: 14px; margin-top: 5px; font-weight: bold;">
<span style="color: #3498DB;">{prob_t1:.1f}%</span>
<span style="color: #E74C3C;">{prob_t2:.1f}%</span>
</div>
<div style="width: 100%; background-color: #E74C3C; height: 6px; border-radius: 3px; margin-top: 5px; overflow: hidden;">
<div style="width: {prob_t1}%; background-color: #3498DB; height: 100%;"></div>
</div>
</div>"""
                    except Exception as e:
                        print(f"⚠️ Daily Hub ML Error for {t1_name} vs {t2_name}: {e}")
                        win_prob_html = f"<p style='text-align: center; color: #E74C3C; font-size: 12px; margin-top: 10px;'>⚠️ AI Forecast temporarily unavailable</p>"
                        
                    st.markdown(f"""
                    <div style="background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                        <h4 style="text-align: center; color: #3498DB; margin: 0;">{t1_name}</h4>
                        <h5 style="text-align: center; color: #ffffff; margin: 5px 0;">vs</h5>
                        <h4 style="text-align: center; color: #E74C3C; margin: 0;">{t2_name}</h4>
                        <hr style="border-color: #30363d; margin: 10px 0;">
                        <p style="text-align: center; margin: 0; font-size: 14px; color: #cccccc;">📍 {v_name}, {match.get('city', '')}</p>
                        <p style="text-align: center; margin: 5px 0 0 0; color: #F1C40F;"><strong>⏰ {match.get('status', 'Scheduled')}</strong></p>
                        {win_prob_html}
                    </div>
                    """, unsafe_allow_html=True)
        return
        
    # --- ACTIVE MATCH UI ---
    st.success(f"🔴 LIVE DATA SYNCED | Last Updated: {live_data.get('timestamp', 'Unknown')}")
    
    weather = live_data.get('weather')
    city = live_data.get('city', 'Unknown Location')
    if weather:
        dew_status = "🚨 HIGH (Advantage Chasing Team)" if weather.get('dew_warning') else "🟢 LOW"
        st.markdown(f"📍 **{city}** &nbsp;|&nbsp; 🌡️ **{weather['temp']}°C** &nbsp;|&nbsp; 💧 **Humidity: {weather['humidity']}%** &nbsp;|&nbsp; 🏏 **Dew Factor: {dew_status}**")
        if weather.get('dew_warning'):
            st.info("💡 *Dew Warning Active: The AI has artificially boosted the chasing team's win probability by 3% due to wet outfield conditions.*")
            
    if live_data.get('ai_commentary'):
        st.info(f"🎙️ **AI Commentary Desk:** \"{live_data['ai_commentary']}\"")
    st.divider()
    
    innings = live_data.get('innings', 2)
    
    if innings == 1:
        st.info("🟡 1st Innings in Progress | AI Win Probability Engine activates during the run-chase.")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Batting Team", live_data.get('batting_team', 'Unknown'))
            st.metric("Current Score", f"{live_data.get('cur_score', 0)} / {live_data.get('wickets', 0)}")
        with col2:
            st.metric("Bowling Team", live_data.get('bowling_team', 'Unknown'))
            st.metric("Projected Target", live_data.get('projected_score', 'Calculating...'))
        with col3:
            st.metric("Overs Completed", f"{live_data.get('overs', 0):.1f}")
            st.metric("Current Run Rate (CRR)", f"{live_data.get('crr', 0):.2f}")

    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Chasing Team", live_data.get('batting_team', 'Unknown'))
            st.metric("Current Score", f"{live_data.get('cur_score', 0)} / {live_data.get('wickets', 0)}")
        with col2:
            st.metric("Defending Team", live_data.get('bowling_team', 'Unknown'))
            st.metric("Target Score", live_data.get('target', 0))
        with col3:
            st.metric("Overs Completed", f"{live_data.get('overs', 0):.1f}")
            st.metric("Phase Active", live_data.get('current_phase', 'In Progress'))
            
        st.divider()
        metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
        metric_col1.metric("Runs Required", live_data.get('runs_required', 0))
        metric_col2.metric("Balls Left", live_data.get('balls_left', 0))
        metric_col3.metric("CRR", f"{live_data.get('crr', 0):.2f}")
        metric_col4.metric("RRR", f"{live_data.get('rrr', 0):.2f}")
        
        r_18 = live_data.get('runs_last_18', 0)
        w_18 = live_data.get('wickets_last_18', 0)
        metric_col5.metric("Momentum (Last 3 Ov)", f"{r_18} R / {w_18} W")
        
        if w_18 >= 2:
            st.error("📉 Collapse Detected: The AI has penalized the chasing team due to recent quick wickets.")
        elif r_18 >= 32:
            st.success("🔥 Surge Detected: The AI has boosted the chasing team due to high recent scoring.")
        
        chasing_win_prob = live_data.get('chasing_win_prob', 0)
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = chasing_win_prob * 100,
            title = {'text': f"{live_data.get('batting_team', 'Chasing Team')} Win Probability"},
            gauge = {
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "white"},
                'bar': {'color': "#2E86C1"},
                'bgcolor': "rgba(0,0,0,0)",
                'borderwidth': 2,
                'bordercolor': "#30363d",
                'steps': [{'range': [0, 30], 'color': "#E74C3C"}, {'range': [30, 70], 'color': "#F1C40F"}, {'range': [70, 100], 'color': "#27AE60"}],
                'threshold': {'line': {'color': "white", 'width': 4}, 'thickness': 0.75, 'value': chasing_win_prob * 100}
            }
        ))
        fig.update_layout(height=400, font={'color': "white"}, paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

# --- TAB 3: PLAYER INTELLIGENCE & MATCHUPS ---
def render_player_intel():
    st.title("⚔️ Player Matchup Engine")
    st.markdown("### Head-to-Head Micro-Analytics")
    st.info("💡 *Analyze the ultimate micro-battles. Select a Batter and a Bowler to see their exact historical head-to-head statistics.*")
    
    batter_col = 'batter' if 'batter' in deliveries_df.columns else 'batsman'
    all_batters = sorted(deliveries_df[batter_col].dropna().unique())
    all_bowlers = sorted(deliveries_df['bowler'].dropna().unique())
    
    def find_player_index(live_name, player_list, default_name):
        if not live_name or live_name == "Unknown":
            return player_list.index(default_name) if default_name in player_list else 0
            
        live_parts = live_name.lower().split()
        for i, p in enumerate(player_list):
            p_lower = p.lower()
            if live_parts[-1] in p_lower or p_lower in live_name.lower():
                return i
        return player_list.index(default_name) if default_name in player_list else 0

    default_bat = find_player_index(global_striker, all_batters, 'V Kohli') if global_is_live else (all_batters.index('V Kohli') if 'V Kohli' in all_batters else 0)
    default_bowl = find_player_index(global_current_bowler, all_bowlers, 'JJ Bumrah') if global_is_live else (all_bowlers.index('JJ Bumrah') if 'JJ Bumrah' in all_bowlers else 0)
    
    col1, col2 = st.columns(2)
    with col1:
        if global_is_live and global_striker != "Unknown":
            st.caption(f"🔴 Live Sync: Auto-selected {global_striker}")
        selected_batter = st.selectbox("🏏 Select Batter", all_batters, index=default_bat)
    with col2:
        if global_is_live and global_current_bowler != "Unknown":
            st.caption(f"🔴 Live Sync: Auto-selected {global_current_bowler}")
        selected_bowler = st.selectbox("🎯 Select Bowler", all_bowlers, index=default_bowl)
        
    if st.button("Calculate Matchup", use_container_width=True):
        st.session_state.matchup_clicked = True
        
    if st.session_state.get('matchup_clicked', False):
        with st.spinner("Analyzing ball-by-ball history..."):
            matchup_df = deliveries_df[(deliveries_df[batter_col] == selected_batter) & 
                                       (deliveries_df['bowler'] == selected_bowler)]
                                       
            if matchup_df.empty:
                st.warning(f"No historical data found for {selected_batter} vs {selected_bowler}.")
                return
                
            runs_scored = int(matchup_df['batsman_runs'].sum())
            balls_faced = len(matchup_df)
            
            if 'dismissal_kind' in matchup_df.columns:
                dismissals = len(matchup_df[(matchup_df['player_dismissed'] == selected_batter) & 
                                            (~matchup_df['dismissal_kind'].isin(['run out', 'retired hurt', 'obstructing the field']))])
            elif 'is_wicket' in matchup_df.columns:
                dismissals = matchup_df['is_wicket'].sum()
            else:
                dismissals = matchup_df['player_dismissed'].notnull().sum()
                
            strike_rate = (runs_scored / balls_faced) * 100 if balls_faced > 0 else 0
            dots = len(matchup_df[matchup_df['batsman_runs'] == 0])
            fours = len(matchup_df[matchup_df['batsman_runs'] == 4])
            sixes = len(matchup_df[matchup_df['batsman_runs'] == 6])
            
            st.divider()
            st.markdown(f"<h3 style='text-align: center; color: #3498DB;'>{selected_batter} <span style='color: white;'>🆚</span> <span style='color: #E74C3C;'>{selected_bowler}</span></h3>", unsafe_allow_html=True)
            
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric("Runs Scored", runs_scored)
            m_col2.metric("Balls Faced", balls_faced)
            m_col3.metric("Strike Rate", f"{strike_rate:.1f}")
            m_col4.metric("Dismissals", dismissals)
            
            st.divider()
            st.markdown("#### Innings Breakdown")
            b_col1, b_col2, b_col3, b_col4 = st.columns(4)
            
            dot_pct = (dots/balls_faced)*100 if balls_faced > 0 else 0
            b_col1.metric("Dot Balls", dots, f"{dot_pct:.1f}% dot rate", delta_color="inverse")
            b_col2.metric("Boundaries (4s)", fours)
            b_col3.metric("Sixes (6s)", sixes)
            
            st.divider()
            if dismissals >= 3 and strike_rate < 130:
                st.error(f"🚨 **BOWLER DOMINANCE:** {selected_bowler} absolutely owns this matchup. Taking {dismissals} wickets while keeping the strike rate at {strike_rate:.1f} means the bowling captain should bring them on immediately when {selected_batter} comes to the crease.")
            elif strike_rate >= 150 and runs_scored >= 30 and dismissals <= 1:
                st.success(f"🔥 **BATTER DOMINANCE:** {selected_batter} bullies this bowler. Striking at {strike_rate:.1f} with minimal dismissals means the batting team should target {selected_bowler} heavily.")
            elif dismissals >= 2 and strike_rate >= 150:
                st.warning(f"⚔️ **HIGH VOLATILITY:** Absolute chaos. {selected_batter} scores very fast ({strike_rate:.1f} SR), but {selected_bowler} strikes back with {dismissals} wickets. High risk, high reward.")
            else:
                st.info("⚖️ **EVEN MATCHUP:** Neither player has established absolute dominance over the other historically.")

# --- TAB 4: TEAM INTELLIGENCE ---
def render_team_intel():
    st.title("🛡️ Team Intelligence")
    st.markdown("### Franchise Performance & Rivalry Analysis")
    
    team_query = st.selectbox("Select Franchise", team_choices, index=default_t1_idx)
    
    if team_query:
        team_mapping = {
            'Delhi Daredevils': 'Delhi Capitals', 'Kings XI Punjab': 'Punjab Kings', 
            'Deccan Chargers': 'Sunrisers Hyderabad', 'Rising Pune Supergiants': 'Rising Pune Supergiant',
            'Royal Challengers Bangalore': 'Royal Challengers Bengaluru', 'Gujarat Lions': 'Gujarat Titans'
        }
        working_matches = matches_df.copy()
        working_matches.replace(team_mapping, inplace=True)
        
        team_matches = working_matches[(working_matches['team1'] == team_query) | (working_matches['team2'] == team_query)]
        total_played = len(team_matches)
        total_wins = len(team_matches[team_matches['winner'] == team_query])
        win_pct = (total_wins / total_played) * 100 if total_played > 0 else 0
        
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Matches Played", total_played)
        c2.metric("Total Wins", total_wins)
        c3.metric("Franchise Win Percentage", f"{win_pct:.2f}%")
        
        col_charts1, col_charts2 = st.columns(2)
        with col_charts1:
            st.subheader("Toss Impact Analysis")
            toss_wins = team_matches[team_matches['toss_winner'] == team_query]
            if not toss_wins.empty:
                bat_wins = len(toss_wins[(toss_wins['toss_decision'] == 'bat') & (toss_wins['winner'] == team_query)])
                field_wins = len(toss_wins[(toss_wins['toss_decision'] == 'field') & (toss_wins['winner'] == team_query)])
                toss_df = pd.DataFrame({'Decision': ['Elected to Bat & Won', 'Elected to Field & Won'], 'Count': [bat_wins, field_wins]})
                fig_toss = px.pie(toss_df, values='Count', names='Decision', hole=0.4, color_discrete_sequence=['#F39C12', '#27AE60'])
                fig_toss.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color='white'))
                st.plotly_chart(fig_toss, use_container_width=True)
                
        with col_charts2:
            st.subheader(f"Dominance Over Rivals")
            rivalry_df = dom_df[dom_df['winner'] == team_query].copy()
            if not rivalry_df.empty:
                def get_opponent(matchup, current_team):
                    teams = matchup.split(' vs ')
                    return teams[0] if teams[1] == current_team else teams[1]
                rivalry_df['Opponent'] = rivalry_df.apply(lambda x: get_opponent(x['matchup'], team_query), axis=1)
                rivalry_df = rivalry_df.sort_values('dominance_score', ascending=True)
                fig_dom = px.bar(rivalry_df, x='dominance_score', y='Opponent', orientation='h',
                text=rivalry_df['dominance_score'].apply(lambda x: f"{x*100:.1f}%"),
                color='dominance_score', color_continuous_scale='Blues')
                fig_dom.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", font=dict(color='white'), xaxis_title="Historical Win Rate")
                st.plotly_chart(fig_dom, use_container_width=True)

# --- TAB 5: VENUE INTELLIGENCE ---
def render_venue_intel():
    st.title("🏟️ Venue Intelligence")
    st.markdown("### Pitch DNA & Historical Trends")
    venue_query = st.selectbox("Select Stadium", sorted(venue_df['venue'].dropna().unique()))
    
    if venue_query:
        v_matches = matches_df[matches_df['venue'] == venue_query]
        total_matches = len(v_matches)
        if total_matches == 0: return
            
        v_dna = venue_df[venue_df['venue'] == venue_query].iloc[0]
        bat_first_win = v_dna['bat_first_win_pct']
        chase_win = 100.0 - bat_first_win
        v_match_ids = v_matches['id'].unique()
        v_dels = deliveries_df[(deliveries_df['match_id'].isin(v_match_ids)) & (deliveries_df['inning'] == 1)]
        inning1_scores = v_dels.groupby('match_id')['total_runs'].sum()
        
        avg_1st_innings = inning1_scores.mean() if not inning1_scores.empty else 0
        high_score_count = len(inning1_scores[inning1_scores >= 180])
        high_score_prob = (high_score_count / len(inning1_scores)) * 100 if len(inning1_scores) > 0 else 0
        
        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Matches", total_matches)
        c2.metric("Avg 1st Innings Score", f"{int(avg_1st_innings)}")
        c3.metric("Bat First Win %", f"{bat_first_win:.1f}%")
        c4.metric("180+ Score Probability", f"{high_score_prob:.1f}%")
        
        col_charts1, col_charts2 = st.columns(2)
        with col_charts1:
            st.subheader("Captain's Toss Preference")
            bat_dec = len(v_matches[v_matches['toss_decision'] == 'bat'])
            field_dec = len(v_matches[v_matches['toss_decision'] == 'field'])
            toss_pref_df = pd.DataFrame({'Decision': ['Elected to Bat', 'Elected to Field'], 'Count': [bat_dec, field_dec]})
            fig_toss = px.pie(toss_pref_df, values='Count', names='Decision', hole=0.4, color_discrete_sequence=['#E67E22', '#3498DB'])
            fig_toss.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color='white'))
            st.plotly_chart(fig_toss, use_container_width=True)
            
        with col_charts2:
            st.subheader("Win Breakdown")
            win_df = pd.DataFrame({'Outcome': ['Batting First Won', 'Chasing Won'], 'Percentage': [bat_first_win, chase_win]})
            fig_win = px.bar(win_df, x='Outcome', y='Percentage', text=win_df['Percentage'].apply(lambda x: f"{x:.1f}%"), color='Outcome', color_discrete_sequence=['#9B59B6', '#2ECC71'])
            fig_win.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", font=dict(color='white'), yaxis_title="Historical Win %")
            st.plotly_chart(fig_win, use_container_width=True)


# --- TAB 6: FANTASY CRICKET ASSISTANT (PRO VERSION) ---
def render_fantasy_assistant():
    st.title("💸 Dream11 Fantasy XI Optimizer (Pro)")
    st.markdown("### Weighted Form & Role-Based AI Generator")
    st.info("💡 *The AI gives a 1.5x weight multiplier to recent seasons to prioritize current form. It then mathematically builds a legal 11-player lineup (WKs, BATs, ARs, BOWLs).*")
    
    col1, col2 = st.columns(2)
    with col1:
        team1 = st.selectbox("Select Team 1", team_choices, index=default_t1_idx, key='fant_t1')
    with col2:
        team2 = st.selectbox("Select Team 2", team_choices, index=default_t2_idx, key='fant_t2')
        
    if st.button("🔮 Generate Optimal Playing XI", use_container_width=True):
        st.session_state.fantasy_clicked = True
        
    if st.session_state.get('fantasy_clicked', False):
        if team1 == team2:
            st.warning("Please select two different teams.")
            return
            
        with st.spinner("Crunching historical data and weighting recent form..."):
            team_mapping = {
                'Delhi Daredevils': 'Delhi Capitals', 'Kings XI Punjab': 'Punjab Kings', 
                'Deccan Chargers': 'Sunrisers Hyderabad', 'Royal Challengers Bangalore': 'Royal Challengers Bengaluru', 
                'Gujarat Lions': 'Gujarat Titans'
            }
            working_matches = matches_df.copy()
            working_matches.replace(team_mapping, inplace=True)
            
            match_subset = working_matches[((working_matches['team1'] == team1) & (working_matches['team2'] == team2)) | 
                                           ((working_matches['team1'] == team2) & (working_matches['team2'] == team1))].copy()
            
            if match_subset.empty:
                st.warning("No historical match data found between these two teams.")
                return
                
            if pd.api.types.is_numeric_dtype(match_subset['season']):
                recent_cutoff = match_subset['season'].max() - 2
                match_subset['weight'] = match_subset['season'].apply(lambda x: 1.5 if x >= recent_cutoff else 1.0)
            else:
                match_subset['weight'] = 1.0 
                
            dels = deliveries_df[deliveries_df['match_id'].isin(match_subset['id'])].copy()
            dels = dels.merge(match_subset[['id', 'weight']], left_on='match_id', right_on='id', how='left')
            
            batter_col = 'batter' if 'batter' in dels.columns else 'batsman'
            
            dels['bat_pts'] = (dels['batsman_runs'] + 
                               (dels['batsman_runs'] == 4).astype(int) + 
                               ((dels['batsman_runs'] == 6).astype(int) * 2)) * dels['weight']
                               
            bat_stats = dels.groupby(batter_col).agg(
                balls_faced=('match_id', 'count'),
                batting_pts=('bat_pts', 'sum')
            ).reset_index().rename(columns={batter_col: 'Player'})
            
            if 'is_wicket' not in dels.columns:
                dels['is_wicket'] = dels['player_dismissed'].notnull().astype(int)
            
            valid_dismissals = ['caught', 'bowled', 'lbw', 'stumped', 'caught and bowled']
            if 'dismissal_kind' in dels.columns:
                bowl_dels = dels[dels['dismissal_kind'].isin(valid_dismissals)].copy()
            else:
                bowl_dels = dels[dels['is_wicket'] == 1].copy()
                
            bowl_dels['bowl_pts'] = 25 * bowl_dels['weight']
            bowl_stats = bowl_dels.groupby('bowler').agg(
                wickets=('is_wicket', 'sum'),
                bowling_pts=('bowl_pts', 'sum')
            ).reset_index()
            
            balls_bowled = dels.groupby('bowler').agg(balls_bowled=('match_id', 'count')).reset_index().rename(columns={'bowler': 'Player'})
            
            fantasy_df = pd.merge(bat_stats, bowl_stats.rename(columns={'bowler': 'Player'}), on='Player', how='outer').fillna(0)
            fantasy_df = pd.merge(fantasy_df, balls_bowled, on='Player', how='outer').fillna(0)
            fantasy_df['Total_Points'] = fantasy_df['batting_pts'] + fantasy_df['bowling_pts']
            fantasy_df = fantasy_df.sort_values(by='Total_Points', ascending=False)
            
            wk_list = ['MS Dhoni', 'RR Pant', 'SV Samson', 'KL Rahul', 'Q de Kock', 'Ishan Kishan', 'N Pooran', 'JC Buttler', 'PD Salt', 'H Klaasen', 'WP Saha', 'KD Karthik']
            
            def assign_role(row):
                if row['Player'] in wk_list: return 'WK'
                if row['balls_bowled'] > 24 and row['balls_faced'] > 24: return 'AR'
                if row['balls_bowled'] > 48: return 'BOWL'
                return 'BAT'
                
            fantasy_df['Role'] = fantasy_df.apply(assign_role, axis=1)
            
            selected_xi = []
            
            def draft_player(role, required_count):
                pool = fantasy_df[(fantasy_df['Role'] == role) & (~fantasy_df['Player'].isin([p['Player'] for p in selected_xi]))]
                for _, player in pool.head(required_count).iterrows():
                    selected_xi.append(player.to_dict())

            draft_player('WK', 1)
            draft_player('BAT', 3)
            draft_player('AR', 1)
            draft_player('BOWL', 3)
            
            remaining_pool = fantasy_df[~fantasy_df['Player'].isin([p['Player'] for p in selected_xi])]
            for _, player in remaining_pool.head(11 - len(selected_xi)).iterrows():
                selected_xi.append(player.to_dict())
                
            final_team_df = pd.DataFrame(selected_xi).sort_values(by='Total_Points', ascending=False).reset_index(drop=True)
            
            captain = final_team_df.iloc[0]
            vice_captain = final_team_df.iloc[1]
            
            st.divider()
            st.subheader("👑 Dream11 Leaders")
            c1, c2 = st.columns(2)
            c1.success(f"**CAPTAIN (C) - 2x Points:**\n### {captain['Player']} ({captain['Role']})\n*Weighted Form Score: {int(captain['Total_Points'])}*")
            c2.info(f"**VICE-CAPTAIN (VC) - 1.5x Points:**\n### {vice_captain['Player']} ({vice_captain['Role']})\n*Weighted Form Score: {int(vice_captain['Total_Points'])}*")
            
            st.subheader("🏏 Mathematically Optimal Playing XI")
            
            display_df = final_team_df[['Player', 'Role', 'Total_Points']].copy()
            display_df.columns = ['Player Name', 'Role', 'AI Weighted Projection']
            display_df['AI Weighted Projection'] = display_df['AI Weighted Projection'].astype(int)
            
            display_df['Role_Order'] = display_df['Role'].map({'WK': 1, 'BAT': 2, 'AR': 3, 'BOWL': 4})
            display_df = display_df.sort_values(by=['Role_Order', 'AI Weighted Projection'], ascending=[True, False]).drop(columns=['Role_Order'])
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)

# --- MAIN APP UI ---
def main():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Rajdhani', sans-serif !important;
            letter-spacing: 0.5px;
        }

        .stApp {
            background-image: url("https://images.unsplash.com/photo-1540747913346-19e32dc3e97e?q=80&w=2805&auto=format&fit=crop");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }
        
        [data-testid="stAppViewContainer"] {
            background-color: rgba(15, 5, 25, 0.85);
        }
        
        [data-testid="stHeader"] {
            background-color: transparent;
        }

        div[data-testid="stButton"] > button {
            background: linear-gradient(90deg, #b026ff 0%, #00d4ff 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 10px 24px !important;
            font-weight: 700 !important;
            font-size: 18px !important;
            letter-spacing: 1px !important;
            text-transform: uppercase !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 0 15px rgba(176, 38, 255, 0.5) !important;
        }
        
        div[data-testid="stButton"] > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 0 25px rgba(0, 212, 255, 0.8) !important;
            border: 1px solid white !important;
        }

        h1, h2, h3 {
            color: #ffffff !important;
            text-shadow: 0 0 10px rgba(255, 255, 255, 0.3) !important;
        }
        
        [data-testid="stMetricValue"] {
            color: #00d4ff !important; 
            text-shadow: 0 0 8px rgba(0, 212, 255, 0.4) !important;
            font-weight: 700 !important;
        }
                
    </style>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Pre-Match Predictor", "Live Win Probability", "Player Stats", 
        "Team Intelligence", "Venue Intelligence", "Fantasy XI Assistant"
    ])
    
    with tab1: render_pre_match()
    with tab2: render_live_match()
    with tab3: render_player_intel()
    with tab4: render_team_intel()
    with tab5: render_venue_intel()
    with tab6: render_fantasy_assistant()

if __name__ == "__main__":
    main()