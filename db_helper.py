import sqlite3
import random
import string
from datetime import datetime, timedelta
import json

DB_FILE = "homestay.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Cho phép truy cập cột theo tên (như dictionary)
    return conn

def parse_date_input(val, reference_date=None):
    """
    Chuẩn hoá các định dạng ngày hoặc từ ngữ chỉ thời gian sang định dạng chuẩn YYYY-MM-DD.
    Hỗ trợ: 'YYYY-MM-DD', 'DD/MM/YYYY', 'DD-MM-YYYY', 'DD/MM', 'DD-MM',
    'hôm nay', 'ngày mai', 'ngày mốt'/'ngày kia', 'cuối tuần này'.
    """
    if not val or not isinstance(val, str):
        return None

    val = val.strip().lower()
    ref = reference_date or datetime.now()

    if val in ["hôm nay", "today"]:
        return ref.strftime("%Y-%m-%d")
    elif val in ["ngày mai", "tomorrow", "mai"]:
        return (ref + timedelta(days=1)).strftime("%Y-%m-%d")
    elif val in ["ngày mốt", "ngày kia", "mốt"]:
        return (ref + timedelta(days=2)).strftime("%Y-%m-%d")
    elif "cuối tuần" in val:
        days_ahead = (5 - ref.weekday()) % 7
        sat = ref + timedelta(days=days_ahead)
        return sat.strftime("%Y-%m-%d")

    # Thử parse các format chuẩn có năm
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"]:
        try:
            return datetime.strptime(val, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Thử parse format không có năm DD/MM hoặc DD-MM -> gán năm hiện tại
    for fmt in ["%d/%m", "%d-%m"]:
        try:
            dt = datetime.strptime(val, fmt)
            return dt.replace(year=ref.year).strftime("%Y-%m-%d")
        except ValueError:
            pass

    return val

def search_homestays(
    city=None,
    district=None,
    name=None,
    query=None,
    check_in=None,
    check_out=None,
    min_capacity=None,
    num_guests=None,
    has_bathtub=None,
    allows_pets=None,
    has_kitchen=None,
    has_swimming_pool=None,
    has_bbq=None,
    min_price=None,
    max_price=None,
    sort_by=None,
    limit=10
):
    """
    Tìm kiếm homestay theo vị trí, tiện nghi, sức chứa, ngân sách (giá tối thiểu / tối đa) và ngày còn trống.
    """
    conn = get_connection()
    cursor = conn.cursor()

    conditions = ["status = 'ACTIVE'"]
    params = []

    if city:
        conditions.append("city LIKE ?")
        params.append(f"%{city}%")

    if district:
        conditions.append("(district LIKE ? OR address LIKE ?)")
        params.extend([f"%{district}%", f"%{district}%"])

    if name:
        conditions.append("name LIKE ?")
        params.append(f"%{name}%")

    # Sức chứa: khách đi N người thì tìm các căn có sức chứa tối đa >= N
    required_capacity = min_capacity if min_capacity is not None else num_guests
    if required_capacity:
        conditions.append("max_guests >= ?")
        params.append(required_capacity)

    if has_bathtub is not None:
        conditions.append("has_bathtub = ?")
        params.append(1 if has_bathtub else 0)

    if allows_pets is not None:
        conditions.append("allows_pets = ?")
        params.append(1 if allows_pets else 0)

    if has_kitchen is not None:
        conditions.append("has_kitchen = ?")
        params.append(1 if has_kitchen else 0)

    if has_swimming_pool is not None:
        conditions.append("has_swimming_pool = ?")
        params.append(1 if has_swimming_pool else 0)

    if has_bbq is not None:
        conditions.append("has_bbq = ?")
        params.append(1 if has_bbq else 0)

    if min_price is not None:
        conditions.append("price_per_night >= ?")
        params.append(min_price)

    if max_price is not None:
        conditions.append("price_per_night <= ?")
        params.append(max_price)

    # Chuẩn hoá ngày nhận / trả phòng tự động
    if check_in:
        check_in = parse_date_input(check_in)
    if check_out:
        check_out = parse_date_input(check_out)

    # Nếu có ngày check_in nhưng chưa có check_out, mặc định tính thuê 1 đêm
    if check_in and not check_out:
        try:
            cin_dt = datetime.strptime(check_in, "%Y-%m-%d")
            check_out = (cin_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        except Exception:
            pass

    # Nếu có ngày check-in và check-out, lọc loại trừ các phòng đã có người đặt
    if check_in and check_out:
        conditions.append("""
            id NOT IN (
                SELECT homestay_id FROM bookings
                WHERE status = 'CONFIRMED'
                  AND check_in < ?
                  AND check_out > ?
            )
        """)
        params.extend([check_out, check_in])

    query_sql = f"SELECT * FROM homestays WHERE {' AND '.join(conditions)}"

    # Hỗ trợ sắp xếp theo giá (price_asc / price_desc)
    if sort_by == "price_asc":
        query_sql += " ORDER BY price_per_night ASC"
    elif sort_by == "price_desc":
        query_sql += " ORDER BY price_per_night DESC"

    # Áp dụng giới hạn số lượng kết quả (mặc định limit = 10 nếu không truyền)
    effective_limit = limit if limit and isinstance(limit, int) else 10

    # Nếu không có query vector re-ranking thì giới hạn số lượng trực tiếp trong câu SQL
    if not query:
        query_sql += f" LIMIT {effective_limit}"

    cursor.execute(query_sql, params)
    rows = cursor.fetchall()

    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "name": r["name"],
            "city": r["city"],
            "district": r["district"],
            "address": r["address"],
            "landmark": r["landmark"],
            "max_guests": r["max_guests"],
            "num_bedrooms": r["num_bedrooms"],
            "price_per_night": r["price_per_night"],
            "has_bathtub": bool(r["has_bathtub"]),
            "allows_pets": bool(r["allows_pets"]),
            "has_kitchen": bool(r["has_kitchen"]),
            "has_swimming_pool": bool(r["has_swimming_pool"]),
            "has_bbq": bool(r["has_bbq"]),
            "amenities": json.loads(r["amenities"]) if r["amenities"] else [],
            "description": r["description"]
        })

    conn.close()

    vector_trace = None

    # BƯỚC 2: NẾU CÓ THAM SỐ QUERY -> DÙNG CHROMADB VECTOR SEARCH ĐỂ XẾP HẠNG NGỮ NGHĨA TRÊN TẬP KẾT QUẢ SQL
    if query and results:
        try:
            import rag_manager
            candidate_ids = [r["id"] for r in results]
            # Gọi Vector search chỉ trên tập ID hợp lệ đã được lọc cứng từ SQL (giới hạn theo effective_limit)
            top_n = min(len(candidate_ids), effective_limit)
            vibe_res = rag_manager.search_vibe(
                query=query,
                city=city,
                top_k=top_n,
                candidate_ids=candidate_ids
            )
            if vibe_res and vibe_res.get("metadatas") and vibe_res["metadatas"][0]:
                ordered_ids = [m["homestay_id"] for m in vibe_res["metadatas"][0]]
                distances = vibe_res.get("distances", [[]])[0]
                
                # Ghi nhận chi tiết kết quả Vector Re-ranking cho Trace UI
                vector_trace = {
                    "vibe_query": query,
                    "candidate_pool_size": len(candidate_ids),
                    "candidate_ids": candidate_ids,
                    "re_ranked_ranking": [
                        {
                            "homestay_id": m.get("homestay_id"),
                            "name": m.get("name"),
                            "city": m.get("city"),
                            "cosine_distance": round(distances[idx], 4) if idx < len(distances) else None
                        }
                        for idx, m in enumerate(vibe_res["metadatas"][0])
                    ]
                }

                # Sắp xếp lại danh sách results theo đúng thứ tự điểm tương đồng của Vector DB
                results_map = {r["id"]: r for r in results}
                ranked_results = []
                for oid in ordered_ids:
                    if oid in results_map:
                        ranked_results.append(results_map[oid])
                return {"items": ranked_results, "_vector_trace": vector_trace}
        except Exception:
            # Fallback nếu Vector DB gặp lỗi thì vẫn trả về kết quả lọc của SQL
            pass

    return {"items": results, "_vector_trace": None}

