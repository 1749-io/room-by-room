"""Replay the fictional screening study with pvlib, numpy and pandas."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pvlib

ROOT = Path(__file__).resolve().parent
SURVEY = json.loads((ROOT / "survey.json").read_text(encoding="utf-8-sig"))
WEATHER_HASH = "c61a0a1ea127529b04380cce1e4fc88553bb7036d11127f7673d4e1e5b4edffc"
CASES = ["Original", "External screens", "Cross ventilation", "Roof and glazing", "Combined", "All-season design", "Smaller crowns", "Vents unavailable"]


def canopy(point, rays, summer, scale):
    """Intersect the forward solar ray with each surveyed crown ellipsoid."""
    transmission = np.ones(len(rays))
    for tree in SURVEY["trees"]:
        mid = (tree["top"] + tree["base"]) / 2
        radii = np.array([tree["radius"], tree["radius"], mid - tree["base"]]) * scale
        origin = (np.array(point) - [tree["east"], tree["north"], mid]) / radii
        direction = rays / radii
        a = (direction * direction).sum(axis=1)
        b = direction @ origin
        disc = b*b - a * (origin @ origin - 1)
        hit = (disc >= 0) & ((-b + np.sqrt(np.maximum(0, disc))) > 0) & (rays[:, 2] > 0)
        transmission[hit] *= np.where(summer[hit], .18, .72)
    return transmission


def study(epw, output):
    if hashlib.sha256(epw.read_bytes()).hexdigest() != WEATHER_HASH:
        raise ValueError("Use the London Gatwick IWEC weather file specified in the README")
    weather, meta = pvlib.iotools.read_epw(epw, coerce_year=2019)
    times = weather.index + pd.Timedelta(minutes=30)
    weather.index = times
    local = times.tz_convert("Europe/London")
    sun = pvlib.solarposition.get_solarposition(times, meta["latitude"], meta["longitude"])
    alt, az = np.radians(sun.apparent_elevation), np.radians(sun.azimuth)
    rays = np.column_stack((np.cos(alt)*np.sin(az), np.cos(alt)*np.cos(az), np.sin(alt)))
    leaves = np.asarray((local.month >= 5) & (local.month <= 9))
    occupied = np.asarray((local.hour >= 8) & (local.hour < 18))
    clock_hour = local.hour.to_numpy()
    outside = weather.temp_air.to_numpy()
    w, d, h = SURVEY["room_m"]
    # Representative centre ray per aperture. North wall adjoins the house.
    apertures = [(2.7,0,1.55, w*1.95*.86,90,180), (0,1.8,1.55,d*1.95*.86,90,270),
                 (w,1.8,1.55,d*1.95*.86,90,90), (2.7,1.8,h,w*d*.87,0,180)]
    frame = pd.DataFrame({"local_time":local.astype(str), "occupied":occupied, "outside_C":outside,
                          "sun_azimuth_deg":np.degrees(az).to_numpy(),
                          "sun_altitude_deg":np.degrees(alt).to_numpy(),
                          "seat_beam_transmission":canopy(SURVEY["seat_eye_m"],rays,leaves,1)})
    summary = {}
    for case in CASES:
        combined = case in ("Combined","All-season design","Smaller crowns","Vents unavailable")
        insulated = combined or case == "Roof and glazing"
        shading = combined or case == "External screens"
        vents = case in ("Combined","All-season design","Smaller crowns","Cross ventilation")
        gain = np.zeros(len(times))
        glass = 0
        for x,y,z,area,tilt,bearing in apertures:
            if insulated and tilt == 0:
                continue
            solar = pvlib.irradiance.get_total_irradiance(tilt,bearing,90-np.degrees(alt),
                np.degrees(az),weather.dni,weather.ghi,weather.dhi)
            factor = canopy((x,y,z),rays,leaves,.65 if case == "Smaller crowns" else 1)
            flux = solar.poa_direct.to_numpy()*factor + solar.poa_diffuse.to_numpy()
            screen = np.where((flux>160) & (outside>13) & (tilt>0) & shading,.16,1)
            gain += area*(.40 if insulated else .68)*flux*screen
            glass += area
        ua = glass*(1.25 if insulated else 2.8) + (w*d if insulated else 0)*.18 + 18
        # Lumped thermal capacity 7 MJ/K. Exact one-hour constant-load solution.
        t = 18.
        temperatures, heating, cooling = [], [], []
        for i in [*range(len(times)-336,len(times)),*range(len(times))]:
            ach = .65
            if occupied[i] and t > 22 and outside[i] < t and case != "Vents unavailable":
                ach = 6 if vents else 2.5
            external = ua + .33*w*d*h*ach
            loss = external + 32 + 18
            decay = np.exp(-3600*loss/7e6)
            free = (external*outside[i] + 32*12 + 18*19 + gain[i]+(150 if occupied[i] else 0))/loss
            end = free+(t-free)*decay
            conditioned = case in ("All-season design","Smaller crowns","Vents unavailable")
            warmup = conditioned and 4 <= clock_hour[i] < 8
            setting = 19 if occupied[i] or warmup else 12
            power = min(2800 if conditioned else 1800, max(0,(setting-end)*loss/(1-decay)))
            cool = min(1800, max(0,(end-25)*loss/(1-decay))) if conditioned and occupied[i] else 0
            t = end+(power-cool)*(1-decay)/loss
            cooling.append(cool)
            temperatures.append(t)
            heating.append(power)
        temps = np.array(temperatures[-len(times):])
        frame[case] = temps.round(3)
        seasons = {}
        for name,months in {"Winter":[12,1,2],"Spring":[3,4,5],"Summer":[6,7,8],"Autumn":[9,10,11]}.items():
            select = occupied & np.isin(local.month,months)
            seasons[name] = round(100*np.mean((temps[select]>=18)&(temps[select]<=26)),1)
        summary[case] = {"hot_hours":int(np.sum(occupied&(temps>26))),
                         "cold_hours":int(np.sum(occupied&(temps<18))),
                         "peak_C":round(float(temps[occupied].max()),1),
                         "cooling_kWh":round(sum(cooling[-len(times):])/1000),
                         "heating_kWh":round(sum(heating[-len(times):])/1000),
                         "in_band_pct":seasons}
    output.mkdir(exist_ok=True)
    frame.to_csv(output/"hourly.csv",index=False)
    (output/"results.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("epw", type=Path)
    p.add_argument("output", type=Path)
    args=p.parse_args()
    study(args.epw,args.output)


