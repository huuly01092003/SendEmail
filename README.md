# 🚀 Gmail OAuth Tool - Tách Excel & Gửi Email

Ứng dụng web cho phép tách file Excel và gửi email tự động thông qua Gmail OAuth 2.0.

## ✨ Tính Năng

- ✅ **Tách File Excel**: Chia file Excel thành nhiều file nhỏ theo cột
- ✅ **Gửi Email Tự Động**: Gửi email từ tài khoản Gmail cá nhân của mỗi người
- ✅ **OAuth 2.0**: Xác thực an toàn với Google, KHÔNG cần mật khẩu
- ✅ **Multiuser**: Mỗi người dùng có tài khoản Gmail riêng
- ✅ **Progress Tracking**: Theo dõi tiến độ gửi email real-time
- ✅ **Log File**: Tải file CSV kết quả sau khi gửi

---

## 📋 Yêu Cầu Hệ Thống

- Python 3.10+
- Git
- Tài khoản GitHub
- Tài khoản Railway (https://railway.app)
- Tài khoản Google Cloud

---

## 🔧 Cài Đặt Local

### 1. Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/gmail-oauth-tool.git
cd gmail-oauth-tool
```

### 2. Tạo Virtual Environment
```bash
python -m venv venv

# Trên Windows:
venv\Scripts\activate

# Trên Mac/Linux:
source venv/bin/activate
```

### 3. Cài Đặt Dependencies
```bash
pip install -r requirements.txt
```

### 4. Tạo File .env
```bash
# Windows PowerShell:
New-Item -Name ".env" -ItemType File
# Hoặc dùng text editor, tạo file .env

# Mac/Linux:
touch .env
```

**Nội dung .env:**
```
GOOGLE_CLIENT_ID=YOUR_CLIENT_ID_HERE
GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE
REDIRECT_URI=http://localhost:5000/oauth2callback
FLASK_SECRET_KEY=your-random-secret-key-change-me
```

### 5. Chạy Ứng Dụng
```bash
python app.py
```

Vào: http://localhost:5000

---

## 🌐 Deploy Lên Railway

### Bước 1: Setup Google Cloud OAuth

#### 1.1 Tạo Google Cloud Project
1. Vào https://console.cloud.google.com
2. Nhấp **"Tạo dự án"** → Đặt tên `Gmail OAuth Tool`

#### 1.2 Bật Gmail API
1. Tìm kiếm **"Gmail API"** → Nhấp **"Bật"**

#### 1.3 Tạo OAuth 2.0 Credentials
1. Vào **"Xác thực"** (Authentication)
2. Nhấp **"+ Tạo Credentials"** → **"OAuth 2.0 Client ID"**
3. **Cấu hình OAuth Consent Screen:**
   - Chọn **"External"**
   - Điền **App name**: `Gmail OAuth Tool`
   - Thêm email hỗ trợ
   - Thêm scope: `gmail.send`
   - Lưu

4. **Tạo Client ID:**
   - Chọn **"Ứng dụng Web"**
   - **Authorized JavaScript origins:**
     ```
     http://localhost:5000
     https://your-railway-domain.up.railway.app
     ```
   - **Authorized redirect URIs:**
     ```
     http://localhost:5000/oauth2callback
     https://your-railway-domain.up.railway.app/oauth2callback
     ```
   - Nhấp **"Tạo"** → Sao chép **Client ID** và **Client Secret**

---

### Bước 2: Push Code Lên GitHub

```bash
git add .
git commit -m "Initial commit - Gmail OAuth Tool"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/gmail-oauth-tool.git
git push -u origin main
```

---

### Bước 3: Deploy Trên Railway

1. Vào https://railway.app
2. Nhấp **"New Project"** → **"Deploy from GitHub"**
3. Chọn repo `gmail-oauth-tool`
4. Railway tự động detect `Procfile` và deploy (~3-5 phút)

---

### Bước 4: Lấy Railway Domain

1. Vào **"Settings"** của project
2. Tìm **"Public URL"** (ví dụ: `https://gmail-oauth-tool-production-xyz.up.railway.app`)

---

### Bước 5: Thêm Biến Môi Trường

1. Vào Railway Dashboard → **"Variables"**
2. Thêm:

```
GOOGLE_CLIENT_ID=YOUR_CLIENT_ID_HERE
GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE
REDIRECT_URI=https://your-railway-domain.up.railway.app/oauth2callback
FLASK_SECRET_KEY=your-random-secret-key-12345
```

3. Nhấp **"Deploy"**

---

### Bước 6: Cập Nhật Google Cloud Credentials

1. Quay lại https://console.cloud.google.com
2. **Credentials** → OAuth 2.0 Client ID
3. Thêm vào **Authorized redirect URIs:**
   ```
   https://your-railway-domain.up.railway.app/oauth2callback
   ```
4. Lưu

---

## ✅ Test Ứng Dụng

1. Vào Railway URL: `https://your-railway-domain.up.railway.app`
2. Nhấp **"🔐 Đăng Nhập Gmail"**
3. Đăng Nhập bằng tài khoản Google
4. Nếu thành công, sẽ hiển thị email ở góc phải ✅

---

## 📂 Cấu Trúc Thư Mục

```
gmail-oauth-tool/
├── app.py                      # Backend chính
├── requirements.txt            # Dependencies
├── Procfile                    # Railway config
├── runtime.txt                 # Python version
├── README.md                   # Tài liệu
├── .gitignore                  # Git ignore
├── .env                        # Environment variables (KHÔNG PUSH)
├── modules/
│   ├── __init__.py
│   ├── email_sender_oauth.py   # Gửi email qua Gmail API
│   ├── excel_splitter.py       # Tách file Excel
│   └── utils.py                # Hỗ trợ Excel
├── templates/
│   └── index_multiuser.html    # Giao diện
├── flask_session/              # Session files (KHÔNG PUSH)
└── __pycache__/                # Cache Python (KHÔNG PUSH)
```

---

## 🆘 Troubleshooting

### "redirect_uri_mismatch" Error
- Kiểm tra `REDIRECT_URI` trong biến môi trường khớp với Google Cloud

### "Invalid client" Error
- Kiểm tra `GOOGLE_CLIENT_ID` và `GOOGLE_CLIENT_SECRET` chính xác

### App không load
- Vào Railway Logs kiểm tra lỗi
- Đảm bảo `Procfile` có trong repo

### Email không gửi
- Kiểm tra token hạn hết (refresh token)
- Kiểm tra scope `gmail.send` được thêm

---

## 🔐 Bảo Mật

⚠️ **QUAN TRỌNG:**
- ❌ KHÔNG commit file `.env`
- ❌ KHÔNG share `GOOGLE_CLIENT_SECRET`
- ❌ KHÔNG push `__pycache__/` hoặc `flask_session/`
- ✅ Dùng Railway Environment Variables thay vì hardcode

---

## 📝 Lưu Ý

✅ Mỗi user cần đăng nhập Gmail một lần
✅ Token tự động lưu trong session của user
✅ Không cần upload `credentials.json`
✅ Support multiuser - mỗi người có token riêng
✅ OAuth token tự động làm mới khi hết hạn

---

## 👥 Chia Sẻ Cho Mọi Người

Sau khi triển khai thành công, chia sẻ URL:
```
https://your-railway-domain.up.railway.app
```

Mỗi người chỉ cần:
1. Vào link
2. Đăng Nhập Gmail
3. Sử dụng ứng dụng

---

## 📊 Quy Trình Sử Dụng

1. **Tách File Excel** (Không cần đăng nhập)
   - Upload file Excel gốc
   - Chọn cột cần chia
   - Tải ZIP file

2. **Đăng Nhập Gmail** (Cần đăng nhập)
   - Nhấp "Đăng Nhập Gmail"
   - Xác thực bằng Google

3. **Gửi Email**
   - Upload ZIP + Email list
   - Điền thông tin email
   - Nhấp "Gửi Email Tự Động"

4. **Tải Log**
   - Download file CSV kết quả

---

## 📧 Liên Hệ

Nếu có vấn đề, vui lòng tạo Issue trên GitHub.

---