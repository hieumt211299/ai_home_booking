import json
import httpx
from datetime import datetime
from dotenv import dotenv_values
import db_helper
import rag_manager

# =========================================================================
# 1. ĐỊNH NGHĨA DANH SÁCH TOOLS (JSON SCHEMA) CHO GOOGLE GEMINI
# =========================================================================
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_homestays",
            "description": "Tra cứu danh sách homestay trong database theo thành phố, quận, tên căn, sức chứa, ngân sách, ngày còn trống và tiện nghi. ĐẶC BIỆT: Hỗ trợ tìm phòng rẻ nhất / đắt nhất (bằng tham số sort_by='price_asc' hoặc 'price_desc') và giới hạn số lượng kết quả (limit).",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Tên thành phố: 'Đà Lạt', 'TP. Hồ Chí Minh', hoặc 'Vũng Tàu'"
                    },
                    "district": {
                        "type": "string",
                        "description": "Quận, huyện hoặc khu vực cụ thể (ví dụ: 'Quận 1', 'Quận 2', 'Bình Thạnh', 'Phường 5', 'Bãi Sau'...)"
                    },
                    "name": {
                        "type": "string",
                        "description": "Tên hoặc từ khóa tên homestay cần tìm (ví dụ: 'Secret Garden', 'Mây Mù', 'Zen Villa')"
                    },
                    "query": {
                        "type": "string",
                        "description": "Địa danh hoặc từ khóa tìm kiếm (ví dụ: 'gần trung tâm', 'Hồ Xuân Hương', 'Landmark 81')"
                    },
                    "min_capacity": {
                        "type": "integer",
                        "description": "Sức chứa tối thiểu mà khách cần (Khách đi 8 người thì truyền 8. Database sẽ tìm các căn có sức chứa >= 8, tức căn 8, 10, 12 người đều nhận được)."
                    },
                    "has_bathtub": {
                        "type": "boolean",
                        "description": "True nếu khách yêu cầu có bồn tắm"
                    },
                    "allows_pets": {
                        "type": "boolean",
                        "description": "True nếu khách mang theo thú cưng (chó, mèo)"
                    },
                    "has_swimming_pool": {
                        "type": "boolean",
                        "description": "True nếu yêu cầu có hồ bơi"
                    },
                    "has_bbq": {
                        "type": "boolean",
                        "description": "True nếu yêu cầu có bếp hoặc sân nướng BBQ"
                    },
                    "min_price": {
                        "type": "number",
                        "description": "Mức giá tối thiểu 1 đêm (VNĐ). Ví dụ: khách nói 'từ 700k', 'trên 1 triệu' thì truyền 700000 hoặc 1000000."
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Mức giá tối đa 1 đêm (VNĐ). Ví dụ: khách nói 'dưới 1 triệu', 'tầm 1tr5 đổ lại', 'tối đa 2 triệu' thì truyền 1000000, 1500000 hoặc 2000000."
                    },
                    "check_in": {
                        "type": "string",
                        "description": "Ngày nhận phòng (YYYY-MM-DD). Nếu khách chỉ hỏi 1 ngày cụ thể (ví dụ 15/11), truyền ngày đó vào check_in."
                    },
                    "check_out": {
                        "type": "string",
                        "description": "Ngày trả phòng (YYYY-MM-DD). Nếu khách thuê 1 đêm hoặc chỉ hỏi 1 ngày, truyền ngày kế tiếp vào check_out."
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["price_asc", "price_desc"],
                        "description": "Sắp xếp theo giá: 'price_asc' (giá từ thấp đến cao, BẮT BUỘC dùng khi khách hỏi tìm phòng rẻ nhất, giá thấp nhất), 'price_desc' (giá từ cao đến thấp)."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Số lượng homestay tối đa cần lấy. MẶC ĐỊNH LÀ 10 để tránh tốn token. Có thể giảm xuống 3 khi khách tìm 'phòng rẻ nhất', hoặc tăng/giảm theo yêu cầu cụ thể của khách."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_homestay_details",
            "description": "Lấy thông tin chi tiết đầy đủ (địa chỉ, sức chứa, giá, mô tả, chính sách) của một homestay theo ID HOẶC THEO TÊN CĂN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "homestay_id": {
                        "type": "integer",
                        "description": "ID số của homestay (nếu đã biết chính xác ID)"
                    },
                    "homestay_name": {
                        "type": "string",
                        "description": "Tên của homestay cần tra cứu (ví dụ: 'EkkoStay Secret Garden', 'Secret Garden', 'Zen Villa'). Dùng khi khách nhắc đến tên mà chưa rõ ID, KHÔNG ĐƯỢC TỰ ĐOÁN ID!"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_booking",
            "description": "Tạo đơn đặt phòng cho khách trong Database. Hãy gọi tool này ngay khi khách cung cấp thông tin đặt phòng (Tên căn, Ngày nhận/trả, Tên khách, SĐT, Số lượng khách).",
            "parameters": {
                "type": "object",
                "properties": {
                    "homestay_id": {
                        "type": "integer",
                        "description": "ID số của homestay cần đặt (nếu đã biết)"
                    },
                    "homestay_name": {
                        "type": "string",
                        "description": "Tên của homestay cần đặt (ví dụ: 'EkkoStay Secret Garden') nếu chưa biết ID"
                    },
                    "customer_name": {
                        "type": "string",
                        "description": "Họ và tên của khách hàng"
                    },
                    "customer_phone": {
                        "type": "string",
                        "description": "Số điện thoại liên hệ của khách hàng"
                    },
                    "check_in": {
                        "type": "string",
                        "description": "Ngày nhận phòng (YYYY-MM-DD)"
                    },
                    "check_out": {
                        "type": "string",
                        "description": "Ngày trả phòng (YYYY-MM-DD)"
                    },
                    "num_guests": {
                        "type": "integer",
                        "description": "Số lượng khách ở"
                    }
                },
                "required": ["customer_name", "customer_phone", "check_in", "check_out"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_booking",
            "description": "Hủy đơn đặt phòng trong Database bằng Mã đặt phòng (HB-xxxx) và Số điện thoại khách.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_code": {
                        "type": "string",
                        "description": "Mã đặt phòng cần hủy (ví dụ: HB-1001)"
                    },
                    "customer_phone": {
                        "type": "string",
                        "description": "Số điện thoại lúc đặt phòng để xác thực"
                    }
                },
                "required": ["booking_code", "customer_phone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ask_homestay_policy",
            "description": "Tra cứu các chính sách, nội quy chuỗi homestay (chính sách huỷ cọc, phụ phí thú cưng, giờ check-in/out, bãi đỗ xe ô tô, tiệc BBQ) bằng RAG.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Câu hỏi chi tiết về chính sách hoặc quy định cần tra cứu"
                    },
                    "homestay_id": {
                        "type": "integer",
                        "description": "ID của homestay cụ thể nếu khách đang hỏi riêng căn đó (tùy chọn)"
                    }
                },
                "required": ["question"]
            }
        }
    }
]

