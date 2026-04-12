import sqlite3
import os

def init_db():
    # 1. Ensure the data/processed directory exists
    os.makedirs('../data/processed', exist_ok=True)
    
    # 2. Connect to SQLite database (this creates the file if it doesn't exist)
    db_path = '../data/processed/ipl_live.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 3. Create table for Live API Data (Cricbuzz State)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS live_match_state (
            match_id TEXT PRIMARY KEY,
            batting_team TEXT,
            bowling_team TEXT,
            target INTEGER,
            current_score INTEGER,
            wickets INTEGER,
            overs REAL,
            crr REAL,
            rrr REAL,
            last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 4. Create table for tracking Prediction Accuracy (For Phase 9)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT,
            over REAL,
            predicted_winner TEXT,
            win_probability REAL,
            actual_winner TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print(f"✅ SQLite Database initialized successfully at {db_path}")

if __name__ == "__main__":
    # Run the setup
    init_db()