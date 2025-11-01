# 🚀 Hướng Dẫn Deploy Gmail OAuth Tool Lên Railway

## 📋 Bước 1: Setup Google Cloud OAuth

### 1.1 Tạo Google Cloud Project
1. Vào https://console.cloud.google.com
2. Nhấp **"Tạo dự án"** → Đặt tên `Gmail OAuth App`
3. Chờ dự án được tạo

### 1.2 Bật Gmail API
1. Tìm kiếm **"Gmail API"** trên thanh tìm kiếm
2. Nhấp vào **Gmail API** → Nhấp **"Bật"**

### 1.3 Tạo OAuth 2.0 Credentials
1. Vào **"Xác thực"** (Authentication) ở menu trái
2. Nhấp **"+ Tạo Credentials"** → **"OAuth 2.0 Client ID"**
3. **Lần đầu:** Nhấp **"Cấu hình OAuth Consent Screen"**
   - Chọn **"External"** → **"Tạo"**
   - Điền App name: `Gmail OAuth Tool`
   - Thêm email: Tài khoản Google của bạn
   - Thêm scopes: Tìm và chọn `gmail.send`
   - Nhấp **"Lưu và tiếp tục"** cho đến hết

### 1.4 Lấy Client ID & Secret
1. Quay lại **"Xác thực"** → **"+ Tạo Credentials"** → **"OAuth 2.0 Client ID"**
2. Chọn **"Web application"**
3. Thêm Authorized redirect URIs:
   - `http://localhost:5000/oauth2callback` (Local testing)
   - `https://yourdomain.railway.app/oauth2callback` (Railway)
4. Nhấp **"Tạo"**
5. **Sao chép** `Client ID` và `Client Secret`

---

## 🚂 Bước 2: Deploy Lên Railway

### 2.1 Push Code Lên GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/gmail-oauth-tool.git
git push -u origin main
```

### 2.2 Deploy Trên Railway
1. Vào https://railway.app
2. Nhấp **"New Project"** → **"Deploy from GitHub"**
3. Chọn repo `gmail-oauth-tool`
4. Railway tự động detect `Procfile` và deploy

### 2.3 Thêm Biến Môi Trường
1. Vào tab **"Variables"** trong Railway dashboard
2. Thêm các biến:

```
GOOGLE_CLIENT_ID=YOUR_CLIENT_ID_HERE
GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE
REDIRECT_URI=https://your-railway-domain.railway.app/oauth2callback
FLASK_SECRET_KEY=your-random-secret-key-12345
```

**Lấy Railway domain:**
- Vào **"Settings"** → Tìm **"Public URL"**
- Ví dụ: `https://gmail-oauth-tool-production.up.railway.app`

---

## ✅ Bước 3: Kiểm Tra

1. Vào URL của Railway app
2. Nhấp **"🔐 Đăng Nhập Gmail"**
3. Đăng nhập bằng tài khoản Gmail
4. Nếu thành công, sẽ hiển thị email của bạn ở góc phải

---

## 📁 Cấu Trúc Thư Mục

```
gmail-oauth-tool/
├── app.py                    # Backend chính (Multiuser)
├── modules/
│   ├── __init__.py
│   ├── email_sender_oauth.py # Gửi email qua Gmail API
│   ├── excel_splitter.py     # Tách file Excel
│   └── utils.py              # Hỗ trợ Excel
├── templates/
│   └── index_multiuser.html  # Giao diện (Login/Logout)
├── requirements.txt          # Dependencies
├── Procfile                  # Railway config
└── .gitignore               # Git ignore
```

---

## 🔧 Local Testing

```bash
# 1. Cài dependencies
pip install -r requirements.txt

# 2. Tạo file .env
echo "GOOGLE_CLIENT_ID=YOUR_CLIENT_ID" > .env
echo "GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET" >> .env
echo "REDIRECT_URI=http://localhost:5000/oauth2callback" >> .env
echo "FLASK_SECRET_KEY=secret123" >> .env

# 3. Chạy ứng dụng
python app.py

# 4. Vào http://localhost:5000
```

---

## 🆘 Troubleshooting

### "redirect_uri_mismatch" error
- Kiểm tra `REDIRECT_URI` trong Google Cloud Console khớp với `REDIRECT_URI` trong Railway

### "Invalid client" error
- Kiểm tra `GOOGLE_CLIENT_ID` và `GOOGLE_CLIENT_SECRET` chính xác

### Email không gửi được
- Kiểm tra tài khoản Gmail không bật 2FA
- Nếu bật 2FA, setup "App Password" cũng không cần vì ta dùng OAuth

---

## 📝 Lưu Ý

✅ Mỗi user cần đăng nhập Gmail một lần
✅ Token tự động lưu trong session
✅ Không cần upload `credentials.json`
✅ Support multiuser - mỗi người có token riêng
✅ OAuth token tự động làm mới khi hết hạn

---

## 🎯 Tóm Tắt

| Bước | Công Việc |
|------|----------|
| 1 | Setup Google Cloud OAuth |
| 2 | Push code lên GitHub |
| 3 | Deploy trên Railway |
| 4 | Thêm biến môi trường |
| 5 | Test đăng nhập |
| 6 | Chia sẻ link cho team |