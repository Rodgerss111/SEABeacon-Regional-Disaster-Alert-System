from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import uvicorn
from typing import List, Dict, Any

# 1. Initialize FastAPI Application
app = FastAPI(
    title="SEABeacon Spatial Warning API",
    description="Transboundary Spatial Conversion Layer converting coordinates to localized alerts.",
    version="1.0.0"
)

# 2. Database Connection Configuration.
# Mapped directly to your running PostGIS Docker container
DATABASE_URL = "postgresql://seabeacon:securepassword@localhost:5432/spatial_db"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# 3. Define Pydantic Input Schema (Updated for Pydantic V2 compliance)
class PredictionPayload(BaseModel):
    simulation_run_id: str = Field(default="live-run", description="Unique ID for this simulation run")
    storm_name: str = Field(..., description="Name of the typhoon", json_schema_extra={"example": "Super Typhoon Kalmaegi"})
    
    # --- NEW ADDITIONS FOR LSTM ENSEMBLE ---
    base_timestamp: str = Field(..., description="Time the forecast was generated", json_schema_extra={"example": "2026-06-19T12:00:00Z"})
    lead_time_hours: int = Field(..., description="Forecast horizon in hours (e.g., 6, 12, 24)", json_schema_extra={"example": 24})
    # ---------------------------------------
    
    timestamp: str = Field(..., description="Forecast valid time (Target time)", json_schema_extra={"example": "2026-06-20T12:00:00Z"})
    latitude: float = Field(
        ..., 
        description="Predicted storm latitude coordinate", 
        json_schema_extra={"example": 15.0}
    )
    longitude: float = Field(
        ..., 
        description="Predicted storm longitude coordinate", 
        json_schema_extra={"example": 108.5}
    )
    cross_track_error_km: float = Field(
        ..., 
        description="Uncertainty radius around the track in kilometers", 
        json_schema_extra={"example": 94.0}
    )
    wind_speed_kph: float = Field(
        ..., 
        description="Predicted wind speed in KPH", 
        json_schema_extra={"example": 185.0}
    )
# Sub-schema for rich output
class ImpactedRegion(BaseModel):
    country: str
    province: str
    storm_name: str
    timestamp: str
    wind_speed_kph: float
    confidence_score: float

# 4. Define Pydantic Output Schema
class AlertResponse(BaseModel):
    alert_status: str
    impacted_count: int
    impacted_regions: List[ImpactedRegion]

# --- NEW: SUPABASE CONNECTION FOR LSTM DATA ---
SUPABASE_URL = "postgresql://postgres.axigjjehzqghflrvewaj:loGiwer21Glw@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"
supabase_engine = create_engine(SUPABASE_URL)

@app.get("/health")
def health_check():
    """Verify backend and database connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except OperationalError:
        raise HTTPException(status_code=500, detail="Database connection failed")

# 5. Core Spatial Conversion Endpoint (Case-Sensitivity Fix)
@app.post("/api/v1/spatial-conversion", response_model=AlertResponse)
async def spatial_conversion(payload: PredictionPayload):
    """
    Accepts an XGBoost trajectory prediction, constructs a metric buffer cone,
    and checks for transboundary geographic intersections using PostGIS.
    """
    # Convert kilometers to meters for accurate ST_Buffer metric calculation
    error_radius_meters = payload.cross_track_error_km * 1000.0
    
    # Updated to use ST_DWithin for intersection and ST_Distance for Confidence Scoring
    spatial_query = text("""
        SELECT "COUNTRY", "NAME_1",
               ST_Distance(
                   ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, 
                   geometry::geography
               ) as distance_meters
        FROM gadm_regions 
        WHERE ST_DWithin(
            geometry::geography,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, 
            :radius
        )
        ORDER BY distance_meters ASC;
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(
                spatial_query, 
                {
                    "lon": payload.longitude, 
                    "lat": payload.latitude, 
                    "radius": error_radius_meters
                }
            )
            
            # Access the result and map the rich payload with confidence calculations
            impacted_regions = []
            for row in result:
                # Linear Confidence Score: 0km = 99%, outer radius edge = 10%
                distance = row.distance_meters
                confidence = max(10.0, round(99.0 * (1.0 - (distance / error_radius_meters)), 1))
                
                impacted_regions.append({
                    "country": row.COUNTRY,
                    "province": row.NAME_1,
                    "storm_name": payload.storm_name,
                    "timestamp": payload.timestamp,
                    "wind_speed_kph": payload.wind_speed_kph,
                    "confidence_score": confidence
                })
            
        # Determine status based on spatial intersection results
        status = "ACTIVE_WARNING" if impacted_regions else "NO_IMPACT_DETECTED"
        
        # --- NEW: LOG TO SUPABASE FOR LSTM ENSEMBLE ---
        try:
            with supabase_engine.connect() as supabase_conn:
                insert_query = text("""
                    INSERT INTO seabeacon_forecasts (
                        simulation_run_id, storm_name, base_timestamp, lead_time_hours, forecast_target_time,
                        predicted_lat, predicted_lon, predicted_wind_kph,
                        warning_scope_km, alert_status, impact_matrix
                    ) VALUES (
                        :run_id, :storm_name, :base_time, :lead_time, :target_time,
                        :lat, :lon, :wind, :scope, :status, :matrix
                    )
                """)
                import json
                supabase_conn.execute(
                    insert_query,
                    {
                        "run_id": payload.simulation_run_id,
                        "storm_name": payload.storm_name,
                        "base_time": payload.base_timestamp,    # NEW
                        "lead_time": payload.lead_time_hours,   # NEW
                        "target_time": payload.timestamp,
                        "lat": payload.latitude,
                        "lon": payload.longitude,
                        "wind": payload.wind_speed_kph,
                        "scope": payload.cross_track_error_km,
                        "status": status,
                        "matrix": json.dumps(impacted_regions)
                    }
                )
                supabase_conn.commit()
        except Exception as supabase_error:
            print(f"--> [Supabase] Failed to log forecast ensemble data: {supabase_error}")
        # ------------------------------------------------
        
        return AlertResponse(
            alert_status=status,
            impacted_count=len(impacted_regions),
            impacted_regions=impacted_regions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spatial processing error: {str(e)}")

if __name__ == "__main__":
    # Run the production ASGI server locally on port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)