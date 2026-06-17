import pandas as pd
import numpy as np
import warnings

# Suppress pandas FutureWarnings for clean console output
warnings.simplefilter(action='ignore', category=FutureWarning)

def load_and_preprocess(file_path):
    """
    Standardized MLOps pipeline for SEABeacon data.
    Takes raw IBTrACS data, cleans it, calculates physics vectors, 
    and outputs a pristine feature-engineered DataFrame ready for XGBoost.
    """
    print("--> [Preprocess] 1. Loading Raw Dataset...")
    df = pd.read_csv(file_path, skiprows=[1], low_memory=False, na_values=[' ', ''])
    
    # Prune and cast
    core_columns = [
        'SID', 'SEASON', 'ISO_TIME', 'NATURE', 'TRACK_TYPE',
        'TOKYO_LAT', 'TOKYO_LON', 'TOKYO_WIND', 'TOKYO_PRES', 'DIST2LAND'
    ]
    df = df[core_columns].copy()
    df['ISO_TIME'] = pd.to_datetime(df['ISO_TIME'])
    
    numeric_cols = ['TOKYO_LAT', 'TOKYO_LON', 'TOKYO_WIND', 'TOKYO_PRES', 'DIST2LAND']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    print("--> [Preprocess] 2. Applying Meteorological Filters...")
    df = df[df['TRACK_TYPE'] == 'main']
    df = df[~df['NATURE'].isin(['ET', 'DS'])]
    df['is_over_land'] = (df['DIST2LAND'] == 0).astype(int) # Boolean to Int for XGBoost
    
    print("--> [Preprocess] 3. Executing 6-Hour Temporal Resampling...")
    df = df.sort_values(['SID', 'ISO_TIME'])
    
    def resample_storm(storm_df):
        sid = storm_df['SID'].iloc[0]
        storm_df = storm_df.set_index('ISO_TIME')
        storm_df = storm_df.resample('6h').asfreq()
        storm_df.index.name = 'ISO_TIME'
        storm_df['SID'] = sid
        return storm_df
    
    df_6h = df.groupby('SID', group_keys=False).apply(resample_storm).reset_index()
    
    # Modern era and interpolation
    df_modern = df_6h[df_6h['SEASON'] >= 1980].copy()
    cols_to_interpolate = ['TOKYO_LAT', 'TOKYO_LON', 'TOKYO_WIND', 'TOKYO_PRES']
    df_modern[cols_to_interpolate] = df_modern.groupby('SID')[cols_to_interpolate].transform(
        lambda x: x.interpolate(method='linear', limit=2, limit_direction='forward')
    )
    df_clean = df_modern.dropna(subset=['TOKYO_LAT', 'TOKYO_LON']).copy()
    
    print("--> [Preprocess] 4. Executing Wind-Pressure Imputation Physics...")
    mask_ocean = df_clean['is_over_land'] == 0
    
    # Impute missing pressure
    mask_missing_pres = df_clean['TOKYO_PRES'].isna() & df_clean['TOKYO_WIND'].notna() & mask_ocean
    v_1min = df_clean.loc[mask_missing_pres, 'TOKYO_WIND'] * 1.14
    df_clean.loc[mask_missing_pres, 'TOKYO_PRES'] = 1010 - (v_1min / 6.7) ** (1 / 0.644)
    
    # Impute missing wind
    mask_missing_wind = df_clean['TOKYO_WIND'].isna() & df_clean['TOKYO_PRES'].notna() & mask_ocean
    mask_calc_wind = mask_missing_wind & (df_clean['TOKYO_PRES'] < 1010)
    v_1min_calc = 6.7 * ((1010 - df_clean.loc[mask_calc_wind, 'TOKYO_PRES']) ** 0.644)
    df_clean.loc[mask_calc_wind, 'TOKYO_WIND'] = v_1min_calc / 1.14
    
    mask_base_wind = mask_missing_wind & (df_clean['TOKYO_PRES'] >= 1010)
    df_clean.loc[mask_base_wind, 'TOKYO_WIND'] = 15.0
    
    df_clean = df_clean.dropna(subset=['TOKYO_WIND', 'TOKYO_PRES']).copy()
    
    print("--> [Preprocess] 5. Engineering Advanced Vector Features...")
    df_clean['day_of_year'] = df_clean['ISO_TIME'].dt.dayofyear
    df_clean['sin_season'] = np.sin(2 * np.pi * df_clean['day_of_year'] / 365.25)
    df_clean['cos_season'] = np.cos(2 * np.pi * df_clean['day_of_year'] / 365.25)
    
    df_clean = df_clean.sort_values(by=['SID', 'ISO_TIME'])
    df_clean['delta_lat'] = df_clean.groupby('SID')['TOKYO_LAT'].diff()
    df_clean['delta_lon'] = df_clean.groupby('SID')['TOKYO_LON'].diff()
    
    cols_to_shift = ['TOKYO_LAT', 'TOKYO_LON', 'TOKYO_WIND', 'TOKYO_PRES']
    for col in cols_to_shift:
        df_clean[f'{col}_t-12'] = df_clean.groupby('SID')[col].shift(2)
        df_clean[f'{col}_t-6'] = df_clean.groupby('SID')[col].shift(1)
        
    print("--> [Preprocess] 6. Constructing 3D Predictive Targets (Lat, Lon, Wind)...")
    df_clean['TARGET_LAT'] = df_clean.groupby('SID')['TOKYO_LAT'].shift(-1)
    df_clean['TARGET_LON'] = df_clean.groupby('SID')['TOKYO_LON'].shift(-1)
    # NEW: We are now explicitly tracking intensity as a learning objective
    df_clean['TARGET_WIND'] = df_clean.groupby('SID')['TOKYO_WIND'].shift(-1) 
    
    df_ml = df_clean.dropna().copy()
    print(f"--> [Preprocess] Pipeline Complete. {df_ml.shape[0]} valid multi-dimensional matrices extracted.\n")
    
    return df_ml