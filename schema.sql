-- Database Schema cho hệ thống Homestay Booking AI

-- 1. Bảng danh sách Homestay
CREATE TABLE IF NOT EXISTS homestays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                         -- Tên homestay (VD: "Mây Lang Thang Homestay")
    city TEXT NOT NULL,                         -- Thành phố (Đà Lạt, Vũng Tàu, Hà Nội...)
    district TEXT NOT NULL,                     -- Quận/Huyện/Phường
    address TEXT NOT NULL,                      -- Địa chỉ chi tiết
    landmark TEXT,                              -- Địa danh nổi bật gần đó (Gần Hồ Xuân Hương, Gần Bãi Sau...)
    latitude REAL,                              -- Tọa độ vĩ độ
    longitude REAL,                             -- Tọa độ kinh độ
    
    max_guests INTEGER NOT NULL,                -- Số lượng khách tối đa
    num_bedrooms INTEGER DEFAULT 1,             -- Số phòng ngủ
    num_beds INTEGER DEFAULT 1,                 -- Số giường
    price_per_night REAL NOT NULL,              -- Giá tiền 1 đêm (VNĐ)
    
    -- Các tiện ích quan trọng khách hay tìm kiếm
    has_bathtub INTEGER DEFAULT 0,              -- 1: Có bồn tắm, 0: Không
    allows_pets INTEGER DEFAULT 0,              -- 1: Cho phép mang thú cưng, 0: Không
    has_kitchen INTEGER DEFAULT 0,              -- 1: Có bếp nấu ăn, 0: Không
    has_swimming_pool INTEGER DEFAULT 0,        -- 1: Có hồ bơi, 0: Không
    has_bbq INTEGER DEFAULT 0,                  -- 1: Có sân/bếp nướng BBQ, 0: Không
    
    amenities TEXT,                             -- Danh sách tiện ích mở rộng (JSON string)
    description TEXT,                           -- Giới thiệu ngắn về căn
    status TEXT DEFAULT 'ACTIVE'                -- ACTIVE / MAINTENANCE
);

-- 2. Bảng chính sách & thông tin chi tiết (Dùng cho RAG / Hỏi đáp)
CREATE TABLE IF NOT EXISTS homestay_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    homestay_id INTEGER NOT NULL,
    topic TEXT NOT NULL,                        -- 'cancellation', 'pets', 'checkin_checkout', 'parking', 'bbq'
    title TEXT NOT NULL,                        -- Tiêu đề ngắn gọn
    content TEXT NOT NULL,                      -- Nội dung chi tiết chính sách/quy định
    FOREIGN KEY (homestay_id) REFERENCES homestays(id) ON DELETE CASCADE
);

-- 3. Bảng đặt phòng
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_code TEXT UNIQUE NOT NULL,          -- Mã đặt phòng (VD: HB-1029)
    homestay_id INTEGER NOT NULL,
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    num_guests INTEGER NOT NULL,
    total_price REAL NOT NULL,
    status TEXT DEFAULT 'CONFIRMED',            -- 'CONFIRMED', 'CANCELLED'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (homestay_id) REFERENCES homestays(id)
);

-- Tạo Index để tối ưu truy vấn tìm kiếm
CREATE INDEX IF NOT EXISTS idx_homestays_city ON homestays(city);
CREATE INDEX IF NOT EXISTS idx_homestays_filters ON homestays(max_guests, has_bathtub, allows_pets, price_per_night);
CREATE INDEX IF NOT EXISTS idx_bookings_dates ON bookings(homestay_id, check_in, check_out, status);
CREATE INDEX IF NOT EXISTS idx_bookings_code_phone ON bookings(booking_code, customer_phone);

