# Top of File
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch
from datetime import datetime
from pathlib import Path

report_path = Path.home() /"Desktop" / "MDA_Capstone" / "ContactReport.txt" # Update this path to where my ContactReport.txt is located
text = report_path.read_text()

lines = text.splitlines()

current_station = None

contacts = [] 

for line in lines: # Loop through each line in the report

    if not line.strip():
        continue

    if line.startswith("Observer:"): # Check if the line starts with "Observer:", which indicates a new station
        station = line.split(":", 1)[1].strip()
        print(f"Found Station: {station}")
        current_station = station
        continue

    if line.strip()[0].isdigit(): # Check if the line starts with a digit, which indicates a contact entry
        tokens = line.split()
        contacts.append({
           "station": current_station,
           "start": datetime.strptime(" ".join(tokens[0:4]), "%d %b %Y %H:%M:%S.%f"),
           "stop": datetime.strptime(" ".join(tokens[4:8]), "%d %b %Y %H:%M:%S.%f"),
           "duration": float(tokens[8]),
        })

print(contacts[0])

# Get Unique Stations
stations = set(c["station"] for c in contacts)

# Loop through each station and calculate contact statistics
for station in stations:
    station_contacts = [c for c in contacts if c["station"] == station]

    # Calculate Durations
    durations = [c["duration"] for c in station_contacts]

    total_minutes = sum(durations)/60  # Convert seconds to minutes

    avg_min = total_minutes / len(durations) if durations else 0
    
    print(f"{station}: {len(station_contacts)} contacts, "
          f"{total_minutes:.1f} total minutes, "
          f"{avg_min:.1f} min/pass average")
    

#Daily Contact Time Bar Graph

daily_totals = {} 

for c in contacts: # Loop through each contact to calculate daily totals
    date = c["start"].strftime("%d %b %Y")
    station = c["station"]
    key = (date, station)
    duration_min = c["duration"] / 60  # Convert seconds to minutes

    if key  in daily_totals:
        daily_totals[key] += duration_min
    else:
        daily_totals[key] = duration_min

for key, value in daily_totals.items(): # Print the daily totals for each station
    print(f"{key}: {value:.1f} minutes")

dates = sorted({key[0] for key in daily_totals})

print(dates)

gatineau_values = [daily_totals[(date, "Gatineau")] for date in dates]
print(gatineau_values)

inuvik_values = [daily_totals[(date, "Inuvik")] for date in dates]
print(inuvik_values)

prince_albert_values = [daily_totals[(date, "Prince_Albert")] for date in dates]
print(prince_albert_values)

day_labels = [date.split()[0] for date in dates]

#Create a stacked bar graph to show daily contact time for each station
fig, ax = plt.subplots(figsize = (13, 6))
ax.bar(day_labels, gatineau_values)
ax.bar(day_labels, inuvik_values, bottom=gatineau_values)
ax.bar(day_labels, prince_albert_values, bottom=[gatineau_values[i] + inuvik_values[i] for i in range(len(day_labels))])
ax.set_xlabel("Date")
ax.set_ylabel("Total Contact Time (minutes)")
ax.set_title("Daily Contact Time per Ground Station (Januray 2026)")
ax.legend(["Gatineau", "Inuvik", "Prince Albert"])
plt.xticks(rotation = 45, ha="right")
plt.savefig("plots/daily_contact_time.png", dpi = 150)
plt.show()

#Pass Duration Histogram

gatineau_durations = [c["duration"] / 60 for c in contacts if c["station"] == "Gatineau"]
inuvik_durations = [c["duration"] / 60 for c in contacts if c["station"] == "Inuvik"]
prince_albert_durations = [c["duration"] / 60 for c in contacts if c["station"] == "Prince_Albert"]

print(f"Gatineau: {len(gatineau_durations)} durations")
print(f"Inuvik: {len(inuvik_durations)} durations")
print(f"Prince_Albert: {len(prince_albert_durations)} durations")

#Create a histogram to show the distribution of pass durations for each station
fig, ax = plt.subplots(figsize = (13, 6))
ax.hist(gatineau_durations, bins = 15, alpha = 0.5, label = "Gatineau")
ax.hist(inuvik_durations, bins = 15, alpha = 0.5, label = "Inuvik")
ax.hist(prince_albert_durations, bins = 15, alpha = 0.5, label = "Prince Albert")
ax.set_xlabel("Pass duration (minutes)")
ax.set_ylabel("Number of Passes")
ax.set_title("Distribution of Pass Durations by Ground Station")
ax.legend()

plt.savefig("plots/pass_duration_histogram.png", dpi = 150)
plt.show()

#Contact Timeline (Gantt Chart)
fig, ax = plt.subplots(figsize = (13, 6))

stations = ["Gatineau", "Inuvik", "Prince_Albert"]
station_colours = {
    "Gatineau": "#1f77b4",      
    "Inuvik": "#ff7f0e",        
    "Prince_Albert": "#2ca02c", 
}

for c in contacts: # Loop through each contact and create a horizontal bar for the contact duration
    y = stations.index(c["station"])
    width = c["stop"] - c["start"]
    ax.barh(y, width, left=c["start"], height=0.6, color=station_colours[c["station"]])

ax.set_yticks([0, 1, 2])
ax.set_yticklabels(["Gatineau", "Inuvik", "Prince Albert"])
ax.set_xlabel("Date (UTC)")
ax.set_title("Contact Timeline - 7-day Mission Simulation")

legend_patches = [
    Patch(color=station_colours["Gatineau"], label="Gatineau"),
    Patch(color=station_colours["Inuvik"], label="Inuvik"),
    Patch(color=station_colours["Prince_Albert"], label="Prince Albert"),
]
ax.legend(handles=legend_patches, loc="upper right")

plt.savefig("plots/contact_timeline.png", dpi = 150)
plt.show()

#Coverage Gap Analysis
sorted_contacts = sorted(contacts, key=lambda c: c["start"])
print(f"First contact: {sorted_contacts[0]['start']}")
print(f"Last contact: {sorted_contacts[-1]['start']}")

gaps_minutes = []

for i in range(1, len(sorted_contacts)):
    previous_stop = sorted_contacts[i - 1]["stop"]
    current_start = sorted_contacts[i]["start"]
    gap = current_start - previous_stop
    gap_min = gap.total_seconds() / 60
    if gap_min > 0:
        gaps_minutes.append(gap_min)

print(f"Number of gaps: {len(gaps_minutes)}")
print(f"First 10 gaps: {gaps_minutes[:10]}")

fig, ax = plt.subplots(figsize=(11, 6))
ax.hist(gaps_minutes, bins=30, color="#2E86AB", edgecolor="black")
ax.set_xlabel("Gap between contacts (minutes)")
ax.set_ylabel("Number of gaps")
ax.set_title("Network-wide Coverage Gaps")

mean_gap = np.mean(gaps_minutes) #average minutes of list
max_gap = np.max(gaps_minutes) #max minute of list

ax.axvline(mean_gap, color="red", linestyle="--", label=f"Mean: {mean_gap:.1f} min")
ax.axvline(max_gap, color="darkred", linestyle="--", label=f"Max: {max_gap:.1f} min")
ax.legend()

plt.savefig("plots/gap_analysis.png", dpi=150)
plt.show()