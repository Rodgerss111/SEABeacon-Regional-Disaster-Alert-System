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
    storm_name: str = Field(..., description="Name of the typhoon", json_schema_extra={"example": "Super Typhoon Kalmaegi"})
    timestamp: str = Field(..., description="Forecast valid time", json_schema_extra={"example": "2026-06-17T18:00:00Z"})
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