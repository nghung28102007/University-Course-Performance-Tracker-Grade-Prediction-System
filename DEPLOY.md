# Deploy ACP Tracker (Render + GitHub)

Repo: https://github.com/nghung28102007/University-Course-Performance-Tracker-Grade-Prediction-System

## Bước 1 — Push code lên GitHub

```powershell
git add .
git commit -m "Add Render deploy config"
git push origin main
```

(Nếu branch là `master`, đổi `main` → `master`.)

## Bước 2 — Tạo Web Service trên Render (miễn phí)

1. Vào https://dashboard.render.com → đăng nhập bằng **GitHub**
2. **New +** → **Web Service**
3. Connect repo `University-Course-Performance-Tracker-Grade-Prediction-System`
4. Cấu hình:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
5. **Create Web Service** → đợi ~3–5 phút

## Bước 3 — Mở app

URL dạng: `https://acp-tracker-xxxx.onrender.com`

Đăng nhập: `/login` → role **Admin**

## Lưu ý

- Free tier **sleep** sau 15 phút không dùng → lần mở đầu chậm ~30s
- SQLite trên Render **reset khi redeploy** → `seed_data()` tự chạy lại khi khởi động
- Local vẫn chạy: `python app.py`
