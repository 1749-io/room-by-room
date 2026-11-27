# Orchard Fold conservatory

A fictional Sussex household wants to read and eat breakfast beside its orchard every season. It will change the roof and glazing, retain both trees and keep the garden view. The brief sets an illustrative target of 18–26 °C during at least 95% of the 08:00–18:00 hours in **each** season. The room, owner, survey and decision are invented. [Explore the public case study](https://roombyroom.pages.dev/).

## Repeat the study

Download the [London Gatwick IWEC weather file](https://energyplus-weather.s3.amazonaws.com/europe_wmo_region_6/GBR/GBR_London.Gatwick.037760_IWEC/GBR_London.Gatwick.037760_IWEC.epw). Install `pvlib==0.16.1` in a Python 3.11 environment, then run `python examples/conservatory/study.py gatwick.epw results`. The script verifies the source hash. It maps the typical year onto the 2019 calendar, calculates the sun at each hour's midpoint and uses local civil time for occupancy. Results include all 8,760 hours.

[Survey](survey.json) · [Comparison results](reference/results.json) · [Hourly results](reference/hourly.csv) · [Reopened geometry](reference/geometry.json)

## What the simulation assumes

The model uses pvlib solar position and isotropic plane-of-array irradiance. Rays from the reader and each glazed face intersect simplified ellipsoidal crowns. Foliage attenuates the direct component. Diffuse and ground-reflected radiation remain unshaded. The seat ray describes the trees alone. The solid roof also shades the proposed seat. Looking west towards late low sun can still require the adjustable west screen. A real project needs an eye-level glare check, measured opening areas and an updated tree survey.

The single-zone screening model has 7 MJ/K effective capacity, fixed ground and adjoining-room temperatures of 12 and 19 °C, coupling of 32 and 18 W/K respectively, 18 W/K additional exposed losses and 150 W occupied internal gains. Wall glazing covers 86% of the 1.95 m-high band. The original roof is 87% glazed. Original glass has U=2.8 W/m²K and solar factor 0.68. The redesign uses U=1.25 and solar factor 0.40 with an opaque roof at U=0.18. The hourly solution includes a fortnight of warm-up. The comfort metric uses end-of-hour zone temperatures. No radiant asymmetry, glare rating, humidity, condensation, extreme weather or wind/rain control is solved.

Original opening gives 2.5 air changes/hour during warm occupied hours when outdoors is cooler, upgraded opposing vents give 6 and closed background leakage gives 0.65. External screens transmit 16% when incident irradiance exceeds 160 W/m² and outdoor temperature exceeds 13 °C. Screens act on vertical panes only. The original and fabric options have 1.8 kW heating and a 12 °C setback. OF-02 adds 2.8 kW available heat, a 04:00 preheat to 19 °C, and up to 1.8 kW occupied cooling above 25 °C. Reported energy is heat delivered or removed, before equipment efficiency.

The fictional owner selects OF-02 for the year-round routine, with six cold occupied hours remaining in this weather year. The result depends on controls and available heating. Confirm required airflow, HVAC sizing, surface temperatures, moisture risk and severe weather before any real specification.

## Reproduce the visual

Run the `build(root)` entry in [native_cad.py](native_cad.py) through FreeCAD MCP, then [native_scene.py](native_scene.py) in a fresh Blender session through Blender MCP. Both use [the same metre-based layout](layout.py). The directory passed as `root` contains these scripts. Open the included native models or build in a copy of the example. The camera looks towards the south-west corner from the north-east. The garden-side screens are retracted in this view. The fan coil and house doorway are behind the camera.

The [camera](reference/camera.png) was the sole input to the [AI concept](reference/concept.png). The reviewer compared the opaque roof, joists, upstand, green transoms, table with two wine glasses, two chairs, three plants by the windows and west tree against the reopened scene. The illustration refines timber, upholstery, tree branching and the meadow. Tree detail and shadows in the illustration have no measurement role. The result is a fictional design study for public demonstration.
