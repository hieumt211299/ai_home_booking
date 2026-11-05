# TÀI LIỆU KIẾN TRÚC TOÀN DIỆN HỆ THỐNG AI HOMESTAY BOOKING (EKKOSTAY)

---

## 1. TỔNG QUAN KIẾN TRÚC (SYSTEM OVERVIEW)

Hệ thống được thiết kế theo mô hình **Autonomous Re-Act Agent** kết hợp **Hybrid Search (SQL Pre-filtering + Vector Semantic Re-ranking)** và cơ chế an toàn **Human-in-the-loop (Backend Interceptor)**.

### Sơ đồ luồng tổng quan:
```text
[Khách hàng (Web UI / API)]
         │
         ▼
[FastAPI / Uvicorn Server (app.py)]
         │
         ▼
[HomestayAgent Engine (agent_engine.py)]
         │
         ├─► [Google Gemini 3.1 Flash-Lite (Function Calling)]
         │
         ▼
[Tầng Dữ Liệu & Thực Thi Công Cụ (db_helper.py & rag_manager.py)]
         │
         ├─► [1. SQLite Database: homestay.db] (Lọc điều kiện cứng: Giá, Số người, Lịch trống)
         │
         └─► [2. ChromaDB Vector Store: ./chroma_db] (450 Chunks: Xếp hạng Vibe & RAG Chính sách)
```

---

## 2. QUY TRÌNH CHUNKING & VECTOR DATABASE (RAG PIPELINE)

Hệ thống sử dụng mô hình nhúng mã nguồn mở `paraphrase-multilingual-MiniLM-L12-v2` (từ thư viện `sentence-transformers`) và lưu trữ tại `./chroma_db` với không gian Cosine Similarity.

