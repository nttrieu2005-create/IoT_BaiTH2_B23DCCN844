"""IQR -> 10s resample -> noi suy 1 o trong -> rolling/delta/z-score."""
import argparse
import time
import numpy as np
import pandas as pd
from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from common import db, query_frame, setting

SENSORS = ["temperature", "humidity", "distance_cm"]

def clean_and_resample(raw: pd.DataFrame):
    if raw.empty:
        return pd.DataFrame(), {}
    df = raw.set_index("_time")[SENSORS].copy()
    df = df.apply(pd.to_numeric, errors="coerce").sort_index()
    counts = {}
    for col in SENSORS:
        values = df[col].dropna()
        counts[col] = 0
        if len(values) >= 8:
            q1, q3 = values.quantile([0.25, 0.75])
            iqr = q3 - q1
            mask = (df[col] < q1 - 1.5 * iqr) | (df[col] > q3 + 1.5 * iqr)
            counts[col] = int(mask.sum())
            df.loc[mask, col] = np.nan
    grid = df.resample("10s").mean()
    before = grid.isna()
    grid[SENSORS] = grid[SENSORS].interpolate(method="time", limit=1, limit_area="inside")
    grid["gap_filled"] = (before & grid[SENSORS].notna()).any(axis=1).astype(int)
    grid["temp_roll3"] = grid["temperature"].rolling(3, min_periods=1).mean()
    grid["temp_delta"] = grid["temperature"].diff()
    mean, std = grid["temperature"].mean(), grid["temperature"].std(ddof=0)
    grid["temp_z"] = ((grid["temperature"] - mean) / std
                      if std and np.isfinite(std)
                      else grid["temperature"].where(grid["temperature"].isna(), 0.0))
    return grid, counts

def run_once(client, minutes):
    raw = query_frame(client, "sensor_raw", minutes)
    grid, counts = clean_and_resample(raw)
    if grid.empty:
        print("Chua co du lieu tho trong khoang truy van.")
        return
    writer = client.write_api(write_options=SYNCHRONOUS)
    points = []
    for stamp, row in grid.iterrows():
        point = Point("sensor_processed").tag("device_id", setting("DEVICE_ID"))
        n = 0
        for key in [*SENSORS, "temp_roll3", "temp_delta", "temp_z"]:
            if pd.notna(row[key]) and np.isfinite(row[key]):
                point.field(key, float(row[key])); n += 1
        if not n:
            continue
        point.field("gap_filled", int(row["gap_filled"]))
        point.time(stamp.to_pydatetime(), WritePrecision.MS)
        points.append(point)
    if points:
        writer.write(bucket=setting("INFLUX_BUCKET"), org=setting("INFLUX_ORG"), record=points)
    writer.close()
    print(f"Raw={len(raw)}, grid={len(grid)}, saved={len(points)}, outliers={counts}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=int, default=60)
    parser.add_argument("--watch", action="store_true", help="Chay lai moi 30 giay")
    args = parser.parse_args()
    if not 1 <= args.minutes <= 10080:
        parser.error("--minutes phai tu 1 den 10080")
    with db() as client:
        while True:
            try:
                run_once(client, args.minutes)
            except Exception as exc:
                print("Processing failed:", exc)
            if not args.watch:
                break
            time.sleep(30)

