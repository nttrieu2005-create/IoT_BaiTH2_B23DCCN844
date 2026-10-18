"""Cau hinh va truy van InfluxDB 2.x dung chung."""
import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

load_dotenv()

def setting(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value or value.startswith("ThayBang"):
        raise RuntimeError(f"Hay dien {key} trong file .env")
    return value

def db():
    return InfluxDBClient(
        url=setting("INFLUX_URL"),
        token=setting("INFLUX_TOKEN"),
        org=setting("INFLUX_ORG"),
        timeout=10000,
    )

def query_frame(client, measurement: str, minutes: int):
    """Tra ve mot DataFrame da pivot: moi timestamp = mot hang."""
    import pandas as pd
    bucket = setting("INFLUX_BUCKET").replace('"', "")
    device = setting("DEVICE_ID").replace('"', "")
    if measurement not in ("sensor_raw", "sensor_processed"):
        raise ValueError("measurement khong hop le")
    flux = f'''from(bucket: "{bucket}")
      |> range(start: -{int(minutes)}m)
      |> filter(fn: (r) => r._measurement == "{measurement}" and r.device_id == "{device}")
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")'''
    frames = client.query_api().query_data_frame(flux)
    if isinstance(frames, list):
        frames = [f for f in frames if not f.empty]
        if not frames:
            return pd.DataFrame()
        df = pd.concat(frames, ignore_index=True)
    else:
        df = frames
    if df.empty:
        return df
    df["_time"] = pd.to_datetime(df["_time"], utc=True)
    return df.sort_values("_time").drop_duplicates("_time", keep="last")

