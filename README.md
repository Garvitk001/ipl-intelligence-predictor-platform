# 🏏 IPL Intelligence Platform ⚡

An autonomous, real-time Cricket analytics dashboard powered by Machine Learning and Google Gemini. This platform ingests live match data, calculates dynamic win probabilities, generates automated fantasy lineups, and broadcasts AI-driven match commentary and alerts.

## 🚀 Key Features

* **⚡ Autonomous Live Match Engine:** Runs continuously in the background, syncing live ball-by-ball data and match states without manual intervention.
* **🧠 Real-Time Win Probability:** Uses 3 specialized Machine Learning models (Powerplay, Middle Overs, Death Overs) to calculate dynamic win percentages based on current run rate, wickets in hand, and target scores.
* **🪙 AI Toss Optimizer:** Analyzes historical venue data and "Pitch DNA" to recommend whether the captain should elect to bat or field.
* **💸 Dream11 Fantasy XI Generator:** Uses a weighted algorithm to prioritize recent form and mathematically construct the optimal, rule-compliant 11-player fantasy lineup (WK, BAT, AR, BOWL).
* **🎙️ Gen AI Commentary Desk:** Integrates Google's Gemini API to generate highly energetic, context-aware match summaries based on the live data feed.
* **📱 Automated Telegram Alerts:** Pushes real-time alerts to a Telegram channel for massive momentum shifts, wicket collapses, and rapid run surges.

## 🛠️ Tech Stack

* **Frontend:** Streamlit, Plotly (for interactive cyberpunk/esports-themed visualizations)
* **Backend Worker:** Python, Requests, JSON
* **Machine Learning:** Scikit-Learn, Pandas, NumPy, Joblib
* **APIs Used:** RapidAPI (Cricbuzz Live Data), Google Generative AI (Gemini), OpenWeatherMap, Telegram Bot API

## 📂 Project Structure

```text
ipl-intelligence-platform/
│
├── app.py                     # The main Streamlit Dashboard UI
├── requirements.txt           # Python dependencies
├── .env                       # API keys and secrets (NOT uploaded to GitHub)
├── .gitignore                 # Keeps secrets safe
│
├── utils/
│   ├── live_api_worker.py     # Background engine that fetches data & runs models
│   └── backfill_2026.py       # Script to backfill missing historical data
│
├── models/                    # Pre-trained Scikit-Learn .pkl models
│
└── data/
    ├── raw/                   # Ball-by-ball and match history CSVs
    └── processed/             # Cleaned ETL data and live_match_state.json