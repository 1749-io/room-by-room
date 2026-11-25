"""Can a direct ray from a table point clear the fictional west hedge?"""

import csv
import math
from pathlib import Path


def sunlight(east_m, north_m, surface_m, hedge_height_m, azimuth_deg, elevation_deg):
    if elevation_deg <= 0:
        return "below horizon"
    azimuth = math.radians(azimuth_deg)
    towards_east = math.sin(azimuth)
    if towards_east >= -1e-12:
        return "sun"
    # Horizontal distance along the ray to x = 0, the west hedge.
    distance = east_m / -towards_east
    crossing_north = north_m + distance * math.cos(azimuth)
    crossing_height = surface_m + distance * math.tan(math.radians(elevation_deg))
    if -6 <= crossing_north <= 6 and crossing_height <= hedge_height_m:
        return "shade"
    return "sun"


def main():
    with Path(__file__).with_name("samples.csv").open(newline="") as stream:
        samples = csv.DictReader(stream)
        print("Local time                 Near 2 m    Far 2 m     Far 3 m")
        for sample in samples:
            azimuth = float(sample["azimuth_deg"])
            elevation = float(sample["apparent_elevation_deg"])
            results = [sunlight(east, 0, 0.75, height, azimuth, elevation)
                       for east, height in ((1, 2), (4, 2), (4, 3))]
            print(sample["local_time"], *[f"{result:12}" for result in results])


if __name__ == "__main__":
    main()
