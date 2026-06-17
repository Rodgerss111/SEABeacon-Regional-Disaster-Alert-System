import sys
import os
import numpy as np
import xgboost as xgb
import joblib
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import mean_absolute_error

# Dynamically add the src directory to the python path to import our pipeline
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.data_pipeline.preprocess import load_and_preprocess

def haversine(lat1, lon1, lat2, lon2):
    """Calculates spatial distance in kilometers between two coordinates."""
    R = 6371.0
    lat1_rad, lon1_rad = np.radians(lat1), np.radians(lon1)
    lat2_rad, lon2_rad = np.radians(lat2), np.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = np.sin(dlat / 2.0)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2.0)**2
    return R * (2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a)))

def train_model():
    print("==================================================")
    print("   SEABeacon 3D XGBoost Engine Training Routine   ")
    print("==================================================\n")
    
    # 1. Ingest and Clean Data using the standardized pipeline
    data_path = os.path.join('data', 'raw', 'ibtracs.WP.list.v04r01.csv')
    df_ml = load_and_preprocess(data_path)
    
    # 2. Define ML Architecture
    features = [
        'TOKYO_LAT_t-12', 'TOKYO_LON_t-12', 'TOKYO_WIND_t-12', 'TOKYO_PRES_t-12',
        'TOKYO_LAT_t-6', 'TOKYO_LON_t-6', 'TOKYO_WIND_t-6', 'TOKYO_PRES_t-6',
        'TOKYO_LAT', 'TOKYO_LON', 'TOKYO_WIND', 'TOKYO_PRES',
        'delta_lat', 'delta_lon', 'sin_season', 'cos_season', 'is_over_land'
    ]
    # NEW: The AI must now output three answers instead of two
    targets = ['TARGET_LAT', 'TARGET_LON', 'TARGET_WIND'] 
    
    # Force float datatype to prevent XGBoost errors
    for col in features:
        df_ml[col] = df_ml[col].astype(float)
        
    print("--> [Training] Executing Chronological Split (1980-2018 vs 2019+)...")
    df_ml['year'] = df_ml['ISO_TIME'].dt.year
    train_mask = df_ml['year'] <= 2018
    test_mask = df_ml['year'] >= 2019
    
    X_train, y_train = df_ml.loc[train_mask, features], df_ml.loc[train_mask, targets]
    X_test, y_test = df_ml.loc[test_mask, features], df_ml.loc[test_mask, targets]
    
    # 3. Train the Model
    print("--> [Training] Initializing MultiOutput XGBoost Engine...")
    base_xgb = xgb.XGBRegressor(
        n_estimators=100, learning_rate=0.1, max_depth=6, 
        random_state=42, n_jobs=-1
    )
    model = MultiOutputRegressor(base_xgb)
    
    print("--> [Training] Baking algorithms... (This may take a moment)")
    model.fit(X_train, y_train)
    
    # 4. Evaluate Performance (Spatial + Intensity)
    print("--> [Training] Evaluating 3D Accuracies on Test Set...")
    predictions = model.predict(X_test)
    
    pred_lat, pred_lon, pred_wind = predictions[:, 0], predictions[:, 1], predictions[:, 2]
    actual_lat, actual_lon, actual_wind = y_test['TARGET_LAT'].values, y_test['TARGET_LON'].values, y_test['TARGET_WIND'].values
    
    errors_km = haversine(actual_lat, actual_lon, pred_lat, pred_lon)
    wind_error_knots = mean_absolute_error(actual_wind, pred_wind)
    
    print("\n================ SYSTEM METRICS ================")
    print(f"Spatial Cross-Track Error (Median): {np.median(errors_km):.2f} km")
    print(f"Intensity Error (Mean Absolute):    {wind_error_knots:.2f} knots")
    print("================================================\n")
    
    # 5. Export the Artifact
    print("--> [System] Serializing and saving the trained model artifact...")
    os.makedirs('models', exist_ok=True)
    model_path = os.path.join('models', 'seabeacon_xgb_v1.pkl')
    joblib.dump(model, model_path)
    print(f"✅ Model successfully saved to: {model_path}")

if __name__ == "__main__":
    train_model()