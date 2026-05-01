import pandas as pd
import os

# --- BULLETPROOF PATH CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
ROSTER_CSV_PATH = os.path.join(BASE_DIR, 'data', 'raw', 'ipl_2026_rosters.csv')

def generate_seed_roster():
    print("📋 Generating Initial 2026 Seed Roster...")
    
    # A robust starting list of core IPL players for the 2026 season.
    # The Live Worker will automatically add to this list as matches are played!
    seed_players = [
        # Chennai Super Kings
        {'Team': 'Chennai Super Kings', 'FullName': 'MS Dhoni', 'DB_Name': 'MS Dhoni', 'Role': 'WK-Batsman'},
        {'Team': 'Chennai Super Kings', 'FullName': 'Ruturaj Gaikwad', 'DB_Name': 'RD Gaikwad', 'Role': 'Batsman'},
        {'Team': 'Chennai Super Kings', 'FullName': 'Ravindra Jadeja', 'DB_Name': 'RA Jadeja', 'Role': 'All-Rounder'},
        {'Team': 'Chennai Super Kings', 'FullName': 'Shivam Dube', 'DB_Name': 'S Dube', 'Role': 'All-Rounder'},
        {'Team': 'Chennai Super Kings', 'FullName': 'Deepak Chahar', 'DB_Name': 'DL Chahar', 'Role': 'Bowler'},
        {'Team': 'Chennai Super Kings', 'FullName': 'Matheesha Pathirana', 'DB_Name': 'M Pathirana', 'Role': 'Bowler'},
        {'Team': 'Chennai Super Kings', 'FullName': 'Daryl Mitchell', 'DB_Name': 'DJ Mitchell', 'Role': 'All-Rounder'},
        {'Team': 'Chennai Super Kings', 'FullName': 'Ajinkya Rahane', 'DB_Name': 'AM Rahane', 'Role': 'Batsman'},
        
        # Mumbai Indians
        {'Team': 'Mumbai Indians', 'FullName': 'Rohit Sharma', 'DB_Name': 'RG Sharma', 'Role': 'Batsman'},
        {'Team': 'Mumbai Indians', 'FullName': 'Hardik Pandya', 'DB_Name': 'HH Pandya', 'Role': 'All-Rounder'},
        {'Team': 'Mumbai Indians', 'FullName': 'Jasprit Bumrah', 'DB_Name': 'JJ Bumrah', 'Role': 'Bowler'},
        {'Team': 'Mumbai Indians', 'FullName': 'Suryakumar Yadav', 'DB_Name': 'SA Yadav', 'Role': 'Batsman'},
        {'Team': 'Mumbai Indians', 'FullName': 'Ishan Kishan', 'DB_Name': 'Ishan Kishan', 'Role': 'WK-Batsman'},
        {'Team': 'Mumbai Indians', 'FullName': 'Tim David', 'DB_Name': 'TH David', 'Role': 'Batsman'},
        {'Team': 'Mumbai Indians', 'FullName': 'Gerald Coetzee', 'DB_Name': 'G Coetzee', 'Role': 'Bowler'},
        {'Team': 'Mumbai Indians', 'FullName': 'Piyush Chawla', 'DB_Name': 'PP Chawla', 'Role': 'Bowler'},
        
        # Royal Challengers Bengaluru
        {'Team': 'Royal Challengers Bengaluru', 'FullName': 'Virat Kohli', 'DB_Name': 'V Kohli', 'Role': 'Batsman'},
        {'Team': 'Royal Challengers Bengaluru', 'FullName': 'Faf du Plessis', 'DB_Name': 'F du Plessis', 'Role': 'Batsman'},
        {'Team': 'Royal Challengers Bengaluru', 'FullName': 'Glenn Maxwell', 'DB_Name': 'GJ Maxwell', 'Role': 'All-Rounder'},
        {'Team': 'Royal Challengers Bengaluru', 'FullName': 'Mohammed Siraj', 'DB_Name': 'Mohammed Siraj', 'Role': 'Bowler'},
        {'Team': 'Royal Challengers Bengaluru', 'FullName': 'Dinesh Karthik', 'DB_Name': 'KD Karthik', 'Role': 'WK-Batsman'},
        {'Team': 'Royal Challengers Bengaluru', 'FullName': 'Rajat Patidar', 'DB_Name': 'RM Patidar', 'Role': 'Batsman'},
        {'Team': 'Royal Challengers Bengaluru', 'FullName': 'Cameron Green', 'DB_Name': 'C Green', 'Role': 'All-Rounder'},
        {'Team': 'Royal Challengers Bengaluru', 'FullName': 'Alzarri Joseph', 'DB_Name': 'AS Joseph', 'Role': 'Bowler'},
        
        # Kolkata Knight Riders
        {'Team': 'Kolkata Knight Riders', 'FullName': 'Shreyas Iyer', 'DB_Name': 'SS Iyer', 'Role': 'Batsman'},
        {'Team': 'Kolkata Knight Riders', 'FullName': 'Andre Russell', 'DB_Name': 'AD Russell', 'Role': 'All-Rounder'},
        {'Team': 'Kolkata Knight Riders', 'FullName': 'Sunil Narine', 'DB_Name': 'SP Narine', 'Role': 'All-Rounder'},
        {'Team': 'Kolkata Knight Riders', 'FullName': 'Mitchell Starc', 'DB_Name': 'MA Starc', 'Role': 'Bowler'},
        {'Team': 'Kolkata Knight Riders', 'FullName': 'Rinku Singh', 'DB_Name': 'RK Singh', 'Role': 'Batsman'},
        {'Team': 'Kolkata Knight Riders', 'FullName': 'Varun Chakaravarthy', 'DB_Name': 'CV Varun', 'Role': 'Bowler'},
        {'Team': 'Kolkata Knight Riders', 'FullName': 'Phil Salt', 'DB_Name': 'PD Salt', 'Role': 'WK-Batsman'},
        {'Team': 'Kolkata Knight Riders', 'FullName': 'Venkatesh Iyer', 'DB_Name': 'VR Iyer', 'Role': 'All-Rounder'},
        
        # Rajasthan Royals
        {'Team': 'Rajasthan Royals', 'FullName': 'Sanju Samson', 'DB_Name': 'SV Samson', 'Role': 'WK-Batsman'},
        {'Team': 'Rajasthan Royals', 'FullName': 'Jos Buttler', 'DB_Name': 'JC Buttler', 'Role': 'WK-Batsman'},
        {'Team': 'Rajasthan Royals', 'FullName': 'Yashasvi Jaiswal', 'DB_Name': 'YBK Jaiswal', 'Role': 'Batsman'},
        {'Team': 'Rajasthan Royals', 'FullName': 'Trent Boult', 'DB_Name': 'TA Boult', 'Role': 'Bowler'},
        {'Team': 'Rajasthan Royals', 'FullName': 'Yuzvendra Chahal', 'DB_Name': 'YS Chahal', 'Role': 'Bowler'},
        {'Team': 'Rajasthan Royals', 'FullName': 'Ravichandran Ashwin', 'DB_Name': 'R Ashwin', 'Role': 'All-Rounder'},
        {'Team': 'Rajasthan Royals', 'FullName': 'Riyan Parag', 'DB_Name': 'R Parag', 'Role': 'Batsman'},
        {'Team': 'Rajasthan Royals', 'FullName': 'Avesh Khan', 'DB_Name': 'Avesh Khan', 'Role': 'Bowler'},
        
        # Sunrisers Hyderabad
        {'Team': 'Sunrisers Hyderabad', 'FullName': 'Pat Cummins', 'DB_Name': 'PJ Cummins', 'Role': 'Bowler'},
        {'Team': 'Sunrisers Hyderabad', 'FullName': 'Heinrich Klaasen', 'DB_Name': 'H Klaasen', 'Role': 'WK-Batsman'},
        {'Team': 'Sunrisers Hyderabad', 'FullName': 'Travis Head', 'DB_Name': 'TM Head', 'Role': 'Batsman'},
        {'Team': 'Sunrisers Hyderabad', 'FullName': 'Abhishek Sharma', 'DB_Name': 'Abhishek Sharma', 'Role': 'All-Rounder'},
        {'Team': 'Sunrisers Hyderabad', 'FullName': 'Bhuvneshwar Kumar', 'DB_Name': 'B Kumar', 'Role': 'Bowler'},
        {'Team': 'Sunrisers Hyderabad', 'FullName': 'Aiden Markram', 'DB_Name': 'AK Markram', 'Role': 'Batsman'},
        {'Team': 'Sunrisers Hyderabad', 'FullName': 'T Natarajan', 'DB_Name': 'T Natarajan', 'Role': 'Bowler'},
        {'Team': 'Sunrisers Hyderabad', 'FullName': 'Nitish Reddy', 'DB_Name': 'NK Reddy', 'Role': 'All-Rounder'},

        # Delhi Capitals
        {'Team': 'Delhi Capitals', 'FullName': 'Rishabh Pant', 'DB_Name': 'RR Pant', 'Role': 'WK-Batsman'},
        {'Team': 'Delhi Capitals', 'FullName': 'David Warner', 'DB_Name': 'DA Warner', 'Role': 'Batsman'},
        {'Team': 'Delhi Capitals', 'FullName': 'Axar Patel', 'DB_Name': 'AR Patel', 'Role': 'All-Rounder'},
        {'Team': 'Delhi Capitals', 'FullName': 'Kuldeep Yadav', 'DB_Name': 'Kuldeep Yadav', 'Role': 'Bowler'},
        {'Team': 'Delhi Capitals', 'FullName': 'Mitchell Marsh', 'DB_Name': 'MR Marsh', 'Role': 'All-Rounder'},
        {'Team': 'Delhi Capitals', 'FullName': 'Prithvi Shaw', 'DB_Name': 'PP Shaw', 'Role': 'Batsman'},
        {'Team': 'Delhi Capitals', 'FullName': 'Anrich Nortje', 'DB_Name': 'A Nortje', 'Role': 'Bowler'},
        {'Team': 'Delhi Capitals', 'FullName': 'Tristan Stubbs', 'DB_Name': 'T Stubbs', 'Role': 'WK-Batsman'},
        
        # Punjab Kings
        {'Team': 'Punjab Kings', 'FullName': 'Shikhar Dhawan', 'DB_Name': 'S Dhawan', 'Role': 'Batsman'},
        {'Team': 'Punjab Kings', 'FullName': 'Sam Curran', 'DB_Name': 'SM Curran', 'Role': 'All-Rounder'},
        {'Team': 'Punjab Kings', 'FullName': 'Arshdeep Singh', 'DB_Name': 'Arshdeep Singh', 'Role': 'Bowler'},
        {'Team': 'Punjab Kings', 'FullName': 'Kagiso Rabada', 'DB_Name': 'K Rabada', 'Role': 'Bowler'},
        {'Team': 'Punjab Kings', 'FullName': 'Liam Livingstone', 'DB_Name': 'LS Livingstone', 'Role': 'All-Rounder'},
        {'Team': 'Punjab Kings', 'FullName': 'Jonny Bairstow', 'DB_Name': 'JM Bairstow', 'Role': 'WK-Batsman'},
        {'Team': 'Punjab Kings', 'FullName': 'Jitesh Sharma', 'DB_Name': 'JM Sharma', 'Role': 'WK-Batsman'},
        {'Team': 'Punjab Kings', 'FullName': 'Harshal Patel', 'DB_Name': 'HV Patel', 'Role': 'Bowler'},
        
        # Lucknow Super Giants
        {'Team': 'Lucknow Super Giants', 'FullName': 'KL Rahul', 'DB_Name': 'KL Rahul', 'Role': 'WK-Batsman'},
        {'Team': 'Lucknow Super Giants', 'FullName': 'Quinton de Kock', 'DB_Name': 'Q de Kock', 'Role': 'WK-Batsman'},
        {'Team': 'Lucknow Super Giants', 'FullName': 'Nicholas Pooran', 'DB_Name': 'N Pooran', 'Role': 'WK-Batsman'},
        {'Team': 'Lucknow Super Giants', 'FullName': 'Marcus Stoinis', 'DB_Name': 'MP Stoinis', 'Role': 'All-Rounder'},
        {'Team': 'Lucknow Super Giants', 'FullName': 'Ravi Bishnoi', 'DB_Name': 'R Bishnoi', 'Role': 'Bowler'},
        {'Team': 'Lucknow Super Giants', 'FullName': 'Krunal Pandya', 'DB_Name': 'KH Pandya', 'Role': 'All-Rounder'},
        {'Team': 'Lucknow Super Giants', 'FullName': 'Mayank Yadav', 'DB_Name': 'M Yadav', 'Role': 'Bowler'},
        {'Team': 'Lucknow Super Giants', 'FullName': 'Ayush Badoni', 'DB_Name': 'A Badoni', 'Role': 'Batsman'},
        
        # Gujarat Titans
        {'Team': 'Gujarat Titans', 'FullName': 'Shubman Gill', 'DB_Name': 'Shubman Gill', 'Role': 'Batsman'},
        {'Team': 'Gujarat Titans', 'FullName': 'Rashid Khan', 'DB_Name': 'Rashid Khan', 'Role': 'All-Rounder'},
        {'Team': 'Gujarat Titans', 'FullName': 'David Miller', 'DB_Name': 'DA Miller', 'Role': 'Batsman'},
        {'Team': 'Gujarat Titans', 'FullName': 'Sai Sudharsan', 'DB_Name': 'B Sai Sudharsan', 'Role': 'Batsman'},
        {'Team': 'Gujarat Titans', 'FullName': 'Wriddhiman Saha', 'DB_Name': 'WP Saha', 'Role': 'WK-Batsman'},
        {'Team': 'Gujarat Titans', 'FullName': 'Mohit Sharma', 'DB_Name': 'MM Sharma', 'Role': 'Bowler'},
        {'Team': 'Gujarat Titans', 'FullName': 'Spencer Johnson', 'DB_Name': 'SH Johnson', 'Role': 'Bowler'},
        {'Team': 'Gujarat Titans', 'FullName': 'Rahul Tewatia', 'DB_Name': 'R Tewatia', 'Role': 'All-Rounder'}
    ]

    roster_df = pd.DataFrame(seed_players)
    os.makedirs(os.path.dirname(ROSTER_CSV_PATH), exist_ok=True)
    roster_df.to_csv(ROSTER_CSV_PATH, index=False)
    
    print(f"✅ Created Initial Database! Saved {len(roster_df)} marquee players across all franchises.")

if __name__ == "__main__":
    generate_seed_roster()