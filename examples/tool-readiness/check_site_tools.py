"""Exercise a QGIS raster, or a bundled EnergyPlus weather run, in a temporary folder."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile


def check_qgis(executable, folder):
    raster = folder / "surface.asc"
    raster.write_text("ncols 3\nnrows 2\nxllcorner -1.53\nyllcorner 52\ncellsize 0.01\n"
                      "NODATA_value -9999\n100 102 100\n100 100 103\n", encoding="ascii")
    raster.with_suffix(".prj").write_text(
        'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],'
        'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4326"]]',
        encoding="ascii")
    points = folder / "observations.geojson"
    locations = {"low": [-1.515, 52.015], "high": [-1.505, 52.005]}
    features = [{"type": "Feature", "properties": {"hedge": name},
                 "geometry": {"type": "Point", "coordinates": point}}
                for name, point in locations.items()]
    points.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    output = folder / "sampled.geojson"
    subprocess.run([executable, "run", "native:rastersampling", "--", f"INPUT={points}",
                    f"RASTERCOPY={raster}", "COLUMN_PREFIX=surface_", f"OUTPUT={output}"],
                   check=True, cwd=folder, env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
    sampled = json.loads(output.read_text(encoding="utf-8"))["features"]
    heights = {f["properties"]["hedge"]: f["properties"]["surface_1"] - 100 for f in sampled}
    if len(sampled) != 2 or heights != {"low": 2, "high": 3}:
        raise ValueError(f"Unexpected hedge heights above the 100 m datum: {heights}")
    print("QGIS sampled the fictional hedges at 2 m and 3 m above the terrain.")


def check_energyplus(executable, folder):
    root = Path(executable).resolve().parent
    source = root / "ExampleFiles" / "1ZoneUncontrolled.idf"
    weather = root / "WeatherData" / "USA_CO_Golden-NREL.724666_TMY3.epw"
    model = folder / source.name
    model.write_bytes(source.read_bytes() + b"\nOutput:SQLite,Simple;\n")
    subprocess.run([executable, "--annual", "-w", str(weather), "-d", str(folder), str(model)],
                   check=True, cwd=folder)
    summary = (folder / "eplusout.end").read_text().strip()
    if "Completed Successfully" not in summary or " 0 Warning" not in summary or " 0 Severe Errors" not in summary:
        raise ValueError(summary)
    sql = """
        SELECT COUNT(r.Value), MIN(r.Value), MAX(r.Value)
        FROM ReportData r JOIN ReportDataDictionary d USING (ReportDataDictionaryIndex)
        JOIN Time t USING (TimeIndex) JOIN EnvironmentPeriods ep USING (EnvironmentPeriodIndex)
        WHERE d.Name = 'Zone Mean Air Temperature'
        AND d.ReportingFrequency = 'Hourly' AND ep.EnvironmentType = 3
    """
    with closing(sqlite3.connect(folder / "eplusout.sql")) as conn:
        count, coldest, warmest = conn.execute(sql).fetchone()
    if count != 8760 or coldest >= warmest:
        raise ValueError(f"Unexpected annual series: {count}, {coldest}, {warmest}")
    print(f"{summary}\n{count} hourly temperatures, {coldest:.2f} to {warmest:.2f} degrees C.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool", choices=("qgis", "energyplus"))
    parser.add_argument("--executable", help="Full executable path when outside PATH")
    args = parser.parse_args()
    command = "qgis_process" if args.tool == "qgis" else "energyplus"
    exe = shutil.which(args.executable or command)
    if exe is None:
        parser.error(f"Cannot find {command}. Supply --executable with its full path.")
    with tempfile.TemporaryDirectory(prefix="renovation-site-") as work:
        (check_qgis if args.tool == "qgis" else check_energyplus)(exe, Path(work))
