import pandas as pd
import requests
import os
import csv

def run_historical_backtest(target_year):
    print("==================================================")
    print(f"   SEABeacon Confidence Engine: {target_year} Backtest     ")
    print("==================================================\n")
    
    print("--> 1. Connecting to NOAA IBTrACS Meteorological Archive...")
    # The direct link to the Western North Pacific best-track dataset
    url = "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r00/access/csv/ibtracs.WP.list.v04r00.csv"
    
    # We must skip row 1, as NOAA uses it for unit descriptions which breaks Pandas
    df = pd.read_csv(url, skiprows=[1], low_memory=False)
    
    print(f"--> 2. Filtering for the {target_year} Pacific Typhoon Season...")
    # Convert SEASON column to numeric to handle any string formatting anomalies
    df['SEASON'] = pd.to_numeric(df['SEASON'], errors='coerce')
    df_target = df[df['SEASON'] == float(target_year)].copy()
    
    # Filter out unnamed depressions to focus on significant storms
    df_target = df_target[df_target['NAME'] != 'NOT_NAMED']
    unique_storms = df_target['NAME'].unique()
    
    print(f"--> Found {len(unique_storms)} named storms in {target_year}.")
    
    # Setup isolated local CSV log
    log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'logs'))
    os.makedirs(log_dir, exist_ok=True)
    csv_path = os.path.join(log_dir, f'{target_year}_confidence_backtest.csv')
    
    print(f"--> 3. Initializing local fine-tuning report: {csv_path}\n")
    
    API_URL = "http://127.0.0.1:8000/api/v1/spatial-conversion"
    
    # Open the CSV file and start the high-speed data stream
    with open(csv_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        # Write the header row
        writer.writerow(["Storm Name", "Timestamp (UTC)", "Lat", "Lon", "Wind (KPH)", "Alert Status", "Impact Matrix JSON"])
        
        for storm in unique_storms:
            print(f"🌀 Processing historic data for: {storm}...")
            storm_data = df_target[df_target['NAME'] == storm]
            
            for index, row in storm_data.iterrows():
                try:
                    # Parse NOAA wind data (which is in knots) to KPH
                    wind_kts = float(row['USA_WIND']) if pd.notna(row['USA_WIND']) else 0.0
                    wind_kph = wind_kts * 1.852 
                    
                    # Construct the payload
                    payload = {
                        "simulation_run_id": f"historical-backtest-{target_year}",
                        "storm_name": storm,
                        "base_timestamp": row['ISO_TIME'].replace(" ", "T") + "Z",
                        "lead_time_hours": 0, # Ground truth data implies 0 hours lead time
                        "timestamp": row['ISO_TIME'].replace(" ", "T") + "Z",
                        "latitude": float(row['LAT']),
                        "longitude": float(row['LON']),
                        "cross_track_error_km": 150.0, # Baseline spatial uncertainty
                        "wind_speed_kph": round(wind_kph, 2)
                    }
                    
                    # Fire to FastAPI Server without sleep delays
                    response = requests.post(API_URL, json=payload)
                    
                    if response.status_code == 200:
                        result = response.json()
                        writer.writerow([
                            storm,
                            payload["timestamp"],
                            payload["latitude"],
                            payload["longitude"],
                            payload["wind_speed_kph"],
                            result["alert_status"],
                            result["impacted_regions"]
                        ])
                except Exception as e:
                    # Silently skip malformed historical rows to maintain execution speed
                    continue
                    
    print(f"\n✅ {target_year} Backtest Complete. Full report saved to: {csv_path}")

if __name__ == "__main__":
    # You can change this year to whatever historical season you want to test!
    run_historical_backtest(target_year=2023)