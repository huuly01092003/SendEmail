# 📧 Excel Splitter & Email Sender

Web application để tách file Excel và gửi email tự động qua Gmail SMTP.

## ✨ Tính năng

- 🧾 Tách file Excel theo cột (VD: Mã đối tác)
- ✉️ Gửi email tự động kèm file đính kèm
- 📊 Theo dõi tiến độ realtime
- 📥 Tải file log CSV

## 🚀 Deploy

### Railway.app (Recommended)
1. Fork repo này
2. Kết nối Railway với GitHub
3. Deploy tự động

### Local
```bash
pip install -r requirements.txt
python app.py
```

## 📝 Cách sử dụng

### 1. Tách file Excel
- Upload file Excel gốc
- Chọn cột cần chia (VD: "Mã NPP")
- Nhập dòng bắt đầu/kết thúc
- Tải file ZIP

### 2. Gửi email
- Upload file ZIP đã tách
- Upload file Excel chứa danh sách email
- Nhập thông tin Gmail (App Password)
- Gửi email tự động

## 🔐 Gmail App Password

1. Vào Google Account → Bảo mật
2. Bật "Xác minh 2 bước"
3. Tạo "Mật khẩu ứng dụng"
4. Chọn "Mail" và "Windows Computer"
5. Copy password 16 ký tự

## 📋 Requirements

- Python 3.8+
- Flask
- pandas
- openpyxl
- gunicorn

## 📄 License

MIT License