"""Dashboard raw/processed, tu cap nhat 2s khi tab dang mo."""
import time
import pandas as pd
import streamlit as st
from common import db, query_frame, setting

st.set_page_config(page_title="Bài 2 IoT - B23DCCN844", layout="wide")
st.title("Giám sát dữ liệu IoT - Bài thực hành 2")
st.caption("ESP32 Wokwi → MQTT → Python → InfluxDB 2.x → Streamlit")
minutes = st.sidebar.selectbox("Khoảng xem", [10, 30, 60, 180], index=1)
st.sidebar.write("Tự cập nhật mỗi 2 giây khi trang đang mở.")

@st.fragment(run_every="2s")
def panels():
    try:
        with db() as client:
            raw = query_frame(client, "sensor_raw", minutes)
            processed = query_frame(client, "sensor_processed", minutes)
    except Exception as exc:
        st.error(f"Không đọc được InfluxDB: {exc}")
        return
    if raw.empty:
        st.info("Chưa có dữ liệu. Hãy chạy collector trước rồi khởi động Wokwi.")
        return
    last = raw.iloc[-1]
    a, b, c, d = st.columns(4)
    a.metric("Nhiệt độ", f"{last['temperature']:.1f} °C")
    b.metric("Độ ẩm", f"{last['humidity']:.1f} %RH")
    c.metric("Khoảng cách", f"{last['distance_cm']:.1f} cm")
    d.metric("Đến collector", f"{last['ingest_latency_ms']:.0f} ms")

    # Ghi thoi diem app lan dau nhin thay mot sequence moi trong phien hien tai.
    current = (str(last.get("boot_id")), int(last["sequence"]))
    if st.session_state.get("seen_key") != current:
        st.session_state.seen_key = current
        observed_ms = time.time_ns() // 1_000_000
        elapsed = observed_ms - int(last["sent_at_ms"])
        if 0 <= elapsed < 60000:
            st.session_state.setdefault("first_seen_ms", []).append(elapsed)
            st.session_state.first_seen_ms = st.session_state.first_seen_ms[-50:]
    seen = st.session_state.get("first_seen_ms", [])
    st.caption(f"Ước lượng đến lần hiển thị đầu trên app: {seen[-1] if seen else '—'} ms; "
               "bao gồm chu kỳ làm mới 2 giây, cần đồng bộ đồng hồ.")
    if seen:
        st.write(f"Trung bình {len(seen)} lần quan sát: {sum(seen)/len(seen):.0f} ms")

    chart = raw.set_index("_time")[["temperature", "humidity", "distance_cm"]]
    st.subheader("Dữ liệu thô theo thời gian")
    st.line_chart(chart)
    st.subheader("Dữ liệu sau tiền xử lý")
    if processed.empty:
        st.info("Chạy python python/process.py --watch để tạo measurement sensor_processed.")
    else:
        chart2 = processed.set_index("_time")
        st.line_chart(chart2[["temperature", "temp_roll3"]].rename(
            columns={"temperature": "Nhiệt độ xử lý", "temp_roll3": "Trung bình trượt"}))
        st.dataframe(processed[["_time", "temperature", "humidity", "distance_cm",
                                "gap_filled", "temp_delta", "temp_z"]].tail(12),
                     hide_index=True, use_container_width=True)
    st.subheader("5 bản ghi thô gần nhất")
    cols = ["_time", "sequence", "temperature", "humidity", "distance_cm", "ingest_latency_ms"]
    st.dataframe(raw[cols].tail(5), hide_index=True, use_container_width=True)

panels()