def get_homestay_details(homestay_id=None, name=None):
    """Lấy thông tin chi tiết của 1 homestay theo ID hoặc theo TÊN (hỗ trợ tìm kiếm theo tên khi khách không nhớ ID)."""
    conn = get_connection()
    cursor = conn.cursor()

    home = None
    if homestay_id is not None:
        try:
            h_id = int(homestay_id)
            cursor.execute("SELECT * FROM homestays WHERE id = ?", (h_id,))
            home = cursor.fetchone()
        except ValueError:
            # Nếu LLM truyền tên vào biến homestay_id
            cursor.execute("SELECT * FROM homestays WHERE name LIKE ?", (f"%{homestay_id}%",))
            home = cursor.fetchone()

    if not home and name:
        cursor.execute("SELECT * FROM homestays WHERE name LIKE ?", (f"%{name}%",))
        home = cursor.fetchone()

    if not home:
        conn.close()
        return {"error": f"Không tìm thấy homestay với thông tin '{homestay_id or name}'"}

    home_data = dict(home)
    home_data["amenities"] = json.loads(home["amenities"]) if home["amenities"] else []

    cursor.execute("SELECT topic, title, content FROM homestay_policies WHERE homestay_id = ?", (home_data["id"],))
    policies = [dict(p) for p in cursor.fetchall()]
    home_data["policies"] = policies

    conn.close()
    return home_data

