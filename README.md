# 🏏 IPL Intelligence Platform ⚡

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://ipl-2026-pro.streamlit.app/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**[🔴 View the Live Dashboard](https://ipl-2026-pro.streamlit.app/)**

An autonomous, real-time cricket analytics platform powered by Machine Learning and Google Gemini. This platform ingests live match telemetry, calculates dynamic win probabilities across match phases, generates mathematically optimal fantasy lineups, and broadcasts AI-driven match commentary and alerts.

---

## 🚀 Key Features

* **⚡ Autonomous Live Match Engine:** Runs continuously in the background, syncing live ball-by-ball data and match states without manual intervention.
* **🧠 Real-Time Win Probability:** Uses 3 specialized Machine Learning models (Powerplay, Middle Overs, Death Overs) to calculate dynamic win percentages based on current run rate, wickets in hand, and target scores.
* **🪙 AI Toss Optimizer:** Analyzes historical venue data and "Pitch DNA" to recommend whether the captain should elect to bat or field.
* **💸 Dream11 Fantasy XI Generator:** Uses a weighted algorithm to prioritize recent player form and mathematically construct the optimal, rule-compliant 11-player fantasy lineup (WK, BAT, AR, BOWL).
* **🎙️ Gen AI Commentary Desk:** Integrates Google Gemini API to generate highly energetic, context-aware match summaries based on live data feeds.
* **📱 Automated Telegram Alerts:** Pushes real-time alerts to a Telegram channel for massive momentum shifts, wicket collapses, and rapid run surges.

---

## 🛠️ Tech Stack

* **Frontend:** Streamlit, Plotly (for interactive cyberpunk/esports-themed visualizations)
* **Backend Worker:** Python, Requests, JSON
* **Machine Learning:** Scikit-Learn, XGBoost, LightGBM, Pandas, NumPy, Joblib
* **APIs Used:** RapidAPI (Cricbuzz Live Data), Google Generative AI (Gemini), OpenWeatherMap, Telegram Bot API

---

## 📂 Project Structure

```text
ipl-intelligence-platform/
│
├── app.py                     # The main Streamlit Dashboard UI
├── test_bot.py                # Verification script for bot notifications
├── requirements.txt           # Python dependencies
├── .env                       # API keys and secrets (configured locally)
├── .gitignore                 # Secret and artifact guardrails
│
├── bot/                       # Telegram alert service integration
├── utils/
│   ├── live_api_worker.py     # Background engine that fetches data & runs models
│   └── backfill_2026.py       # Script to backfill missing historical data
│
├── models/                    # Pre-trained Scikit-Learn / ML models (.pkl)
├── notebooks/                 # Exploratory data analysis & model training
└── data/
    ├── raw/                   # Ball-by-ball and match history CSVs
    └── processed/             # Cleaned ETL data and live_match_state.json
```

---

## 💻 Quickstart — Run Locally

### 1. Clone the Repository
```bash
git clone https://github.com/Garvitk001/ipl-intelligence-predictor-platform.git
cd ipl-intelligence-predictor-platform
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
RAPIDAPI_KEY=your_rapidapi_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
```

### 5. Launch the Dashboard
```bash
streamlit run app.py
```
The application will launch automatically in your default browser at `http://localhost:8501`.

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
