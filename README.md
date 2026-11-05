# Hệ Thống AI Chatbot Đặt Phòng Homestay (EkkoStay Chain)

Dự án AI Agent hoàn chỉnh cho chuỗi 50 Homestay (Đà Lạt, TP.HCM, Vũng Tàu), kết hợp:
* **Tool Calling (Database SQLite)**: Tìm kiếm phòng theo giá, sức chứa, tiện nghi, kiểm tra lịch trống và đặt phòng.
* **Hybrid Search (SQL Pre-filtering + Vector Semantic Re-ranking)**: Lọc cứng điều kiện bằng SQL trước, sau đó dùng ChromaDB + Embedding tiếng Việt `paraphrase-multilingual-MiniLM-L12-v2` để xếp hạng ngữ nghĩa theo "vibe" (ví dụ: *"gần biển"*, *"săn mây"*, *"lãng mạn"*).
* **Human-in-the-Loop Interceptor**: Chặn lệnh đặt phòng ở tầng Backend Python, bắt buộc người dùng xác nhận bản nháp trước khi lưu vào CSDL thật.
* **Live AI Thought Inspector**: Giao diện chia đôi màn hình hiển thị trực quan toàn bộ quá trình suy nghĩ và gọi công cụ ngầm của AI thời gian thực.

---

## ⚡ 1. Cài Đặt & Chạy Siêu Tốc Bằng `uv` (Khuyên dùng)

