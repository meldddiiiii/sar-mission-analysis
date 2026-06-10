import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Mission Parameters
FREQ_HZ       = 9.6e9           # X-band frequency (9.6 GHz)
SPEED_LIGHT   = 3e8             # m/s
TX_POWER_W    = 20              # Satellite transmit power (watts)
TX_POWER_DB   = 10 * np.log10(TX_POWER_W)
TX_GAIN_DB    = 10              # Satellite antenna gain (dBi)
RX_GAIN_DB    = 45              # Ground station dish gain (dBi)
LOSSES_DB     = 2               # Atmospheric + pointing losses (dB)
DATA_RATE_BPS = 300e6           # 300 Mbps
NOISE_TEMP_K  = 135             # System noise temperature (Kelvin)
BOLTZMANN     = 1.38e-23        # Boltzmann's constant
REQUIRED_EBN0 = 14.0            # Minimum Eb/N0 for QPSK (dB)
LINK_MARGIN_THRESHOLD = 3.0     # dB safety buffer
H_ORBIT       = 600.0           # km, orbital altitude

MISSION_START = datetime(2026, 1, 1, 12, 0, 0)

# GST calibrated empirically to match ContactReport timing
GST_AT_START = (100.4 + 360.9856 * (1.0/365.25) * (31 + (12/24)) - 97.5) % 360

# Load satellite position data from GMAT 
pos = pd.read_csv(
    '/Users/melodie/Desktop/SAR_Mission_Analysis/PositionReport.txt',
    sep=r'\s+',
    skiprows=1,
    names=['elapsed_sec', 'x_km', 'y_km', 'z_km']
)
print(f"Total timesteps: {len(pos)}")
print(f"Total duration:  {pos['elapsed_sec'].max() / 3600:.1f} hours")

# Ground station coordinates 
stations = {
    'Inuvik':        {'lat': 68.3195, 'lon': 226.4505, 'alt_km': 0.102},
    'Prince_Albert': {'lat': 53.2124, 'lon': 254.0686, 'alt_km': 0.490},
    'Gatineau':      {'lat': 45.5853, 'lon': 284.2127, 'alt_km': 0.240},
}

R_earth = 6378.137        # km
earth_rot_rate = 360.0 / 86400.0 # degrees per second

def latlon_to_xyz(lat_deg, lon_deg, alt_km):
    lat = np.radians(lat_deg)
    lon = np.radians(lon_deg + GST_AT_START)
    r   = R_earth + alt_km
    x   = r * np.cos(lat) * np.cos(lon)
    y   = r * np.cos(lat) * np.sin(lon)
    z   = r * np.sin(lat)
    return np.array([x, y, z])

def rotate_z(xyz, angle_deg):
    angle = np.radians(angle_deg)
    x_new = xyz[0] * np.cos(angle) - xyz[1] * np.sin(angle)
    y_new = xyz[0] * np.sin(angle) + xyz[1] * np.cos(angle)
    return np.array([x_new, y_new, xyz[2]])

def compute_elevation(sat_xyz, gs_xyz):
    vec    = sat_xyz - gs_xyz
    up     = gs_xyz / np.linalg.norm(gs_xyz)
    sin_el = np.dot(vec, up) / np.linalg.norm(vec)
    return np.degrees(np.arcsin(np.clip(sin_el, -1, 1)))

# Pre-compute base XYZ for each station at t=0
for name, gs in stations.items():
    gs['xyz_base'] = latlon_to_xyz(gs['lat'], gs['lon'], gs['alt_km'])

# Compute elevation angles for all timesteps 
sat_xyz_all  = pos[['x_km', 'y_km', 'z_km']].values
elapsed_secs = pos['elapsed_sec'].values

for name, gs in stations.items():
    elevations = []
    for i, sat_xyz in enumerate(sat_xyz_all):
        angle          = earth_rot_rate * elapsed_secs[i]
        gs_xyz_rotated = rotate_z(gs['xyz_base'], angle)
        el             = compute_elevation(sat_xyz, gs_xyz_rotated)
        elevations.append(el)
    gs['elevations'] = np.array(elevations)

# Link budget functions 
def free_space_path_loss(slant_range_km):
    slant_range_m = slant_range_km * 1000
    return 20 * np.log10(4 * np.pi * slant_range_m * FREQ_HZ / SPEED_LIGHT)

def received_power(fspl_db):
    return TX_POWER_DB + TX_GAIN_DB - fspl_db - LOSSES_DB + RX_GAIN_DB

def calc_ebn0(pr_db):
    return pr_db - 10*np.log10(BOLTZMANN) - 10*np.log10(NOISE_TEMP_K) - 10*np.log10(DATA_RATE_BPS)

def link_margin(ebn0_db):
    return ebn0_db - REQUIRED_EBN0

