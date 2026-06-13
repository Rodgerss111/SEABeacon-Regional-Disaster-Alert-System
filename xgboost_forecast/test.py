import matplotlib.pyplot as plt
import numpy as np

# =============================================
# SCENARIO: Your typhoon near Vietnam
# =============================================
# Forecasted track: from (15.0°N, 108.0°E) at t to (17.0°N, 109.0°E) at t+6
forecast_start = (108.0, 15.0)   # (lon, lat)
forecast_end   = (109.0, 17.0)

# Actual observed position at t+6
actual_observed = (108.5, 16.0)

# =============================================
# COMPUTE CROSS-TRACK ERROR
# =============================================
def haversine_distance(lon1, lat1, lon2, lat2):
    """Distance in km between two points on Earth."""
    R = 6371.0
    dlon = np.radians(lon2 - lon1)
    dlat = np.radians(lat2 - lat1)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

def cross_track_distance(lon1, lat1, lon2, lat2, lon_obs, lat_obs):
    """
    Cross-track distance: perpendicular distance from observed point to the track line.
    """
    R = 6371.0
    
    # Convert to radians
    lat1, lon1 = np.radians(lat1), np.radians(lon1)
    lat2, lon2 = np.radians(lat2), np.radians(lon2)
    lat_obs, lon_obs = np.radians(lat_obs), np.radians(lon_obs)
    
    # Angular distance from track start to observed point
    d13 = np.arccos(np.sin(lat1)*np.sin(lat_obs) + 
                    np.cos(lat1)*np.cos(lat_obs)*np.cos(lon_obs - lon1))
    
    # Bearing from track start to observed point
    bearing_13 = np.arctan2(np.sin(lon_obs - lon1)*np.cos(lat_obs),
                            np.cos(lat1)*np.sin(lat_obs) - 
                            np.sin(lat1)*np.cos(lat_obs)*np.cos(lon_obs - lon1))
    
    # Bearing from track start to track end
    bearing_12 = np.arctan2(np.sin(lon2 - lon1)*np.cos(lat2),
                            np.cos(lat1)*np.sin(lat2) - 
                            np.sin(lat1)*np.cos(lat2)*np.cos(lon2 - lon1))
    
    # Cross-track distance
    cte_rad = np.arcsin(np.sin(d13) * np.sin(bearing_13 - bearing_12))
    return abs(cte_rad * R)

# =============================================
# COMPUTE ERROR VALUES
# =============================================
cte = cross_track_distance(*forecast_start, *forecast_end, *actual_observed)
direct_error = haversine_distance(*forecast_end, *actual_observed)

# Compute perpendicular foot point on track line for drawing
t = 0.5  # Simplified — approximate foot at midpoint for visualization
foot_lon = forecast_start[0] + t * (forecast_end[0] - forecast_start[0])
foot_lat = forecast_start[1] + t * (forecast_end[1] - forecast_start[1])

# =============================================
# CREATE THE VISUALIZATION
# =============================================
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# ----- LEFT PANEL: Geographic View -----
ax1 = axes[0]
ax1.set_title("Cross-Track Error: Geographic View\n(Typhoon Near Vietnam Coast)", 
              fontsize=13, fontweight='bold')

# Draw Vietnam coastline (simplified)
vietnam_coast_lon = [108.0, 108.2, 108.4, 108.6, 108.8, 109.0, 109.2, 109.4]
vietnam_coast_lat = [15.0, 15.3, 15.7, 16.0, 16.4, 16.8, 17.2, 17.5]
ax1.fill_between(vietnam_coast_lon, [14.5]*8, vietnam_coast_lat, 
                  color='burlywood', alpha=0.5, label='Vietnam Coastline')
ax1.plot(vietnam_coast_lon, vietnam_coast_lat, 'k-', linewidth=2, label='_Coastline')

# Forecast track line
ax1.plot([forecast_start[0], forecast_end[0]], 
         [forecast_start[1], forecast_end[1]], 
         'b--', linewidth=3, label='Forecasted Track', zorder=4)
ax1.scatter(*forecast_start, c='blue', s=150, marker='o', 
            edgecolors='darkblue', linewidths=2, zorder=5, label='Storm at t (forecast start)')
ax1.scatter(*forecast_end, c='dodgerblue', s=200, marker='s', 
            edgecolors='darkblue', linewidths=2, zorder=5, label='Predicted at t+6')

# Actual observed position
ax1.scatter(*actual_observed, c='red', s=200, marker='X', 
            edgecolors='darkred', linewidths=3, zorder=6, label='Actual Observed at t+6')

