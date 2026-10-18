"""Kiem tra cau truc, kieu va mien vat ly truoc khi ghi du lieu."""
import json
import math
import time

def parse_payload(raw: bytes, expected_device: str):
    obj = json.loads(raw.decode("utf-8"))
    if not isinstance(obj, dict) or obj.get("device_id") != expected_device:
        raise ValueError("device_id khong khop")
    boot = obj.get("boot_id")
    if not isinstance(boot, str) or not (1 <= len(boot) <= 32):
        raise ValueError("boot_id thieu hoac sai")
    for key in ("sequence", "sent_at_ms", "uptime_s"):
        if isinstance(obj.get(key), bool) or not isinstance(obj.get(key), int):
            raise ValueError(f"{key} phai la so nguyen")
    if obj["sequence"] < 1 or obj["uptime_s"] < 0:
        raise ValueError("sequence/uptime am")
    now_ms = time.time_ns() // 1_000_000
    if abs(now_ms - obj["sent_at_ms"]) > 5 * 60 * 1000:
        raise ValueError("timestamp lech qua 5 phut; kiem tra NTP")
    ranges = {
        "temperature": (-40, 80),
        "humidity": (0, 100),
        "distance_cm": (2, 400),
        "rssi": (-120, 0),
    }
    for key, (low, high) in ranges.items():
        value = obj.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{key} phai la so")
        if not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"{key} ngoai mien [{low}, {high}]")
    return obj