Dự án đã hỗ trợ chuẩn `pyproject.toml` và `uv`. Nếu bạn đã cài [uv](https://docs.astral.sh/uv/):

```bash
# 1. Khởi tạo dữ liệu (tự động cài thư viện nếu chưa có):
uv run seed_data.py

# 2. Khởi động Web UI kèm AI Thought Inspector:
uv run app.py --ui
```
*(Hoặc chạy trên Terminal CLI: `uv run app.py`)*

---

## 🚀 2. Cài Đặt Môi Trường Truyền Thống (Pip / Python)

Nếu không dùng `uv`, bạn có thể dùng `pip` tiêu chuẩn:

### Bước 1: Yêu cầu hệ thống
* Python 3.10 trở lên.
* Khuyến nghị dùng môi trường ảo (virtual environment).

### Bước 2: Cài đặt các thư viện cần thiết
```bash
pip install -r requirements.txt
```

### Bước 3: Cấu hình file `.env`
Tạo file `.env` tại thư mục gốc với nội dung:
```env
GOOGLE_API_KEY="AIzaSy..."
GOOGLE_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
GOOGLE_MODEL="gemini-3.1-flash-lite"
```
> [!NOTE]
> Bạn có thể lấy API Key hoàn toàn miễn phí tại [Google AI Studio](https://aistudio.google.com/apikey) (chọn *Create API key in new project* để dùng hạn mức Free Tier).

---

## 🗄️ 3. Khởi Tạo Cơ Sở Dữ Liệu & Vector Store (Nếu dùng Python truyền thống)

Trước khi chạy lần đầu, hãy khởi tạo database SQLite và nạp 450 Vector Chunks vào ChromaDB:
```bash
python3 seed_data.py
```
Lệnh này sẽ:
1. Tạo file SQLite `homestay.db` với 50 căn homestay mẫu tại Đà Lạt, TP.HCM, Vũng Tàu.
2. Tải mô hình nhúng `paraphrase-multilingual-MiniLM-L12-v2` về máy và lập chỉ mục Vector vào thư mục `./chroma_db` (50 Vibe Chunks + 400 Policy Chunks).

---

## 💻 4. Chạy Ứng Dụng Local

### Cách 1: Chạy Web UI kèm Live Inspector (Khuyên dùng)
* **Dùng `uv`**:
  ```bash
  uv run app.py --ui
  ```
* **Dùng `python3`**:
  ```bash
  python3 app.py --ui
  ```
* Tự động mở trình duyệt tại: **`http://localhost:8000`**
* **Cột trái**: Giao diện Chatbot với khách hàng (kèm các gợi ý câu hỏi mẫu).
* **Cột phải (Live Inspector)**: Xem từng bước xử lý ngầm của AI:
  * Trích xuất tham số gọi Tool (`search_homestays`, `create_booking`, `ask_homestay_policy`).
  * Vector Semantic Re-ranking (Cosine Distance trên ChromaDB).
  * Trạng thái chặn của Backend Interceptor (Human Confirmation).
  * Thống kê Token & Chi phí phản hồi của Gemini.

### Cách 2: Chạy chế độ Chat trực tiếp trên Terminal CLI
```bash
uv run app.py
# hoặc: python3 app.py
```

---

## 🌐 5. Public Online Để Demo Cho Người Khác

Để gửi link cho đồng nghiệp hoặc xem thử trên điện thoại mà không cần deploy lên server phức tạp:

### Cách A: Dùng Ngrok với Subdomain Cố Định (Khuyên dùng - 100% Free)
> Cách này giúp link **cố định mãi mãi**, mỗi lần mở máy lên demo không bị đổi link.

1. **Bật Server App (Tab Terminal 1 - Chạy cổng 8000):**
   ```bash
   python3 app.py --ui
   ```
2. **Bật Ngrok trỏ đúng vào cổng 8000 (Tab Terminal 2):**
   ```bash
   ngrok http --domain=<SUBDOMAIN_CỦA_BẠN> 8000
   ```
   *(Ví dụ: `ngrok http --domain=grinning-untamed-relenting.ngrok-free.dev 8000`)*

### Cách B: Dùng Cloudflare Tunnel (Nhanh - Link ngẫu nhiên)
1. **Bật Server App (Tab Terminal 1):**
   ```bash
   python3 app.py --ui
   ```
2. **Tạo Tunnel (Tab Terminal 2):**
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```
   Copy link `https://xxxx.trycloudflare.com` hiển thị ở log để gửi demo.

---

## ⚠️ 5. Xử Lý Sự Cố Thường Gặp (Troubleshooting)

| Sự cố | Nguyên nhân | Cách khắc phục |
| :--- | :--- | :--- |
| **`Address already in use: ('127.0.0.1', 8000)`** | Tiến trình cũ vẫn đang chiếm cổng 8000 ngầm. | Chạy lệnh giải phóng port: <br>`kill -9 $(lsof -ti:8000)` rồi bật lại server. |
| **Ngrok báo `502 Bad Gateway`** | 1. Ngrok trỏ nhầm cổng (ví dụ gõ 8080 thay vì 8000).<br>2. Server `app.py` chưa được bật. | Đảm bảo server `python3 app.py --ui` đang chạy và lệnh ngrok có đuôi là `8000`. |
| **Google API [402 - Hết credits/hạn mức]** | API Key thuộc GCP Project trả trước đã hết số dư tiền ($0 USD). | Vào [Google AI Studio](https://aistudio.google.com/apikey) tạo key mới trong project miễn phí (Free Tier) rồi thay vào file `.env`. |

---

## 📁 6. Cấu Trúc Mã Nguồn

```text
├── app.py                  # Server FastAPI + Giao diện Web Chat & Thought Inspector UI
├── agent_engine.py         # Bộ não AI Re-Act, Quản lý Session, Backend HITL Interceptor
├── db_helper.py            # Tầng CSDL SQLite: Truy vấn, Đặt cọc, Huỷ phòng, Hybrid Search
├── rag_manager.py          # Quản lý ChromaDB & Embedding paraphrase-multilingual-MiniLM-L12-v2
├── seed_data.py            # Dữ liệu hạt giống: 50 căn homestay & 450 Vector chunks
├── schema.sql              # Định nghĩa schema bảng CSDL SQLite
├── SYSTEM_ARCHITECTURE.md  # Tài liệu kỹ thuật chi tiết toàn diện về kiến trúc hệ thống
└── .env                    # Biến môi trường (API Key, Model config)
```

> [!TIP]
> Xem chi tiết tài liệu thiết kế sâu về luồng dữ liệu, schema tools và cơ chế Hybrid Search tại [SYSTEM_ARCHITECTURE.md](file:///Users/maitrunghieu/WorkSpace/my/home_booking/SYSTEM_ARCHITECTURE.md).