# Parse ContactReport 
def parse_contact_report(filepath):
    passes          = []
    current_station = None
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('Observer:'):
                current_station = line.split(':')[1].strip()
            if not line or 'Start Time' in line or 'Number' in line or 'Target' in line:
                continue
            parts = line.split()
            if len(parts) >= 8:
                try:
                    start_str = ' '.join(parts[0:4])
                    stop_str  = ' '.join(parts[4:8])
                    duration  = float(parts[8])
                    start_dt  = datetime.strptime(start_str, '%d %b %Y %H:%M:%S.%f')
                    stop_dt   = datetime.strptime(stop_str,  '%d %b %Y %H:%M:%S.%f')
                    start_sec = (start_dt - MISSION_START).total_seconds()
                    stop_sec  = (stop_dt  - MISSION_START).total_seconds()
                    passes.append({
                        'station':   current_station,
                        'start_sec': start_sec,
                        'stop_sec':  stop_sec,
                        'duration':  duration
                    })
                except Exception as e:
                    continue
    return passes

passes = parse_contact_report('/Users/melodie/Desktop/SAR_Mission_Analysis/data/ContactReport.txt')
print(f"Total passes loaded: {len(passes)}")

# Link budget per pass
results = []
dt = 10.0  # seconds per timestep

for p in passes:
    duration = p['duration']
    
    # Estimate max elevation from pass duration
    # Longer passes = higher max elevation
    # For a 600km SSO orbit, max duration ~614s corresponds to ~90° elevation
    max_el_deg = min(90.0, 8.0 + (duration / 614.0) * 82.0)
    
    # Model elevation across the pass as a sine curve
    n_steps = int(duration / dt)
    if n_steps == 0:
        continue
    
    t = np.linspace(0, np.pi, n_steps)
    el_profile = max_el_deg * np.sin(t)
    
    # Only use timesteps above 5 degrees
    vis = el_profile > 5
    if vis.sum() == 0:
        continue
    
    el_vis = el_profile[vis]
    sr_vis = H_ORBIT / np.sin(np.radians(el_vis))
    lm     = link_margin(calc_ebn0(received_power(free_space_path_loss(sr_vis))))

    usable_mask    = lm > LINK_MARGIN_THRESHOLD
    usable_seconds = float(usable_mask.sum() * dt)
    data_gb        = usable_seconds * 0.3

    results.append({
        'station':        p['station'],
        'start_sec':      p['start_sec'],
        'duration_sec':   duration,
        'max_el_deg':     max_el_deg,
        'usable_sec':     usable_seconds,
        'mean_margin_db': float(lm[usable_mask].mean()) if usable_mask.sum() > 0 else 0,
        'data_gb':        data_gb
    })

# Summary statistics 
df = pd.DataFrame(results)
print("\nSummary per Station:")
for station in ['Inuvik', 'Prince_Albert', 'Gatineau']:
    s = df[df['station'] == station]
    print(f"{station}:")
    print(f"  Passes analysed:    {len(s)}")
    print(f"  Total usable sec:   {s['usable_sec'].sum():.0f} s")
    print(f"  Total data:         {s['data_gb'].sum():.1f} Gb")
    print(f"  Avg data per pass:  {s['data_gb'].mean():.1f} Gb")

print(f"\nTotal data downlinked (all stations, 7 days): {df['data_gb'].sum():.1f} Gb")

#plots

plt.figure(figsize=(12, 4))

#plot 1 Data volume per station
plt.subplot(1, 3, 1)

stations = ["Gatineau", "Inuvik", "Prince_Albert"]
station_colours = {
    "Gatineau": "#1f77b4",      
    "Inuvik": "#ff7f0e",        
    "Prince_Albert": "#2ca02c", 
}

station_data = df.groupby('station')['data_gb'].sum()

bar_colours = [station_colours[s] for s in station_data.index]
plt.bar(station_data.index, station_data.values, color=bar_colours)

plt.title('Total Data Volume per Station')
plt.xlabel('Ground Station')
plt.ylabel('Data Volume (Gb)')

#plot 2
plt.subplot(1, 3, 2)

plt.scatter(
    df['duration_sec'],
    df['usable_sec'],
    c=df['station'].map(station_colours)
)

plt.title('Pass Duration vs Usable Time')
plt.xlabel('Pass Duration (s)')
plt.ylabel('Usable Time (s)')

#plot 3
plt.subplot(1, 3, 3)

plt.scatter(df['start_sec'] / 3600, df['data_gb'], c=df['station'].map(station_colours))

plt.title('Data Volume Per Pass Over Time')
plt.xlabel('Time (hrs)')
plt.ylabel('Data Volume (Gb)')

#plot summary text
plt.tight_layout(rect=[0, 0.15, 1, 1])

plt.figtext(0.17, 0.02, "Inuvik dominates due to its polar proximity,\nyielding the most passes and highest data volume.", 
            ha='center', fontsize=8, wrap=True)

plt.figtext(0.5, 0.02, "Longer passes yield proportionally more usable time.\nShort passes (<250s) fail to close the link.", 
            ha='center', fontsize=8, wrap=True)

plt.figtext(0.83, 0.02, "Data volume is consistent across all 7 days.\nZero-data points represent marginal horizon passes.", 
            ha='center', fontsize=8, wrap=True)

plt.savefig('/Users/melodie/Desktop/SAR_Mission_Analysis/link_budget_results.png', dpi=150)
plt.show()