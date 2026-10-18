"""Subscribe MQTT, validate JSON, ghi measurement sensor_raw."""
import logging
import time
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from common import db, setting
from validate import parse_payload

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
database = db()
writer = database.write_api(write_options=SYNCHRONOUS)
last_seq = {}  # Phat hien trung/lỗ hổng trong mot lan chay; InfluxDB ghi de diem cung time + tag.

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        logging.error("MQTT connection refused: %s", reason_code)
        return
    topic = setting("MQTT_TOPIC")
    client.subscribe(topic, qos=1)
    logging.info("Subscribed %s", topic)

def on_message(client, userdata, message):
    try:
        item = parse_payload(message.payload, setting("DEVICE_ID"))
        key = (item["device_id"], item["boot_id"])
        seq = item["sequence"]
        prev = last_seq.get(key, 0)
        if seq <= prev:
            logging.warning("Duplicate/out-of-order sequence=%s, previous=%s; skip", seq, prev)
            return
        if prev and seq > prev + 1:
            logging.warning("Sequence gap: %s -> %s (can doi chieu voi Serial)", prev, seq)
        received_ms = time.time_ns() // 1_000_000
        latency_ms = received_ms - item["sent_at_ms"]
        point = (Point("sensor_raw")
            .tag("device_id", item["device_id"])
            .field("boot_id", item["boot_id"])
            .field("sequence", seq)
            .field("temperature", float(item["temperature"]))
            .field("humidity", float(item["humidity"]))
            .field("distance_cm", float(item["distance_cm"]))
            .field("rssi", int(item["rssi"]))
            .field("uptime_s", int(item["uptime_s"]))
            .field("sent_at_ms", int(item["sent_at_ms"]))
            .field("received_at_ms", received_ms)
            .field("ingest_latency_ms", latency_ms)
            .time(datetime.fromtimestamp(item["sent_at_ms"] / 1000, tz=timezone.utc), WritePrecision.MS))
        writer.write(bucket=setting("INFLUX_BUCKET"), org=setting("INFLUX_ORG"), record=point)
        last_seq[key] = seq  # Chi danh dau sau khi DB ghi thanh cong.
        logging.info("stored seq=%d temp=%.2f latency_to_collector=%dms", seq,
                     item["temperature"], latency_ms)
    except Exception as exc:
        logging.error("Skipped message / DB write failed: %s", exc)

def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="collector-B23DCCN844")
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.connect(setting("MQTT_HOST"), int(setting("MQTT_PORT")), keepalive=60)
    try:
        client.loop_forever()
    finally:
        writer.close()
        database.close()

if __name__ == "__main__":
    main()

