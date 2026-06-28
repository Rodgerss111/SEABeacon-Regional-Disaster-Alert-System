import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine
import glob
import os

print("==================================================")
print("   SEABeacon ASEAN Transboundary Map Merger       ")
print("==================================================\n")

# 1. Your Exact Supabase URL (Paste the one with port 6543 here!)
SUPABASE_URL = "postgresql://postgres.axigjjehzqghflrvewaj:loGiwer21Glw@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"
engine = create_engine(SUPABASE_URL)

# 2. Find ONLY the Level 1 (Province) shapefiles
shapefile_paths = glob.glob("data/shapefiles/*_1.shp")

if not shapefile_paths:
    print("❌ Could not find any Level 1 shapefiles. Make sure files ending in '_1.shp' are in the folder.")
    exit()

print(f"--> Found {len(shapefile_paths)} Province-Level Maps:")
gdfs = []

# 3. Load and standardize all maps
for path in shapefile_paths:
    print(f"    * Processing {os.path.basename(path)}...")
    gdf = gpd.read_file(path)
    
    # Ensure standard GPS coordinates (WGS84)
    if gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")
    
    gdfs.append(gdf)

# 4. Fuse them together into a super-map
print("\n--> Fusing maps into a single ASEAN Transboundary Polygon Network...")
combined_gdf = pd.concat(gdfs, ignore_index=True)

print("--> Connecting to Supabase and uploading geography...")
print("--> ⚠️ DO NOT CLOSE THIS WINDOW. Uploading heavy spatial data...")

try:
    # Push the fused map directly to Supabase as PostGIS geometry!
    combined_gdf.to_postgis(
        "gadm_regions", 
        engine, 
        if_exists="replace", 
        index=False,
        dtype={'geometry': 'Geometry'}
    )
    
    print("\n✅ SUCCESS! Transboundary ASEAN Map successfully migrated to the Cloud!")
    
except Exception as e:
    print(f"\n❌ Migration Failed: {e}")