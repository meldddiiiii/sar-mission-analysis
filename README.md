# sar-mission-analysis
Sun-synchronous SAR Earth observation mission analysis using GMAT + Python

Hi! This is a self-initiated systems engineering capstone project simulating a sun-synchronous SAR satellite mission and analyzing ground station contact opportunities across Canada's existing downlink network.

Orbit propagation and ground track visualization were performed in GMAT (General Mission Analysis Tool). Contact report data was parsed and analyzed using Python (matplotlib, numpy).

| Parameter | Value |
| --- | --- |
| Orbit type | Sun-synchronous (SSO) |
| Semi-major axis | 6978 km |
| Inclination | 97.79° |
| Eccentricity | ~0 (circular) |
| Epoch | 01 Jan 2026 12:00:00 UTC |
| Simulation Duration | 7 days |
| Propagator | Runge-Kutta 8-9 |
| Gravity Model | JGM-2 (4×4) |

**Ground Station Network**

Three Canadian ground stations were modelled, each with a minimum elevation angle of 5°:

|Station | Latitude | Longitude |
| --- | --- | --- |
| Gatineau, QC | 45.59°N | 284.21°E |
| Prince Albert, SK | 53.21°N | 254.07°E |
| Inuvik, NT | 68.32°N | 226.45°E |

These stations mirror the CSA's (Canadian Space Agency's) RADARSAT downlink infrastructure.

**Results Summary**

| Station | Passes | Total Contact Time |
| -- | -- | -- |
| Inuvik | 72 | ~720 min |
| Prince Albert | 41 | ~370 min |
| Gatineau | 33 | ~250 min |

**Key Findings**

- **Inuvik dominates contact frequency:** its high latitude (68°N) means the polar orbit passes nearly overhead on nearly every revolution, yielding ~10 contacts per day.
- **Mean network-wide coverage gap is ~99 minutes,** roughly matching the orbital period (~94 min), indicating efficient multi-station handoff with minimal dead time.
- **Maximum coverage gap is ~396 minutes (~6.6 hours),** occurring when the spacecraft is below the horizon for all three stations simultaneously.
- **Most passes fall in the 8–10 minute range,** consistent with LEO geometry at Canadian latitudes; Inuvik skews toward longer, higher-elevation passes.
Total daily network contact time is ~170 minutes from Jan 2–7, providing a consistent downlink budget across the simulation window.