# =========================================================================
# 2. QUẢN LÝ PHIÊN HỘI THOẠI (SESSION STATE)
# =========================================================================
class SessionState:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages = []  # Danh sách message chuẩn OpenAI: [{"role": ..., "content": ...}]
        self.detected_profile = {"name": None, "phone": None}
        self.pending_booking = None  # Lưu trữ đơn nháp đang chờ khách xác nhận (HITL Interceptor)

    def to_dict(self):
        user_msgs = [m for m in self.messages if m.get("role") == "user"]
        return {
            "session_id": self.session_id,
            "detected_profile": self.detected_profile,
            "total_turns": len(user_msgs),
            "pending_booking": self.pending_booking
        }

# =========================================================================
# 3. HOMESTAY AGENT RE-ACT ENGINE
# =========================================================================
class HomestayAgent:
    def __init__(self):
        self.sessions: dict[str, SessionState] = {}
        env = dotenv_values(".env")
        self.api_key = env.get("GOOGLE_API_KEY", "")
        self.base_url = env.get("GOOGLE_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/").rstrip("/")
        self.model = env.get("GOOGLE_MODEL", "gemini-3.1-flash-lite")

    def get_or_create_session(self, session_id: str = None) -> SessionState:
        s_id = session_id or "default_session"
        if s_id not in self.sessions:
            self.sessions[s_id] = SessionState(s_id)
        return self.sessions[s_id]

    def reset_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
        return self.get_or_create_session(session_id)

    def execute_tool(self, tool_name: str, args: dict, session: SessionState = None):
        """Thực thi hàm Python tương ứng khi LLM quyết định gọi Tool"""
        if tool_name == "search_homestays":
            return db_helper.search_homestays(**args)
        elif tool_name == "get_homestay_details":
            h_id = args.get("homestay_id")
            h_name = args.get("homestay_name")
            return db_helper.get_homestay_details(homestay_id=h_id, name=h_name)
        elif tool_name == "create_booking":
            # -------------------------------------------------------------
            # [HUMAN-IN-THE-LOOP INTERCEPTOR Ở TẦNG BACKEND PYTHON]
            # -------------------------------------------------------------
            # Nếu session có đơn pending và khách đã bấm nút xác nhận hoặc nói đồng ý:
            is_confirmed = False
            if session and session.pending_booking and session.pending_booking.get("is_confirmed"):
                is_confirmed = True

            # Nếu CHƯA ĐƯỢC XÁC NHẬN BỞI CON NGƯỜI:
            # Code Python CHẶN ĐỨNG việc ghi vào DB, chỉ tính toán và tạo bản nháp!
            if not is_confirmed:
                # 1. Tra cứu chi tiết homestay để tính tiền thật
                h_info = db_helper.get_homestay_details(
                    homestay_id=args.get("homestay_id"),
                    name=args.get("homestay_name")
                )
                if not h_info or "error" in h_info:
                    return {"success": False, "message": f"Không tìm thấy homestay để đặt phòng."}

                # 1.1. KIỂM TRA SỨC CHỨA CỦA PHÒNG:
                num_guests = args.get("num_guests", 2)
                if num_guests > h_info["max_guests"]:
                    # Tự động tìm ngay các căn rộng hơn thỏa mãn số lượng khách tại cùng thành phố
                    alt_homes = db_helper.search_homestays(
                        city=h_info.get("city"),
                        min_capacity=num_guests,
                        limit=3
                    )
                    alt_list = alt_homes.get("items", []) if isinstance(alt_homes, dict) else []
                    alt_names = [f"**{h['name']}** (Sức chứa tối đa: {h['max_guests']} người, Giá: {h['price_per_night']:,}đ/đêm)" for h in alt_list]
                    alt_msg = ""
                    if alt_names:
                        alt_msg = f"\n\n👉 Em xin gợi ý ngay các căn khác rộng hơn phù hợp cho đoàn {num_guests} người tại {h_info.get('city')}:\n- " + "\n- ".join(alt_names)
                    
                    return {
                        "success": False,
                        "error_type": "CAPACITY_EXCEEDED",
                        "message": f"Căn '{h_info['name']}' chỉ nhận tối đa {h_info['max_guests']} khách, trong khi đoàn của bạn gồm {num_guests} khách.{alt_msg}\n\nBạn có muốn đổi sang đặt một trong các căn rộng rãi phía trên không ạ?"
                    }

                # 2. Tính số đêm và tổng tiền
                cin = db_helper.parse_date_input(args.get("check_in"))
                cout = db_helper.parse_date_input(args.get("check_out"))
                nights = 1
                try:
                    d1 = datetime.strptime(cin, "%Y-%m-%d")
                    d2 = datetime.strptime(cout, "%Y-%m-%d")
                    nights = max((d2 - d1).days, 1)
                except Exception:
                    pass

                total_price = nights * h_info["price_per_night"]

                # 3. Lưu thông tin bản nháp vào Session
                draft_data = {
                    "homestay_id": h_info["id"],
                    "homestay_name": h_info["name"],
                    "customer_name": args.get("customer_name"),
                    "customer_phone": args.get("customer_phone"),
                    "check_in": cin,
                    "check_out": cout,
                    "num_guests": num_guests,
                    "nights": nights,
                    "total_price": total_price,
                    "is_confirmed": False
                }
                if session:
                    session.pending_booking = draft_data

                # 4. Trả về tín hiệu INTERCEPTED cho LLM biết cần người dùng xác nhận
                return {
                    "status": "REQUIRES_HUMAN_CONFIRMATION",
                    "draft_booking": draft_data,
                    "message": "Đơn đặt phòng đang ở trạng thái BẢN NHÁP. Yêu cầu bạn trình bày tóm tắt đơn phòng cho khách hàng và xin ý kiến xác nhận của khách (Ví dụ khách nói 'Đồng ý' hoặc 'Xác nhận'). TUYỆT ĐỐI CHƯA ĐƯỢC BÁO LÀ ĐÃ ĐẶT THÀNH CÔNG VÌ CHƯA GHI VÀO DATABASE."
                }

            # NẾU ĐÃ CÓ XÁC NHẬN CỦA HUMAN: Thực hiện ghi CSDL thật!
            res = db_helper.create_booking(
                homestay_id=args.get("homestay_id") or session.pending_booking.get("homestay_id"),
                homestay_name=args.get("homestay_name") or session.pending_booking.get("homestay_name"),
                customer_name=args.get("customer_name") or session.pending_booking.get("customer_name"),
                customer_phone=args.get("customer_phone") or session.pending_booking.get("customer_phone"),
                check_in=args.get("check_in") or session.pending_booking.get("check_in"),
                check_out=args.get("check_out") or session.pending_booking.get("check_out"),
                num_guests=args.get("num_guests") or session.pending_booking.get("num_guests", 2)
            )
            # Reset lại pending booking sau khi đặt thành công
            if session:
                session.pending_booking = None
            return res

        elif tool_name == "cancel_booking":
            return db_helper.cancel_booking(
                booking_code=args.get("booking_code"),
                customer_phone=args.get("customer_phone")
            )
        elif tool_name == "ask_homestay_policy":
            q = args.get("question", "")
            h_id = args.get("homestay_id")
            rag_res = rag_manager.search_policy(query=q, homestay_id=h_id, top_k=2)
            if rag_res and rag_res.get("documents") and rag_res["documents"][0]:
                return {"policies_found": rag_res["documents"][0]}
            return {"policies_found": ["Chính sách chuỗi: Check-in 14:00, Check-out 12:00, cọc 50%, huỷ trước 5 ngày hoàn 100% cọc."]}
        else:
            return {"error": f"Tool '{tool_name}' không tồn tại"}

    def _safe_post_api(self, client: httpx.Client, url: str, headers: dict, payload: dict) -> dict:
        """Gửi request đến Gemini API và xử lý lỗi phản hồi an toàn (tránh lỗi TypeError khi Google trả về list error)"""
        r = client.post(url, headers=headers, json=payload)
        try:
            data = r.json()
        except Exception:
            data = r.text

        if r.status_code != 200:
            err_msg = ""
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                err_msg = data[0].get("error", {}).get("message", str(data[0]))
            elif isinstance(data, dict) and "error" in data:
                err_msg = data["error"].get("message", str(data["error"]))
            else:
                err_msg = str(data)

            if r.status_code == 402:
                raise RuntimeError(
                    f"Google API [402 - Hết credits/hạn mức]: {err_msg}. "
                    f"Vui lòng nạp thêm credit tại Google AI Studio hoặc tạo API Key mới từ project miễn phí (Free Tier)."
                )
            raise RuntimeError(f"Google API [{r.status_code}]: {err_msg}")

        if not isinstance(data, dict) or "choices" not in data or not data["choices"]:
            raise RuntimeError(f"Google API trả về định dạng không hợp lệ: {data}")

        return data

    def process_message(self, user_text: str, session_id: str = "default_session"):
        session = self.get_or_create_session(session_id)
        traces = []

        # [HITL BACKEND CHECK]: Nếu đang có đơn nháp và khách gửi tín hiệu đồng ý/xác nhận
        confirm_keywords = ["đồng ý", "xác nhận", "ok", "đúng rồi", "chuẩn rồi", "đặt đi", "chốt", "yes", "confirm"]
        user_clean = user_text.strip().lower()
        if session.pending_booking and any(kw in user_clean for kw in confirm_keywords):
            session.pending_booking["is_confirmed"] = True

        # Lưu tin nhắn mới của người dùng vào phiên
        session.messages.append({"role": "user", "content": user_text})

        now = datetime.now()
        weekdays_vn = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
        weekday_name = weekdays_vn[now.weekday()]
        current_time_str = f"{weekday_name}, ngày {now.strftime('%d/%m/%Y')}"

        # System prompt định nghĩa Persona và Quy tắc nghiêm ngặt chống bịa đặt
        system_prompt = f"""Bạn là trợ lý ảo lễ tân chuyên nghiệp, thông minh, trung thực và thân thiện của chuỗi homestay EkkoStay (50 căn tại Đà Lạt, TP. Hồ Chí Minh và Vũng Tàu).

THỜI ĐIỂM HIỆN TẠI: Hôm nay là {current_time_str} (Năm hiện tại: {now.year}).

QUY TẮC RẤT QUAN TRỌNG VỀ PHONG CÁCH VÀ DỮ LIỆU:
1. TRÌNH BÀY TÊN HOMESTAY TỰ NHIÊN, CHUYÊN NGHIỆP:
   - Hiển thị tên homestay một cách tự nhiên và trang nhã (ví dụ: "**EkkoStay Secret Garden - Biệt Thự Vườn Cổ Tích**").
   - TUYỆT ĐỐI KHÔNG HIỂN THỊ MÃ ID NỘI BỘ (như [ID: 15], [ID: 9]) cho khách hàng, vì mã ID là thông số kỹ thuật nội bộ của hệ thống, không có ý nghĩa với trải nghiệm của khách.

2. TRA CỨU HOẶC ĐẶT PHÒNG THEO TÊN CĂN:
   - Khi khách yêu cầu kiểm tra hoặc đặt phòng theo tên (ví dụ: 'đặt EkkoStay Secret Garden', 'kiểm tra lại thông tin Secret Garden'):
     👉 BẠN PHẢI GỌI TOOL `get_homestay_details(homestay_name='EkkoStay Secret Garden')` hoặc `search_homestays(name='Secret Garden')` để tra cứu thông tin chính xác.
     👉 TUYỆT ĐỐI KHÔNG TỰ TIỆN ĐOÁN BỪA ID (không tự gán ID 1) khi chưa tra cứu!
     👉 TUYỆT ĐỐI KHÔNG BỊA ĐẶT TÊN CĂN HOẶC NÓI SAI SỰ THẬT.

3. QUY TẮC BẮT BUỘC VỀ SỐ LƯỢNG NGƯỜI (SỨC CHỨA - RẤT QUAN TRỌNG):
   - NGUYÊN TẮC TIÊN QUYẾT: ĐỂ TRÁNH TÌNH TRẠNG KHÁCH CHỌN PHÒNG NHỎ RỒI ĐẾN BƯỚC ĐẶT PHÒNG BỊ QUÁ TẢI SỨC CHỨA, BẠN PHẢI LUÔN HỎI SỐ LƯỢNG NGƯỜI NGAY TỪ ĐẦU!
   - NẾU KHÁCH CHƯA CUNG CẤP SỐ NGƯỜI (Ví dụ: khách hỏi 'tìm homestay Đà Lạt', 'giá phòng Vũng Tàu bao nhiêu', 'tìm phòng dưới 1 triệu', 'có căn nào gần biển không'):
     👉 BẮT BUỘC PHẢI HỎI NGAY số lượng người trong câu trả lời đầu tiên!
     👉 Mẫu câu tự nhiên: "Dạ đoàn mình dự kiến đi bao nhiêu người (người lớn và trẻ em) để em lọc chính xác các căn có sức chứa phù hợp nhất cho đoàn mình ạ?"
     👉 Bạn CÓ THỂ giới thiệu sơ lược 2-3 căn tiêu biểu nhưng BẮT BUỘC kèm theo câu hỏi số lượng người để tư vấn chuẩn xác.
   - KHI KHÁCH ĐÃ CUNG CẤP SỐ NGƯỜI (Ví dụ: 'đi 4 người', 'đoàn 6 người', '2 người lớn 1 bé'):
     👉 BẮT BUỘC truyền `min_capacity = N` vào tool `search_homestays` để database loại bỏ toàn bộ các căn có sức chứa nhỏ hơn, chỉ lấy các căn có sức chứa >= N!
   - KHI LỠ XẢY RA QUÁ TẢI SỨC CHỨA Ở BƯỚC ĐẶT PHÒNG:
     👉 Tool `create_booking` sẽ tự động trả về danh sách các căn rộng hơn có sức chứa đủ cho đoàn.
     👉 Bạn hãy giải thích lịch sự lý do căn khách chọn không đủ chỗ và gợi ý ngay các căn rộng hơn được cung cấp để mời khách đổi sang, TUYỆT ĐỐI KHÔNG chỉ nói cụt lủn bắt khách tự tìm lại!

4. VỀ NGÂN SÁCH (BUDGET / KHOẢNG GIÁ):
   - Khi khách nói về ngân sách hoặc khoảng giá (ví dụ: 'từ 500k đến 1 triệu', 'dưới 800k', 'tối đa 1tr5', 'tầm 2 triệu đổ lại'):
     👉 Hãy tự động quy đổi sang số tiền VNĐ (500k = 500000, 1 triệu = 1000000, 1tr5 = 1500000).
     👉 Truyền vào `min_price` (giá tối thiểu) và `max_price` (giá tối đa) trong tool `search_homestays`.

5. ĐA NGÔN NGỮ (Multilingual): Tự động nhận diện và trả lời bằng đúng ngôn ngữ của khách.

6. ĐẶT PHÒNG VÀ HUMAN-IN-THE-LOOP:
   - Khi khách yêu cầu đặt phòng và cung cấp thông tin (Tên căn, Ngày nhận/trả, Tên khách, SĐT, Số lượng khách), hãy gọi tool `create_booking`.
   - Nếu tool trả về trạng thái `REQUIRES_HUMAN_CONFIRMATION` (Bản nháp được Backend chặn lại để chờ xác nhận): Bạn hãy trình bày một phiếu tóm tắt đơn phòng rõ ràng từ dữ liệu draft và lịch sự mời khách kiểm tra và xác nhận (ví dụ 'Đồng ý đặt' hoặc 'Xác nhận'). Tuyệt đối chưa chúc mừng hay báo đặt phòng thành công.
   - Khi khách đã xác nhận và tool `create_booking` trả về `success: true` kèm mã booking: Lúc này mới thông báo mã đặt phòng và chúc khách có chuyến đi vui vẻ.

7. TUYỆT ĐỐI KHÔNG CẬP NHẬT ĐƠN PHÒNG QUA CHATBOT (CHÍNH SÁCH BẢO MẬT):
   - Chuỗi EkkoStay KHÔNG CHO PHÉP chỉnh sửa thông tin đơn đặt phòng (như đổi ngày, đổi tên khách, đổi số người, đổi căn) trực tiếp qua Chatbot AI nhằm tránh sai sót và bảo mật dữ liệu.
   - TUYỆT ĐỐI KHÔNG ĐƯỢC BÁO 'ĐÃ CẬP NHẬT THÀNH CÔNG' hay 'ĐÃ SỬA THÀNH CÔNG'.
   - Khi khách yêu cầu sửa thông tin, dời ngày hay thay đổi booking:
     👉 BẠN PHẢI TỪ CHỐI LỊCH SỰ VÀ HƯỚNG DẪN KHÁCH VÀO APP:
     "Dạ để đảm bảo tính an toàn và bảo mật cho đơn phòng của bạn, hệ thống Chatbot hiện chưa hỗ trợ thao tác chỉnh sửa trực tiếp thông tin đơn đặt phòng đã xác nhận. Bạn vui lòng truy cập ứng dụng EkkoStay (App) vào mục 'Quản lý đặt phòng' để thao tác chỉnh sửa trực tiếp, hoặc tiến hành huỷ đơn cũ và đặt lại đơn mới giúp em nhé ạ!"

8. QUY TẮC XỬ LÝ THỜI GIAN, LỊCH TRỐNG VÀ GIÁ CẢ:
   - XỬ LÝ THỜI GIAN TƯƠNG ĐỐI ('cuối tuần này', 'ngày mai', 'tuần sau'):
     👉 Luôn căn cứ vào ngày hôm nay ({current_time_str}) để tính ra ngày chính xác dạng YYYY-MM-DD.
     👉 Nếu khách nói 'cuối tuần này': Hãy tính ngày Thứ Bảy gần nhất của tuần này làm ngày check_in, Chủ Nhật làm ngày check_out (hoặc Thứ Hai nếu khách thuê 2 đêm).
     👉 Nếu khách nói ngày không kèm năm (ví dụ '15/11', '20/12'): Tự động lấy năm hiện tại ({now.year}) -> YYYY-MM-DD.
   - XỬ LÝ KHI KHÁCH HỎI 1 NGÀY CÒN TRỐNG (Ví dụ: 'Ngày 15/11 còn phòng không?'):
     👉 Mặc định hiểu là khách thuê 1 đêm: truyền `check_in='{now.year}-11-15'` và `check_out='{now.year}-11-16'` vào tool `search_homestays`.
     👉 Trong câu trả lời, nói rõ: "Dạ em đã kiểm tra các phòng còn trống cho 1 đêm từ 15/11 đến 16/11...".
   - XỬ LÝ KHI KHÁCH CHỈ NÓI SỐ NGÀY (Ví dụ: 'Tôi muốn thuê 3 ngày 2 đêm', 'cần phòng 2 ngày'):
     👉 Nếu khách CHƯA CUNG CẤP ngày bắt đầu đi: Đừng tự đoán ngày, hãy lịch sự hỏi lại khách dự kiến đi vào ngày nào để bạn kiểm tra phòng trống chính xác nhất.
     👉 Nếu khách ĐÃ CÓ ngày nhận phòng kèm số đêm: Tự động tính ngày check_out bằng cách cộng thêm số đêm vào ngày check_in.
   - XỬ LÝ KHI KHÁCH TÌM PHÒNG GIÁ RẺ NHẤT / TIẾT KIỆM NHẤT:
     👉 BẮT BUỘC truyền `sort_by='price_asc'` và `limit=3` vào tool `search_homestays`.
     👉 Luôn nêu rõ mức giá phòng/đêm để khách dễ so sánh và lựa chọn."""

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Tạo danh sách messages gửi cho Gemini
        # Giới hạn 12 messages gần nhất để tránh quá dài
        recent_messages = session.messages[-12:]
        api_messages = [{"role": "system", "content": system_prompt}] + recent_messages

        payload = {
            "model": self.model,
            "messages": api_messages,
            "tools": AGENT_TOOLS,
            "tool_choice": "auto",
            "temperature": 0.4
        }

        final_text = ""
        try:
            with httpx.Client(timeout=35.0) as client:
                # Lần gọi 1: Gemini quyết định gọi Tool hay trả lời trực tiếp
                resp = self._safe_post_api(client, url, headers, payload)
                choice = resp["choices"][0]
                message = choice["message"]

                # Nếu Gemini quyết định gọi TOOL
                if message.get("tool_calls"):
                    tool_calls = message["tool_calls"]
                    api_messages.append(message)

                    for tc in tool_calls:
                        fn_name = tc["function"]["name"]
                        try:
                            fn_args = json.loads(tc["function"]["arguments"])
                        except Exception:
                            fn_args = {}
                        tc_id = tc.get("id", "call_1")

                        # Ghi nhận vào Trace UI
                        traces.append({
                            "stage": f"🔧 LLM GỌI TOOL: {fn_name}()",
                            "type": "tool",
                            "title": f"Gemini tự động trích xuất tham số & gọi {fn_name}()",
                            "data": {
                                "tool": fn_name,
                                "arguments": fn_args
                            }
                        })

                        # Thực thi Tool thật trong Database / RAG (có truyền session để kiểm tra Human Confirmation)
                        raw_output = self.execute_tool(fn_name, fn_args, session=session)

                        # Tách phần vector_trace (nếu có) để hiển thị riêng trên UI Inspector
                        clean_output = raw_output
                        if isinstance(raw_output, dict) and "_vector_trace" in raw_output:
                            v_trace = raw_output["_vector_trace"]
                            clean_output = raw_output.get("items", [])
                            if v_trace:
                                traces.append({
                                    "stage": "⚡ VECTOR SEMANTIC RE-RANKING",
                                    "type": "vector",
                                    "title": f"ChromaDB tính Cosine Similarity cho '{v_trace.get('vibe_query')}' trên {v_trace.get('candidate_pool_size')} căn SQL hợp lệ",
                                    "data": v_trace
                                })

                        # Ghi nhận kết quả Tool vào Trace UI
                        traces.append({
                            "stage": f"📊 KẾT QUẢ TỪ DATABASE",
                            "type": "result",
                            "title": f"Dữ liệu thực tế từ {fn_name}()",
                            "data": clean_output
                        })

                        # Gửi kết quả Tool về lại cho Gemini (gửi danh sách sạch)
                        api_messages.append({
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "content": json.dumps(clean_output, ensure_ascii=False)
                        })

                    # Lần gọi 2: Gemini đọc dữ liệu thật từ DB và biên tập câu trả lời chuẩn xác
                    followup_payload = {
                        "model": self.model,
                        "messages": api_messages,
                        "temperature": 0.4
                    }
                    resp2 = self._safe_post_api(client, url, headers, followup_payload)
                    final_text = resp2["choices"][0]["message"]["content"]
                    
                    traces.append({
                        "stage": f"🤖 LLM TỔNG HỢP ({self.model})",
                        "type": "result",
                        "title": "Gemini phản hồi dựa trên dữ liệu thật",
                        "data": {
                            "usage": resp2.get("usage", {}),
                            "response_preview": final_text[:200] + "..."
                        }
                    })

                else:
                    final_text = message["content"]
                    traces.append({
                        "stage": f"💬 LLM GIAO TIẾP TRỰC TIẾP",
                        "type": "info",
                        "title": "Gemini phản hồi trực tiếp không cần gọi Tool",
                        "data": {"content": final_text[:200] + "..."}
                    })

        except Exception as e:
            final_text = f"Dạ em xin lỗi, kết nối AI gặp trục trặc: {str(e)}"
            traces.append({
                "stage": "❌ LỖI HỆ THỐNG",
                "type": "result",
                "title": "Lỗi API",
                "data": {"error": str(e)}
            })

        # Lưu câu trả lời của AI vào phiên
        session.messages.append({"role": "assistant", "content": final_text})

        return {
            "response": final_text,
            "traces": traces,
            "session": session.to_dict()
        }

agent = HomestayAgent()