def ask_homestay_policy(homestay_id=None, keyword=None):
    """
    Tra cứu chính sách (huỷ phòng, thú cưng, BBQ, giờ giấc) của homestay.
    Đóng vai trò RAG / Knowledge Base đơn giản.
    """
    conn = get_connection()
    cursor = conn.cursor()

    sql = """
        SELECT h.name as homestay_name, p.homestay_id, p.topic, p.title, p.content 
        FROM homestay_policies p
        JOIN homestays h ON p.homestay_id = h.id
        WHERE 1=1
    """
    params = []

    if homestay_id:
        sql += " AND p.homestay_id = ?"
        params.append(homestay_id)

    if keyword:
        sql += " AND (p.title LIKE ? OR p.content LIKE ? OR p.topic LIKE ?)"
        term = f"%{keyword}%"
        params.extend([term, term, term])

    cursor.execute(sql, params)
    policies = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return policies

def create_booking(homestay_id=None, homestay_name=None, customer_name=None, customer_phone=None, check_in=None, check_out=None, num_guests=2):
    """Tạo booking mới nếu phòng còn trống trong khoảng ngày (hỗ trợ tìm căn theo ID hoặc theo Tên)."""
    conn = get_connection()
    cursor = conn.cursor()

    home = None
    if homestay_id is not None:
        try:
            h_id = int(homestay_id)
            cursor.execute("SELECT id, name, max_guests, price_per_night FROM homestays WHERE id = ? AND status = 'ACTIVE'", (h_id,))
            home = cursor.fetchone()
        except ValueError:
            cursor.execute("SELECT id, name, max_guests, price_per_night FROM homestays WHERE name LIKE ? AND status = 'ACTIVE'", (f"%{homestay_id}%",))
            home = cursor.fetchone()

    if not home and homestay_name:
        cursor.execute("SELECT id, name, max_guests, price_per_night FROM homestays WHERE name LIKE ? AND status = 'ACTIVE'", (f"%{homestay_name}%",))
        home = cursor.fetchone()

    if not home:
        conn.close()
        return {"success": False, "message": f"Không tìm thấy Homestay với thông tin '{homestay_id or homestay_name}'"}

    actual_homestay_id = home["id"]

    if num_guests > home["max_guests"]:
        conn.close()
        return {"success": False, "message": f"Căn này chỉ chứa tối đa {home['max_guests']} người (bạn yêu cầu {num_guests} người)."}

    # 2. Kiểm tra trùng lịch
    cursor.execute("""
        SELECT COUNT(*) as count FROM bookings
        WHERE homestay_id = ?
          AND status = 'CONFIRMED'
          AND check_in < ?
          AND check_out > ?
    """, (actual_homestay_id, check_out, check_in))
    if cursor.fetchone()["count"] > 0:
        conn.close()
        return {"success": False, "message": "Phòng đã có người đặt trong khoảng thời gian này, vui lòng chọn ngày hoặc phòng khác."}

    # 3. Tính tổng tiền (số ngày * giá 1 đêm)
    d1 = datetime.strptime(check_in, "%Y-%m-%d")
    d2 = datetime.strptime(check_out, "%Y-%m-%d")
    nights = (d2 - d1).days
    if nights <= 0:
        conn.close()
        return {"success": False, "message": "Ngày check-out phải sau ngày check-in ít nhất 1 đêm."}

    total_price = nights * home["price_per_night"]

    # 4. Sinh mã đặt phòng duy nhất: VD: HB-4821
    random_code = "".join(random.choices(string.digits, k=4))
    booking_code = f"HB-{random_code}"

    cursor.execute("""
        INSERT INTO bookings (booking_code, homestay_id, customer_name, customer_phone, check_in, check_out, num_guests, total_price, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'CONFIRMED')
    """, (booking_code, actual_homestay_id, customer_name, customer_phone, check_in, check_out, num_guests, total_price))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "booking_code": booking_code,
        "homestay_name": home["name"],
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "check_in": check_in,
        "check_out": check_out,
        "nights": nights,
        "total_price": total_price,
        "message": f"Đặt phòng thành công! Mã booking của bạn là {booking_code}."
    }

def get_booking_details(booking_code, customer_phone):
    """Tra cứu booking theo mã và số điện thoại."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT b.*, h.name as homestay_name, h.address
        FROM bookings b
        JOIN homestays h ON b.homestay_id = h.id
        WHERE b.booking_code = ? AND b.customer_phone = ?
    """, (booking_code, customer_phone))

    row = cursor.fetchone()
    conn.close()
    if not row:
        return {"success": False, "message": "Không tìm thấy thông tin đặt phòng khớp với mã booking và số điện thoại này."}
    return {"success": True, "booking": dict(row)}

def cancel_booking(booking_code, customer_phone):
    """Huỷ booking."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, status FROM bookings 
        WHERE booking_code = ? AND customer_phone = ?
    """, (booking_code, customer_phone))

    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"success": False, "message": "Không tìm thấy booking hoặc số điện thoại không khớp."}

    if row["status"] == "CANCELLED":
        conn.close()
        return {"success": False, "message": "Đơn đặt phòng này trước đó đã được huỷ rồi."}

    cursor.execute("UPDATE bookings SET status = 'CANCELLED' WHERE id = ?", (row["id"],))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Đã huỷ thành công đơn đặt phòng {booking_code}!"}

