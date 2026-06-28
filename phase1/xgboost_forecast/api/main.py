import os
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

app = FastAPI(title="SEABeacon Spatial API")

SUPABASE_URL = "postgresql://postgres.axigjjehzqghflrvewaj:loGiwer21Glw@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"
engine = create_engine(SUPABASE_URL)

class ImpactedRegion(BaseModel):
    country: str
    province: str
    storm_name: str
    timestamp: str
    wind_speed_kph: float
    confidence_score: float

class PredictionPayload(BaseModel):
    simulation_run_id: str = Field(default="live-run")
    storm_name: str
    base_timestamp: Optional[str] = None
    lead_time_hours: Optional[int] = None
    timestamp: str
    latitude: float
    longitude: float
    cross_track_error_km: float
    wind_speed_kph: float

class AlertResponse(BaseModel):
    alert_status: str
    impacted_count: int
    impacted_regions: List[ImpactedRegion]

@app.get("/health")
def health_check():
    return {"status": "online", "database": "supabase"}

@app.post("/api/v1/spatial-conversion", response_model=AlertResponse)
async def spatial_conversion(payload: PredictionPayload):
    error_radius_meters = payload.cross_track_error_km * 1000.0
    
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
                {"lon": payload.longitude, "lat": payload.latitude, "radius": error_radius_meters}
            )
            
            impacted_regions = []
            for row in result:
                distance = row.distance_meters
                confidence = max(10.0, round(99.0 * (1.0 - (distance / error_radius_meters)), 1))
                
                impacted_regions.append({
                    "country": row.COUNTRY, "province": row.NAME_1,
                    "storm_name": payload.storm_name, "timestamp": payload.timestamp,
                    "wind_speed_kph": payload.wind_speed_kph, "confidence_score": confidence
                })
            
        status = "ACTIVE_WARNING" if impacted_regions else "NO_IMPACT_DETECTED"
        
        with engine.connect() as conn:
            insert_query = text("""
                INSERT INTO seabeacon_forecasts (
                    simulation_run_id, storm_name, forecast_target_time,
                    predicted_lat, predicted_lon, predicted_wind_kph,
                    warning_scope_km, alert_status, impact_matrix,
                    base_timestamp, lead_time_hours
                ) VALUES (
                    :run_id, :storm_name, :target_time,
                    :lat, :lon, :wind, :scope, :status, :matrix,
                    :base_time, :lead_time
                )
            """)
            conn.execute(
                insert_query,
                {
                    "run_id": payload.simulation_run_id, "storm_name": payload.storm_name,
                    "target_time": payload.timestamp, "lat": payload.latitude,
                    "lon": payload.longitude, "wind": payload.wind_speed_kph,
                    "scope": payload.cross_track_error_km, "status": status,
                    "matrix": json.dumps(impacted_regions),
                    "base_time": payload.base_timestamp, "lead_time": payload.lead_time_hours
                }
            )
            conn.commit()
        
        return AlertResponse(
            alert_status=status, impacted_count=len(impacted_regions),
            impacted_regions=impacted_regions
        )
        
    except Exception as e:
        print(f"Spatial Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")