# Dashed line for cross-track error (perpendicular)
ax1.plot([actual_observed[0], foot_lon], 
         [actual_observed[1], foot_lat], 
         'r--', linewidth=2.5, alpha=0.8, zorder=3)
ax1.annotate(f'{cte:.0f} km', 
             xy=((actual_observed[0]+foot_lon)/2, (actual_observed[1]+foot_lat)/2),
             fontsize=11, color='darkred', fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

# Direct error line (not perpendicular)
ax1.plot([actual_observed[0], forecast_end[0]], 
         [actual_observed[1], forecast_end[1]], 
         'gray', linestyle=':', linewidth=1.5, alpha=0.5)
mid_direct = ((actual_observed[0]+forecast_end[0])/2, (actual_observed[1]+forecast_end[1])/2)
ax1.annotate(f'Direct: {direct_error:.0f} km', xy=mid_direct, fontsize=9, color='gray')

ax1.set_xlabel('Longitude (°E)', fontsize=11)
ax1.set_ylabel('Latitude (°N)', fontsize=11)
ax1.legend(loc='upper left', fontsize=9)
ax1.grid(True, alpha=0.3)
ax1.set_xlim(107.5, 110.0)
ax1.set_ylim(14.5, 18.0)

# ----- RIGHT PANEL: Geometric Diagram -----
ax2 = axes[1]
ax2.set_title("Cross-Track Error: Geometric Diagram\n(Perpendicular Distance to Track Line)", 
              fontsize=13, fontweight='bold')

# Define coordinates for geometric diagram
A = (0, 0)        # Track start (t)
B = (6, 4)        # Track end (predicted t+6)
P = (3, 0.5)      # Actual observed (off the line)

# Draw the track line
ax2.plot([A[0], B[0]], [A[1], B[1]], 'b-', linewidth=4, label='Forecast Track Line', zorder=2)
ax2.scatter(*A, c='blue', s=150, zorder=3, label='t (forecast start)')
ax2.scatter(*B, c='dodgerblue', s=150, marker='s', zorder=3, label='Predicted t+6')

# Draw the actual position
ax2.scatter(*P, c='red', s=200, marker='X', zorder=4, label='Actual Observed t+6')

# Project P onto line AB to find perpendicular foot
def project_point_onto_line(A, B, P):
    AB = np.array([B[0]-A[0], B[1]-A[1]])
    AP = np.array([P[0]-A[0], P[1]-A[1]])
    t = np.dot(AP, AB) / np.dot(AB, AB)
    foot = np.array(A) + t * AB
    return tuple(foot)

foot = project_point_onto_line(A, B, P)

# Draw cross-track error (perpendicular from P to foot)
ax2.plot([P[0], foot[0]], [P[1], foot[1]], 'r-', linewidth=4, 
         label=f'Cross-Track Error', zorder=5)
ax2.scatter(*foot, c='green', s=100, marker='o', zorder=6, label='Perpendicular Foot Point')

# Right angle marker at foot point
size = 0.3
ax2.plot([foot[0], foot[0]-size], [foot[1], foot[1]-size], 'k-', linewidth=1)
ax2.plot([foot[0]-size, foot[0]-size], [foot[1]-size, foot[1]], 'k-', linewidth=1)

# Draw direct error (P to B) for comparison
ax2.plot([P[0], B[0]], [P[1], B[1]], 'gray', linestyle=':', linewidth=2, 
         alpha=0.6, label='Direct Error (not perpendicular)')

# Annotations
ax2.annotate('Cross-Track\n(⊥ distance)', xy=((P[0]+foot[0])/2, (P[1]+foot[1])/2),
             fontsize=10, color='darkred', fontweight='bold', ha='center',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='mistyrose', alpha=0.9))
ax2.annotate('Along-Track\n(timing error)', xy=(foot[0]+1.2, foot[1]+0.4),
             fontsize=10, color='green', fontweight='bold',
             arrowprops=dict(arrowstyle='->', color='green', lw=2))

ax2.set_xlabel('Longitude →', fontsize=11)
ax2.set_ylabel('Latitude →', fontsize=11)
ax2.legend(loc='upper left', fontsize=9)
ax2.grid(True, alpha=0.3)
ax2.set_xlim(-1, 7.5)
ax2.set_ylim(-1, 5)
ax2.set_aspect('equal')

plt.tight_layout()
plt.show()

print(f"Cross-Track Error: {cte:.1f} km")
print(f"Direct Haversine Error: {direct_error:.1f} km")
print(f"Difference: {direct_error - cte:.1f} km (the along-track component)")