Dữ liệu được nạp qua [seed_data.py](file:///Users/maitrunghieu/WorkSpace/my/home_booking/seed_data.py) và [rag_manager.py](file:///Users/maitrunghieu/WorkSpace/my/home_booking/rag_manager.py) thành **450 Vector Chunks** chia làm 2 loại:

### 2.1. Nhóm Vibe Chunks (50 Chunks - ID: `vibe_1` đến `vibe_50`)
* **Mục đích**: Nhận diện không gian, vị trí tương đối, cảm xúc của căn (*"gần biển"*, *"săn mây"*, *"lãng mạn cho 2 người"*, *"yên tĩnh"*).
* **Cấu trúc Document**:
  `Tên căn + Thành phố + Quận + Địa chỉ + Điểm nổi bật lân cận (Landmark) + Sức chứa + Giá tiền + Danh sách tiện nghi + Mô tả không gian trải nghiệm.`
* **Metadata đính kèm**: `homestay_id`, `name`, `city`, `price`, `type="vibe"`, `has_bathtub`, `allows_pets`, `has_swimming_pool`.

### 2.2. Nhóm Policy Chunks (400 Chunks - ID: `policy_1` đến `policy_400`)
* **Mục đích**: Tra cứu chính sách nội quy chuỗi bằng Vector RAG động, không cần nhồi vào System Prompt.
* **8 Chủ đề được mã hóa (Topics)**:
  1. `checkin_checkout`: Giờ nhận (14h) & trả (12h), phụ thu đi sớm/về muộn 50k/giờ.
  2. `cancellation`: Đặt cọc 50%; huỷ trước 5 ngày hoàn 100%; huỷ trước 2-5 ngày hoàn 50%; dưới 48h không hoàn cọc.
  3. `pets`: Cho phép cún/mèo < 10kg, phụ phí vệ sinh 100k/bé/đêm (phân loại rõ căn cho phép và căn cấm).
  4. `quiet_hours`: Giờ yên tĩnh 22h30 - 07h00 sáng, nghiêm cấm loa kéo công suất lớn, bay lắc.
  5. `bbq`: Phí than nướng, cồn mồi và dọn tro sau tiệc 120k/lần.
  6. `children_and_extra_guests`: Trẻ < 6 tuổi miễn phí (tối đa 2 bé/căn); trẻ 6-11 tuổi hoặc người phát sinh thêm phụ thu 150k/đêm kèm nệm phụ.
  7. `fees_and_cleaning`: Giá niêm yết trọn gói 100%, đã gồm phí vệ sinh tiêu chuẩn, cam kết không phí ẩn.
  8. `reschedule`: Đổi ngày miễn phí 1 lần trước 5 ngày; phụ phí 100k trước 2-5 ngày; dưới 48h không hỗ trợ đổi ngày.

---

## 3. DANH MỤC TOOLS (FUNCTION CALLING SCHEMA)

Các công cụ được định nghĩa trong `AGENT_TOOLS` ([agent_engine.py](file:///Users/maitrunghieu/WorkSpace/my/home_booking/agent_engine.py)):

| Tên Tool | Mô tả | Tham số đầu vào (Parameters) |
|:---|:---|:---|
| `search_homestays` | Tra cứu danh sách phòng bằng thuật toán **Hybrid Search** (SQL + Vector). **Mặc định giới hạn limit=10** để tối ưu chi phí token, linh hoạt thay đổi theo yêu cầu khách. | `city`, `district`, `name`, `query`, `min_capacity`, `min_price`, `max_price`, `check_in`, `check_out`, `has_bathtub`, `allows_pets`, `has_kitchen`, `has_swimming_pool`, `has_bbq`, `sort_by`, `limit` (mặc định 10) |
| `get_homestay_details`| Lấy chi tiết đầy đủ 1 căn theo ID hoặc theo Tên căn | `homestay_id` (int), `homestay_name` (string) |
| `ask_homestay_policy` | Tra cứu chính sách chuỗi bằng Vector RAG | `question` (string - bắt buộc), `homestay_id` (int - tuỳ chọn) |
| `create_booking` | Tạo đơn đặt phòng mới (có Human Interceptor chặn cứng) | `customer_name`, `customer_phone`, `check_in`, `check_out`, `homestay_id` / `homestay_name`, `num_guests` |
| `cancel_booking` | Hủy đơn đặt phòng và xác thực số điện thoại | `booking_code`, `customer_phone` |

---

## 4. CHI TIẾT THUẬT TOÁN HYBRID SEARCH (SQL-FIRST + VECTOR RE-RANKING)

Giải quyết triệt để các câu hỏi kết hợp tiêu chí cứng + mô tả mềm (Ví dụ: *"Tìm homestay Vũng Tàu cho 4 người gần biển"*):

```text
Khách gửi câu hỏi
        │
        ▼
LLM trích xuất tham số: city='Vũng Tàu', min_capacity=4, query='gần biển'
        │
        ▼
[BƯỚC 1: SQL HARD-FILTERING (LỌC CỨNG TRƯỚC)]
- Chạy SQL: WHERE city='Vũng Tàu' AND max_guests >= 4 AND status='ACTIVE'
- Kiểm tra loại trừ các căn trùng lịch check-in/out
- Thu được tập Candidate IDs hợp lệ: [35, 36, 37, 40, 41, 42, 43, 45, 47, 49, 50]
(Toàn bộ các căn 2 người bị loại bỏ 100% tại bước này)
        │
        ▼
[BƯỚC 2: VECTOR RE-RANKING (XẾP HẠNG NGỮ NGHĨA TRÊN TẬP ĐÃ LỌC)]
- Truyền query='gần biển' và candidate_ids vào ChromaDB (hàm search_vibe)
- ChromaDB tính Cosine Similarity CHỈ TRÊN các ID ứng viên:
    1. vibe_35 (EkkoStay Ocean View Bãi Trước - Sát biển Bãi Trước) -> Distance: 0.40 (Khớp nhất)
    2. vibe_49 (EkkoStay Oasky Seaview Bãi Sau - Tầng cao 30+)     -> Distance: 0.47
    3. vibe_41 (EkkoStay Thủy Tiên - Sát bờ cát Long Cung)         -> Distance: 0.51
    4. vibe_36 (EkkoStay Seaview Bãi Sau - 2 phút ra bãi tắm)      -> Distance: 0.57
- Sắp xếp lại danh sách kết quả SQL theo đúng thứ tự Vector
        │
        ▼
LLM nhận danh sách đã xếp hạng và tư vấn chính xác cho khách hàng
```

---

## 5. CƠ CHẾ BẢO MẬT HUMAN-IN-THE-LOOP (BACKEND INTERCEPTOR - XÁC NHẬN 1 BƯỚC DUY NHẤT)

Ngăn chặn tuyệt đối việc AI tự tiện ghi vào CSDL hoặc bịa đặt mã đặt phòng, đồng thời tối ưu trải nghiệm người dùng (chỉ xác nhận 1 lần):

```text
[LƯỢT 1] Khách gửi thông tin: "Đặt căn Phan Xích Long cuối tuần này cho 2 người, Mai Hiếu, 0972782912"
        │
        ▼
LLM gọi ngay tool create_booking(...)
        │
        ▼
[TẦNG BACKEND PYTHON INTERCEPTOR (agent_engine.py)]
- Kiểm tra cờ: is_confirmed = False
- CHẶN ĐỨNG lệnh INSERT vào CSDL!
- Tự động tra cứu giá căn và tính tổng tiền: 1 đêm x 650.000 = 650.000 VNĐ
- Lưu bản nháp (draft_booking) vào SessionState
- Trả về cho LLM trạng thái: "REQUIRES_HUMAN_CONFIRMATION" kèm dữ liệu draft
        │
        ▼
LLM xuất phiếu tóm tắt đơn phòng và yêu cầu khách phản hồi "Đồng ý" hoặc "Xác nhận"
        │
        ▼
[LƯỢT 2] Khách phản hồi: "Đồng ý" (hoặc "Xác nhận", "Ok")
        │
        ▼
- Backend nhận diện từ khóa xác nhận ['xác nhận', 'đồng ý', 'ok', 'chốt'] -> Bật cờ is_confirmed = True
- LLM gọi lại create_booking(...)
- Backend kiểm tra thấy is_confirmed = True -> CHO PHÉP THỰC THI GHI VÀO SQL DATABASE
- Sinh mã booking duy nhất (VD: HB-6742), khóa lịch phòng và thông báo đặt phòng thành công ngay!
```

---

## 6. QUẢN LÝ PHIÊN (SESSION STATE), TRACES & SYSTEM PROMPT

### 6.1. Cấu trúc SessionState
Mỗi phiên chat (`session_id`) lưu giữ:
* `messages`: Lịch sử hội thoại chuẩn OpenAI format (lấy 12 tin nhắn gần nhất để tối ưu token).
* `detected_profile`: Thông tin tên và số điện thoại của khách hàng.
* `pending_booking`: Lưu trữ bản nháp đơn phòng đang chờ duyệt.

### 6.2. Hệ thống Giám sát thời gian thực (Live AI Inspector Traces)
Bảng điều khiển bên phải của Web UI hiển thị tuần tự các giai đoạn xử lý:
1. `🔧 LLM GỌI TOOL`: Thông số hàm và tham số Gemini tự động bóc tách.
2. `⚡ VECTOR SEMANTIC RE-RANKING`: ChromaDB tính toán Cosine Similarity cho cụm từ ngữ nghĩa (`vibe_query`) trên tập ID ứng viên đã lọc cứng từ SQL, hiển thị điểm số và bảng xếp hạng.
3. `📊 KẾT QUẢ TỪ DATABASE`: Dữ liệu trả về sạch sau khi đã sắp xếp.
4. `🤖 LLM TỔNG HỢP`: Câu trả lời được biên tập dựa trên dữ liệu thật (kèm thông tin token usage).

### 6.3. Bộ nguyên tắc cốt lõi trong System Prompt (Meta-Rules)
Prompt được tinh gọn thành 5 nhóm Meta-Rules giúp chống Prompt Bloat:
1. **Persona & Trình bày**: Lễ tân chuỗi EkkoStay lịch sự, tự nhiên; **tuyệt đối không để lộ mã ID kỹ thuật** (như `[ID: 15]`).
2. **Grounding & Sử dụng Tool**: Mọi thông tin giá cả, lịch phòng, chính sách đều phải lấy từ Tool thật, không tự đoán.
3. **Thời gian thực**: Tự động inject ngày giờ hiện tại (`now = datetime.now()`) vào prompt để AI tự quy đổi *"hôm nay"*, *"ngày mai"*, *"cuối tuần này"*, *"15/11"* thành định dạng `YYYY-MM-DD`.
4. **Clarification Strategy**: Khi khách nói tiêu chí mơ hồ (*"thuê 3 ngày 2 đêm"* mà chưa có ngày đi), lễ tân chủ động hỏi lại lịch dự kiến.
5. **Chính sách bảo mật**: Không cho phép sửa đổi đơn phòng qua Chatbot, hướng dẫn khách mở App EkkoStay vào mục *"Quản lý đặt phòng"*.

### 6.4. Xử lý lỗi API & Cơ chế Phục hồi An toàn (API Resilience & Error Handling)
- **Chuẩn hóa Error Response**: Hàm `_safe_post_api` trong `HomestayAgent` xử lý an toàn khi Google Gemini API trả về cấu trúc lỗi dạng mảng JSON `[{'error': ...}]` (đặc thù của một số endpoint Google), ngăn chặn triệt để lỗi `TypeError: list indices must be integers or slices, not str`.
- **Nhận diện chính xác lỗi HTTP 402/429**: Trích xuất chi tiết nguyên nhân (ví dụ tài khoản hết credit trả trước hoặc vượt hạn mức RPM/TPM) và hiển thị thông tin trực quan lên Live AI Inspector giúp kỹ sư vận hành khắc phục ngay lập tức.

---

## 7. MÔI TRƯỜNG THỰC THI & QUẢN LÝ PHỤ THUỘC (RUNTIME & DEPENDENCIES)
- **Trình quản lý chính thức**: Hỗ trợ tiêu chuẩn **Astral `uv`** qua [pyproject.toml](file:///Users/maitrunghieu/WorkSpace/my/home_booking/pyproject.toml), cho phép chạy ứng dụng không cần kích hoạt virtualenv thủ công:
  * Khởi tạo dữ liệu: `uv run seed_data.py`
  * Khởi chạy Web UI: `uv run app.py --ui`
- **Tương thích ngược**: Cung cấp song song file [requirements.txt](file:///Users/maitrunghieu/WorkSpace/my/home_booking/requirements.txt) phục vụ môi trường CI/CD và triển khai Docker/Pip truyền thống.

