# Thực hành 2 IoT B23DCCN844 không cần Docker

Phiên bản này dùng **InfluxDB OSS 2.x cài trực tiếp trên Windows**. Phần ESP32, MQTT,
collector, tiền xử lý và dashboard giữ nguyên. Không dùng token ThingsBoard bài 1.

## 1. Cài và khởi tạo InfluxDB

1. Tải **InfluxDB OSS v2 cho Windows AMD64** từ trang chính thức:
   https://docs.influxdata.com/influxdb/v2/install/?t=Windows
   Chọn liên kết `InfluxDB v2 (Windows)`, giải nén ZIP ở nơi dễ nhớ như
   `C:\IoT\influxdb2`. Đây là `influxd` **v2**, không tải InfluxDB 3.
2. Mở PowerShell tại thư mục chứa `influxd.exe`, chạy ` .\influxd.exe ` và
   giữ cửa sổ này mở khi thực hành. Mở http://localhost:8086.
3. Trong trang thiết lập lần đầu, tạo tên người dùng và mật khẩu riêng,
   Organization Name `ptit`, Bucket Name `iot_bai2`. Sao chép API token
   được tạo và giữ riêng, không gửi cho người khác. Vào Load Data > Buckets
   > Settings của bucket `iot_bai2`, đặt retention là 7 ngày.
4. Ở thư mục dự án này, mở PowerShell và chạy `Copy-Item .env.example .env`,
   rồi `notepad .env`. Thay `ThayBangTokenInfluxDBDaSaoChep` bằng token
   InfluxDB vừa sao chép. Giữ nguyên URL, org, bucket, broker, topic và
   device_id nếu bạn làm đúng tên ở bước 3. Không đưa `.env` lên GitHub.

## 2. Cài Python

Mở PowerShell trong thư mục chứa `requirements.txt`:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 3. Khôi phục Wokwi và thu thập

Tạo dự án https://wokwi.com/projects/new/esp32. Chép ba tệp trong `wokwi/`
vào đúng tab `sketch.ino`, `diagram.json`, `libraries.txt`; có thể thêm
PubSubClient và DHT sensor library for ESPx trong Library Manager.
Lưu URL dự án. Trước khi Start Simulation, mở PowerShell trong thư mục dự án:

```powershell
.\.venv\Scripts\python.exe python\collector.py
```

Đợi dòng `Subscribed ...`, sau đó mới chạy Wokwi. Serial Monitor cần hiện
WiFi, NTP, MQTT, `publish=OK`; collector cần hiện `stored seq=...`.
Nếu không nhận, kiểm tra `MQTT_HOST`, `MQTT_TOPIC`, `DEVICE_ID` trong .env
và firmware. test.mosquitto.org:1883 công khai, không gửi dữ liệu riêng.

## 4. Xử lý và dashboard

Sau 1–2 phút, mở PowerShell thứ hai trong thư mục dự án:

```powershell
.\.venv\Scripts\python.exe python\process.py --minutes 60 --watch
```

Mở PowerShell thứ ba:

```powershell
.\.venv\Scripts\python.exe -m streamlit run python\app.py
```

Mở http://localhost:8501. Dữ liệu thô nằm ở measurement `sensor_raw`;
dữ liệu xử lý nằm ở `sensor_processed` trong bucket `iot_bai2`. Trang đang
mở tự cập nhật 2 giây, script xử lý chạy lại mỗi 30 giây.

## 5. Minh chứng và đánh giá

- Ghi 5 bản tin thật từ Data Explorer/Serial vào Word, chụp ảnh Wokwi,
  collector + InfluxDB, dashboard Streamlit. Che token/mật khẩu.
- Giữ nhiệt độ quanh 25 °C ít nhất 8 mẫu, tăng một lần lên 60 °C và về
  ban đầu; ghi kết quả outliers mà script thực tế báo.
- Dừng Wokwi 15–25 giây để quan sát ô 10 giây thiếu và gap_filled; việc
  khởi động lại tạo boot_id mới, sequence trở về 1 không phải mất gói.
- Lấy ít nhất 10 giá trị ingest_latency_ms để tính trung bình/lớn nhất;
  đọc ước lượng độ trễ tới lần app thấy mẫu khi trang mở liên tục.
- Đo CPU/RAM của influxd.exe trong Task Manager. Muốn ước lượng dung lượng
  dữ liệu tại thư mục mặc định, chạy PowerShell:

```powershell
Get-ChildItem "$env:USERPROFILE\.influxdbv2" -Recurse -File |
  Measure-Object -Property Length -Sum
```

  Ghi tổng bytes và thời gian đo; nó còn gồm metadata và dữ liệu phụ,
  không phải dung lượng riêng của các bản ghi cảm biến.

## 6. Nộp bài

Đẩy mã trong thư mục này lên GitHub, trừ `.env` và `.venv` đã được loại bởi
`.gitignore`. Nộp link Wokwi, link GitHub, Word 4–6 trang và demo Streamlit.
Giữ PowerShell `influxd.exe`, collector, process và Streamlit mở trong lúc demo.

Nguồn: https://docs.influxdata.com/influxdb/v2/install/?t=Windows
https://docs.influxdata.com/influxdb/v2/get-started/setup/
https://docs.influxdata.com/influxdb/v2/admin/buckets/update-bucket/
https://test.mosquitto.org/
