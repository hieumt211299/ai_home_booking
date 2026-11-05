import os
import json
import sys
import argparse
import webbrowser
import httpx
import uvicorn
from typing import Optional
from fastapi import FastAPI, Request, Query, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from pydantic import BaseModel
from dotenv import dotenv_values
from agent_engine import agent

app = FastAPI(title="EkkoStay AI Chatbot & Agent Inspector")

# =========================================================================
# FACEBOOK MESSENGER HELPER FUNCTIONS & PER-PSID LOGGING
# =========================================================================
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "fb_chats")
os.makedirs(LOGS_DIR, exist_ok=True)
fb_message_logs = []

def save_fb_session_log(sender_id: str, user_message: str, ai_response: str, traces: list, session_info: dict):
    """Lưu toàn bộ lịch sử hội thoại và AI Thought Flow theo từng Facebook PSID ra file JSON."""
    from datetime import datetime
    file_path = os.path.join(LOGS_DIR, f"{sender_id}.json")
    data = {
        "sender_id": sender_id,
        "customer_name": None,
        "customer_phone": None,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "turns": []
    }
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
                if isinstance(existing, dict):
                    data["turns"] = existing.get("turns", [])
                    data["customer_name"] = existing.get("customer_name")
                    data["customer_phone"] = existing.get("customer_phone")
        except Exception as e:
            print(f"[LOG_ERROR] Lỗi đọc {file_path}: {e}")

    profile = session_info.get("detected_profile", {}) if session_info else {}
    if profile.get("name"):
        data["customer_name"] = profile["name"]
    if profile.get("phone"):
        data["customer_phone"] = profile["phone"]

    turn_data = {
        "turn": len(data["turns"]) + 1,
        "time": datetime.now().strftime("%H:%M:%S %d/%m/%Y"),
        "user_message": user_message,
        "ai_response": ai_response,
        "traces": traces,
        "session": session_info
    }
    data["turns"].append(turn_data)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[LOG_ERROR] Lỗi ghi {file_path}: {e}")

async def send_fb_message(recipient_id: str, text: str):
    """Gửi tin nhắn phản hồi về Facebook Messenger qua Graph API."""
    env = dotenv_values(".env")
    page_access_token = env.get("FB_PAGE_ACCESS_TOKEN", "").strip()
    if not page_access_token:
        print("[FB_WEBHOOK] ⚠️ Chưa cấu hình FB_PAGE_ACCESS_TOKEN trong file .env! Vui lòng thêm token để bot có thể trả lời tin nhắn.")
        return

    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={page_access_token}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                print(f"[FB_WEBHOOK] ❌ Lỗi gửi tin: {resp.status_code} - {resp.text}")
            else:
                print(f"[FB_WEBHOOK] ✅ Đã gửi tin nhắn phản hồi tới PSID {recipient_id}")
        except Exception as e:
            print(f"[FB_WEBHOOK] ❌ Ngoại lệ khi gửi tin Facebook: {e}")

def handle_fb_message_bg(sender_id: str, text: str):
    """Xử lý tin nhắn ngầm với AI Agent và gửi lại cho khách hàng."""
    from datetime import datetime
    now_str = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    
    print("\n" + "═" * 80)
    print(f"📩 [FACEBOOK MESSENGER] TIN NHẮN TỪ KHÁCH HÀNG ({now_str})")
    print(f"👤 Facebook PSID: {sender_id}")
    print(f"💬 Nội dung: \"{text}\"")
    print("─" * 80)

    try:
        # Tự động phục hồi bộ nhớ từ file JSON nếu server vừa khởi động lại
        session = agent.get_or_create_session(f"fb_{sender_id}")
        if not session.messages:
            file_path = os.path.join(LOGS_DIR, f"{sender_id}.json")
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        saved = json.load(f)
                        for t in saved.get("turns", []):
                            if t.get("user_message"):
                                session.messages.append({"role": "user", "content": t["user_message"]})
                            if t.get("ai_response"):
                                session.messages.append({"role": "assistant", "content": t["ai_response"]})
                        if saved.get("customer_name"):
                            session.detected_profile["name"] = saved["customer_name"]
                        if saved.get("customer_phone"):
                            session.detected_profile["phone"] = saved["customer_phone"]
                except Exception:
                    pass

        # Gán sender_id (PSID) làm session_id để AI ghi nhớ ngữ cảnh riêng cho từng người
        res = agent.process_message(text, session_id=f"fb_{sender_id}")
        reply_text = res.get("response", "")
        traces = res.get("traces", [])
        session_info = res.get("session", {})

        print("🧠 [AI THOUGHT FLOW - TIẾN TRÌNH XỬ LÝ]:")
        for idx, t in enumerate(traces, 1):
            stage = t.get("stage", "STAGE")
            title = t.get("title", "")
            print(f"   [{idx}] {stage} ➔ {title}")
            data = t.get("data")
            if data:
                try:
                    data_str = json.dumps(data, ensure_ascii=False)
                    if len(data_str) > 220:
                        data_str = data_str[:217] + "..."
                    print(f"       Chi tiết: {data_str}")
                except Exception:
                    pass

        print("─" * 80)
        print(f"🤖 [AI PHẢN HỒI LẠI KHÁCH]:\n{reply_text}")
        print("─" * 80)

        # Lưu log theo từng Facebook PSID ra ổ cứng
        save_fb_session_log(sender_id, text, reply_text, traces, session_info)

        # Lưu vào danh sách log gần nhất
        log_entry = {
            "id": len(fb_message_logs) + 1,
            "time": datetime.now().strftime("%H:%M:%S"),
            "sender_id": sender_id,
            "user_message": text,
            "response": reply_text,
            "traces": traces,
            "session": session_info
        }
        fb_message_logs.insert(0, log_entry)
        if len(fb_message_logs) > 50:
            fb_message_logs.pop()

        if reply_text:
            import asyncio
            asyncio.run(send_fb_message(sender_id, reply_text))

    except Exception as e:
        print(f"[FB_WEBHOOK] ❌ Lỗi xử lý Agent: {e}")

    print("═" * 80 + "\n")

# =========================================================================
# FACEBOOK MESSENGER WEBHOOK ENDPOINTS
# =========================================================================
@app.get("/webhook")
def fb_verify(
    mode: Optional[str] = Query(None, alias="hub.mode"),
    token: Optional[str] = Query(None, alias="hub.verify_token"),
    challenge: Optional[str] = Query(None, alias="hub.challenge")
):
    """Facebook gọi GET để xác thực webhook handshake."""
    env = dotenv_values(".env")
    expected_token = env.get("FB_VERIFY_TOKEN", "ekko_stay_token_2026").strip()

    if mode == "subscribe" and token == expected_token:
        print(f"[FB_WEBHOOK] ✅ Xác thực Webhook Meta thành công! (Challenge: {challenge})")
        return PlainTextResponse(content=challenge, status_code=200)

    print(f"[FB_WEBHOOK] ❌ Xác thực thất bại! Nhận được: '{token}', Kỳ vọng: '{expected_token}'")
    raise HTTPException(status_code=403, detail="Verification token mismatch")

@app.post("/webhook")
async def fb_webhook_receiver(request: Request, bg_tasks: BackgroundTasks):
    """Facebook gửi POST chứa tin nhắn và sự kiện của người dùng."""
    try:
        data = await request.json()
    except Exception:
        return PlainTextResponse("EVENT_RECEIVED", status_code=200)

    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event.get("sender", {}).get("id")
                message = messaging_event.get("message", {})

                # Bỏ qua tin nhắn do chính page gửi lại (echo) hoặc không phải tin nhắn text
                if message.get("is_echo"):
                    continue

                text = message.get("text")
                if sender_id and text:
                    print(f"[FB_WEBHOOK] 📩 Nhận tin nhắn từ Facebook PSID {sender_id}: {text}")
                    bg_tasks.add_task(handle_fb_message_bg, sender_id, text)

        return PlainTextResponse("EVENT_RECEIVED", status_code=200)

    return PlainTextResponse("NOT_A_PAGE", status_code=404)

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default_session"

class ResetRequest(BaseModel):
    session_id: Optional[str] = "default_session"

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    result = agent.process_message(req.message, req.session_id)
    return result

@app.post("/api/reset")
def reset_endpoint(req: ResetRequest):
    agent.reset_session(req.session_id)
    return {"status": "success", "message": "Đã làm mới phiên hội thoại thành công!"}

@app.get("/api/fb_logs")
def get_fb_logs():
    return {"logs": fb_message_logs}

@app.get("/api/fb/sessions")
def list_fb_sessions():
    """Lấy danh sách tất cả các phiên chat của khách theo từng Facebook PSID."""
    sessions = []
    if not os.path.exists(LOGS_DIR):
        return {"sessions": []}
    for fname in sorted(os.listdir(LOGS_DIR), reverse=True):
        if fname.endswith(".json"):
            fpath = os.path.join(LOGS_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    turns = d.get("turns", [])
                    last_msg = turns[-1]["user_message"] if turns else ""
                    last_reply = turns[-1]["ai_response"] if turns else ""
                    last_time = turns[-1]["time"] if turns else d.get("updated_at", "")
                    sessions.append({
                        "sender_id": d.get("sender_id", fname.replace(".json", "")),
                        "customer_name": d.get("customer_name") or "Khách Messenger",
                        "customer_phone": d.get("customer_phone") or "Chưa có",
                        "total_turns": len(turns),
                        "last_message": last_msg,
                        "last_reply": last_reply,
                        "last_time": last_time
                    })
            except Exception:
                continue
    return {"sessions": sessions}

@app.get("/api/fb/session/{sender_id}")
def get_fb_session_detail(sender_id: str):
    """Lấy chi tiết toàn bộ lịch sử tin nhắn và AI thought flow của một Facebook PSID."""
    fpath = os.path.join(LOGS_DIR, f"{sender_id}.json")
    if os.path.exists(fpath):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=404, detail="Không tìm thấy phiên của PSID này")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EkkoStay AI Agent Inspector & Tester</title>
    <style>
        :root {
            --primary: #2563eb;
            --primary-light: #eff6ff;
            --bg: #0f172a;
            --panel-bg: #ffffff;
            --border: #e2e8f0;
            --text-main: #1e293b;
            --text-muted: #64748b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
        html, body { height: 100%; height: 100vh; overflow: hidden; background: #f1f5f9; }
        body { display: flex; flex-direction: column; }

        /* Custom Scrollbar */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.04); }
        ::-webkit-scrollbar-thumb { background: #94a3b8; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #64748b; }

        .inspector-container ::-webkit-scrollbar-track { background: #090d16; }
        .inspector-container ::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
        .inspector-container ::-webkit-scrollbar-thumb:hover { background: #475569; }

        /* Header */
        header { height: 56px; flex-shrink: 0; background: #ffffff; border-bottom: 1px solid var(--border); padding: 0 24px; display: flex; justify-content: space-between; align-items: center; z-index: 10; }
        .logo { font-size: 17px; font-weight: 700; color: #0f172a; display: flex; align-items: center; gap: 8px; }
        .header-actions { display: flex; align-items: center; gap: 12px; }
        .btn-reset { background: #f1f5f9; border: 1px solid #cbd5e1; color: #475569; padding: 6px 14px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px; transition: all 0.2s; }
        .btn-reset:hover { background: #fee2e2; border-color: #ef4444; color: #dc2626; }
        .badge-status { background: #dcfce7; color: #166534; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 999px; }
        .btn-fb { background: #0084ff; color: #ffffff; border: none; padding: 6px 14px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px; transition: all 0.2s; box-shadow: 0 1px 3px rgba(0,132,255,0.3); }
        .btn-fb:hover { background: #006bce; }

        /* Workspace */
        .workspace { flex: 1 1 0%; min-height: 0; display: flex; overflow: hidden; }

        /* Left: Chat Area */
        .chat-container { flex: 0 0 55%; width: 55%; display: flex; flex-direction: column; height: 100%; min-height: 0; border-right: 1px solid var(--border); background: #ffffff; }
        .chat-messages { flex: 1 1 0%; min-height: 0; overflow-y: auto; overflow-x: hidden; padding: 20px; display: flex; flex-direction: column; gap: 16px; scroll-behavior: smooth; }
        
        .message { display: flex; flex-direction: column; max-width: 85%; line-height: 1.5; font-size: 14px; }
        .msg-user { align-self: flex-end; }
        .msg-user .bubble { background: var(--primary); color: #ffffff; border-radius: 16px 16px 2px 16px; padding: 12px 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); word-break: break-word; }
        .msg-bot { align-self: flex-start; }
        .msg-bot .bubble { background: #f8fafc; color: var(--text-main); border: 1px solid var(--border); border-radius: 16px 16px 16px 2px; padding: 14px 18px; white-space: pre-wrap; word-break: break-word; }
        .msg-meta { font-size: 11px; color: var(--text-muted); margin-top: 4px; }
        .msg-user .msg-meta { text-align: right; }

        .suggestions { flex-shrink: 0; padding: 10px 20px; display: flex; gap: 8px; overflow-x: auto; background: #ffffff; border-top: 1px solid #f1f5f9; }
        .chip { background: #f1f5f9; border: 1px solid #cbd5e1; padding: 6px 12px; border-radius: 999px; font-size: 12px; color: #334155; cursor: pointer; white-space: nowrap; transition: all 0.2s; }
        .chip:hover { background: #e2e8f0; border-color: var(--primary); color: var(--primary); }

        .chat-input-area { flex-shrink: 0; padding: 14px 20px; background: #ffffff; border-top: 1px solid var(--border); display: flex; gap: 10px; }
        .input-box { flex: 1; padding: 12px 16px; border: 1px solid #cbd5e1; border-radius: 10px; font-size: 14px; outline: none; }
        .input-box:focus { border-color: var(--primary); }
        .btn-send { background: var(--primary); color: white; border: none; padding: 0 24px; border-radius: 10px; font-weight: 600; cursor: pointer; transition: opacity 0.2s; }
        .btn-send:hover { opacity: 0.9; }

        /* Right: Inspector */
        .inspector-container { flex: 0 0 45%; width: 45%; display: flex; flex-direction: column; height: 100%; min-height: 0; background: #0f172a; color: #f8fafc; }
        .inspector-header { height: 48px; flex-shrink: 0; padding: 0 20px; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; background: #1e293b; }
        .inspector-title { font-size: 13px; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase; color: #94a3b8; display: flex; align-items: center; gap: 8px; }
        .inspector-body { flex: 1 1 0%; min-height: 0; overflow-y: auto; overflow-x: hidden; padding: 20px; display: flex; flex-direction: column; gap: 16px; scroll-behavior: smooth; }

        /* Session State Box */
        .memory-box { background: #1e293b; border: 1px solid #3b82f6; border-radius: 10px; padding: 14px; font-size: 13px; }
        .memory-title { font-weight: 700; color: #60a5fa; display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .memory-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px; }
        .memory-item { background: #090d16; padding: 6px 10px; border-radius: 6px; }
        .memory-label { color: #94a3b8; margin-bottom: 2px; }
        .memory-val { color: #f8fafc; font-weight: 600; }

        /* Trace Cards */
        .trace-card { background: #1e293b; border: 1px solid #334155; border-radius: 10px; overflow: hidden; flex-shrink: 0; }
        .trace-card-header { padding: 10px 14px; display: flex; justify-content: space-between; align-items: center; font-size: 13px; font-weight: 600; }
        .trace-card-body { padding: 12px 14px; font-size: 12px; border-top: 1px solid #334155; background: #090d16; }
        
        .badge-stage { font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 700; }
        .stage-nlu { background: #3b82f6; color: white; }
        .stage-tool { background: #f59e0b; color: black; }
        .stage-vector { background: #8b5cf6; color: white; }
        .stage-result { background: #10b981; color: white; }

        pre { font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; color: #38bdf8; font-size: 12px; line-height: 1.4; overflow-x: auto; white-space: pre-wrap; word-break: break-word; }
        .empty-inspector { text-align: center; color: #64748b; margin-top: 40px; font-size: 14px; }
    </style>
</head>
<body>

    <header>
        <div class="logo">
            🤖 EkkoStay AI Agent Inspector & Tester
        </div>
        <div class="header-actions">
            <div style="display: flex; align-items: center; gap: 8px;">
                <label style="font-size: 12px; font-weight: 600; color: #64748b;">Xem phiên:</label>
                <select id="sessionDropdown" onchange="onSessionChange(this.value)" style="padding: 6px 12px; border-radius: 6px; border: 1px solid #cbd5e1; font-size: 13px; font-weight: 600; color: #1e293b; background: #f8fafc; cursor: pointer; outline: none; max-width: 280px;">
                    <option value="__WEB_LOCAL__">💻 Web Tester (Trò chuyện cục bộ)</option>
                    <optgroup label="💬 Khách hàng Facebook Messenger" id="fbSessionOptions">
                    </optgroup>
                </select>
                <button onclick="refreshSessions()" title="Tải lại danh sách phiên" style="padding: 6px 10px; border-radius: 6px; border: 1px solid #cbd5e1; background: #ffffff; cursor: pointer; font-size: 12px; font-weight: 600; color: #334155;">🔄 Tải lại DS</button>
            </div>
            <button class="btn-fb" onclick="toggleFbModal()">
                💬 DS Khách FB (<span id="fbCountBadge">0</span>)
            </button>
            <button class="btn-reset" id="btnResetSession" onclick="resetConversation()">🔄 Làm mới chat</button>
            <span class="badge-status" id="activeBadge">● Web Test Mode</span>
        </div>
    </header>

    <!-- MODAL FACEBOOK LIVE MONITOR -->
    <div id="fbModal" style="display: none; position: fixed; inset: 0; background: rgba(15,23,42,0.6); z-index: 1000; align-items: center; justify-content: center;">
        <div style="background: white; width: 90%; max-width: 820px; max-height: 85vh; border-radius: 12px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.2);">
            <div style="padding: 16px 20px; background: #0f172a; color: white; display: flex; justify-content: space-between; align-items: center;">
                <div style="font-weight: 700; font-size: 15px; display: flex; align-items: center; gap: 8px;">
                    <span>💬 Tin Nhắn Facebook Messenger Thời Gian Thực</span>
                    <span id="fbModalCount" style="font-size: 11px; background: #0084ff; padding: 2px 8px; border-radius: 999px;">0 tin</span>
                </div>
                <button onclick="toggleFbModal()" style="background: none; border: none; color: #94a3b8; font-size: 22px; cursor: pointer; line-height: 1;">&times;</button>
            </div>
            <div id="fbLogsList" style="flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; background: #f8fafc;">
                <div style="text-align: center; color: #64748b; padding: 30px;">Chưa có tin nhắn nào từ Facebook. Hãy mở Messenger của Fanpage để chat thử!</div>
            </div>
        </div>
    </div>

    <div class="workspace">
        <!-- CHAT AREA -->
        <div class="chat-container">
            <div class="chat-messages" id="messagesList">
                <div class="message msg-bot">
                    <div class="bubble">Xin chào! Em là trợ lý ảo chuỗi homestay **EkkoStay**. 
Hệ thống hiện đã được nâng cấp **Bộ nhớ phiên (Session Memory)**: Em có thể ghi nhớ tên bạn, lưu giữ ngữ cảnh tìm kiếm qua nhiều câu hỏi liên tiếp! 
Bạn tên là gì và đang dự định đi đâu ạ?</div>
                    <div class="msg-meta">Hôm nay</div>
                </div>
            </div>

            <!-- GỢI Ý KỊCH BẢN TEST MULTI-TURN NHỚ TÊN & NGỮ CẢNH -->
            <div class="suggestions">
                <div class="chip" onclick="quickSend('Chào em, mình tên là Hiếu')">1️⃣ Chào em, mình tên là Hiếu</div>
                <div class="chip" onclick="quickSend('Tìm cho mình phòng ở Đà Lạt cho 2 người')">2️⃣ Tìm phòng ở Đà Lạt cho 2 người</div>
                <div class="chip" onclick="quickSend('Có căn nào có bồn tắm không em?')">3️⃣ Có căn nào có bồn tắm không?</div>
                <div class="chip" onclick="quickSend('Đổi sang căn cho mang cún đi bạn')">4️⃣ Đổi sang căn cho mang cún đi</div>
                <div class="chip" onclick="quickSend('Chốt đặt căn EkkoStay Secret Garden với SĐT 0912345678')">5️⃣ Chốt đặt EkkoStay Secret Garden (SĐT 0912345678)</div>
            </div>

            <div class="chat-input-area">
                <input type="text" id="userInput" class="input-box" placeholder="Nhập tin nhắn của bạn (hoặc bấm kịch bản gợi ý 1, 2, 3 phía trên)..." onkeydown="if(event.key==='Enter') sendMessage()">
                <button class="btn-send" id="btnSend" onclick="sendMessage()">Gửi tin</button>
            </div>
        </div>

        <!-- AI INSPECTOR & TRACE AREA -->
        <div class="inspector-container">
            <div class="inspector-header">
                <div class="inspector-title">
                    ⚡ Live AI Thought & Session Memory
                </div>
                <div id="sessionBadge" style="font-size: 12px; color: #38bdf8;">Session: Active</div>
            </div>
            
            <div class="inspector-body" id="inspectorBody">
                <!-- BOX BỘ NHỚ PHIÊN -->
                <div class="memory-box" id="memoryBox">
                    <div class="memory-title">
                        <span>🧠 BỘ NHỚ PHIÊN (SESSION MEMORY)</span>
                        <span id="turnCounter" style="font-size: 11px; background: #3b82f6; color: white; padding: 2px 6px; border-radius: 4px;">0 lượt chat</span>
                    </div>
                    <div class="memory-grid">
                        <div class="memory-item">
                            <div class="memory-label">👤 Tên khách</div>
                            <div class="memory-val" id="memName">Chưa nhận diện</div>
                        </div>
                        <div class="memory-item">
                            <div class="memory-label">📞 Số điện thoại</div>
                            <div class="memory-val" id="memPhone">Chưa có</div>
                        </div>
                        <div class="memory-item" style="grid-column: span 2;">
                            <div class="memory-label">📍 Ngữ cảnh tìm kiếm kế thừa</div>
                            <div class="memory-val" id="memContext">Chưa có bộ lọc</div>
                        </div>
                    </div>
                </div>

                <div id="traceCardsContainer">
                    <div class="empty-inspector">
                        👈 Hãy gửi tin nhắn bên khung chat để thấy AI ghi nhớ tên và kế thừa ngữ cảnh qua từng câu hỏi!
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Quản lý đa phiên (Web Test vs Facebook Messenger PSID)
        let currentSessionMode = '__WEB_LOCAL__';
        let webMessagesHTML = '';
        let webSessionMemory = null;
        let webTraces = [];
        let activeFbData = null;

        // Tạo hoặc lấy session_id duy nhất cho Web Tester
        let sessionId = localStorage.getItem('ekkostay_session_id');
        if (!sessionId) {
            sessionId = 'sess_' + Math.random().toString(36).substring(2, 9);
            localStorage.setItem('ekkostay_session_id', sessionId);
        }
        document.getElementById('sessionBadge').innerText = `Session: ${sessionId}`;

        async function updateSessionDropdown() {
            try {
                const res = await fetch('/api/fb/sessions');
                const data = await res.json();
                const optgroup = document.getElementById('fbSessionOptions');
                const badge = document.getElementById('fbCountBadge');
                if (!optgroup) return;

                const sessions = data.sessions || [];
                if (badge) badge.innerText = sessions.length;

                optgroup.innerHTML = sessions.map(s => {
                    const label = `${s.customer_name} (PSID: ...${s.sender_id.slice(-6)}) • ${s.total_turns} tin`;
                    const isSelected = (currentSessionMode === s.sender_id) ? 'selected' : '';
                    return `<option value="${s.sender_id}" ${isSelected}>👤 ${label}</option>`;
                }).join('');
            } catch (e) {
                console.error('Lỗi nạp danh sách sessions:', e);
            }
        }

        async function onSessionChange(val) {
            currentSessionMode = val;
            const input = document.getElementById('userInput');
            const btnSend = document.getElementById('btnSend');
            const suggestions = document.querySelector('.suggestions');
            const activeBadge = document.getElementById('activeBadge');
            const sessionBadge = document.getElementById('sessionBadge');
            const btnReset = document.getElementById('btnResetSession');

            if (val === '__WEB_LOCAL__') {
                activeBadge.innerText = '● Web Test Mode';
                activeBadge.style.background = '#dcfce7';
                activeBadge.style.color = '#166534';
                sessionBadge.innerText = `Session: ${sessionId}`;
                input.disabled = false;
                input.placeholder = "Nhập tin nhắn của bạn (hoặc bấm kịch bản gợi ý 1, 2, 3 phía trên)...";
                btnSend.disabled = false;
                if (suggestions) suggestions.style.display = 'flex';
                if (btnReset) btnReset.style.display = 'inline-flex';

                if (webMessagesHTML) {
                    document.getElementById('messagesList').innerHTML = webMessagesHTML;
                    updateMemoryBox(webSessionMemory);
                    renderTraces(webTraces);
                } else {
                    document.getElementById('messagesList').innerHTML = `
                        <div class="message msg-bot">
                            <div class="bubble">Xin chào! Em là trợ lý ảo chuỗi homestay **EkkoStay**. Bạn cần tìm homestay ở đâu ạ?</div>
                            <div class="msg-meta">Hôm nay</div>
                        </div>
                    `;
                    document.getElementById('traceCardsContainer').innerHTML = '<div class="empty-inspector">👈 Hãy gửi tin nhắn bên khung chat để thấy AI gọi Tool và suy nghĩ!</div>';
                }
            } else {
                activeBadge.innerText = `● Khách FB: ...${val.slice(-6)}`;
                activeBadge.style.background = '#dbeafe';
                activeBadge.style.color = '#1e40af';
                sessionBadge.innerText = `FB PSID: ${val}`;
                input.disabled = true;
                input.placeholder = `Đang xem lịch sử của Facebook PSID: ${val} (Tin nhắn mới sẽ tự động nạp)...`;
                btnSend.disabled = true;
                if (suggestions) suggestions.style.display = 'none';
                if (btnReset) btnReset.style.display = 'none';

                await loadFbSessionDetail(val);
            }
        }

        async function loadFbSessionDetail(senderId) {
            try {
                const res = await fetch(`/api/fb/session/${senderId}`);
                if (!res.ok) return;
                const data = await res.json();
                activeFbData = data;
                const turns = data.turns || [];

                const list = document.getElementById('messagesList');
                if (turns.length === 0) {
                    list.innerHTML = `<div class="empty-inspector">Khách chưa có tin nhắn nào.</div>`;
                    return;
                }

                list.innerHTML = turns.map((t, idx) => `
                    <div class="message msg-user">
                        <div class="bubble">${t.user_message}</div>
                        <div class="msg-meta">👤 Khách Messenger • ${t.time} (Lượt ${t.turn})</div>
                    </div>
                    <div class="message msg-bot">
                        <div class="bubble">${t.ai_response}</div>
                        <div class="msg-meta" style="display:flex; justify-content:space-between; align-items:center; margin-top:6px;">
                            <span>🤖 EkkoStay Assistant</span>
                            <button onclick="renderTurnTraces(${idx})" style="background:#0f172a; color:#38bdf8; border:1px solid #334155; padding:3px 8px; border-radius:4px; font-size:11px; cursor:pointer;">
                                ⚡ Xem AI Thought Lượt ${idx + 1}
                            </button>
                        </div>
                    </div>
                `).join('');
                list.scrollTop = list.scrollHeight;

                const latestTurn = turns[turns.length - 1];
                if (latestTurn) {
                    updateMemoryBox(latestTurn.session);
                    renderTraces(latestTurn.traces);
                }
            } catch (e) {
                console.error('Lỗi nạp chi tiết FB session:', e);
            }
        }

        function renderTurnTraces(turnIdx) {
            if (!activeFbData || !activeFbData.turns) return;
            const turn = activeFbData.turns[turnIdx];
            if (turn) {
                updateMemoryBox(turn.session);
                renderTraces(turn.traces);
                const title = document.querySelector('.inspector-title');
                if (title) {
                    title.innerHTML = `⚡ Live AI Thought (Lượt ${turnIdx + 1} - ${turn.time})`;
                }
            }
        }

        async function sendMessage() {
            const input = document.getElementById('userInput');
            const text = input.value.trim();
            if (!text) return;

            appendMessage('user', text);
            input.value = '';
            input.disabled = true;
            document.getElementById('btnSend').disabled = true;

            const traceContainer = document.getElementById('traceCardsContainer');
            traceContainer.innerHTML = '<div style="color: #38bdf8; text-align: center; margin-top: 20px;">⏳ Đang xử lý: Phân tích NLU & Kế thừa Session State...</div>';

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text, session_id: sessionId })
                });
                const data = await res.json();

                appendMessage('bot', data.response);

                // Cập nhật Box Bộ nhớ (Session Memory)
                updateMemoryBox(data.session);
                webSessionMemory = data.session;

                // Render Traces
                renderTraces(data.traces);
                webTraces = data.traces;

                webMessagesHTML = document.getElementById('messagesList').innerHTML;
            } catch (err) {
                appendMessage('bot', '❌ Lỗi kết nối: ' + err.message);
            } finally {
                input.disabled = false;
                document.getElementById('btnSend').disabled = false;
                input.focus();
            }
        }

        async function resetConversation() {
            try {
                await fetch('/api/reset', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: sessionId })
                });
                document.getElementById('messagesList').innerHTML = `
                    <div class="message msg-bot">
                        <div class="bubble">✨ Đã làm mới phiên hội thoại! Em đã xoá toàn bộ bộ nhớ cũ. Bạn cần tìm homestay ở đâu ạ?</div>
                        <div class="msg-meta">Hôm nay</div>
                    </div>
                `;
                webMessagesHTML = document.getElementById('messagesList').innerHTML;
                document.getElementById('memName').innerText = 'Chưa nhận diện';
                document.getElementById('memPhone').innerText = 'Chưa có';
                document.getElementById('memContext').innerText = 'Chưa có bộ lọc';
                document.getElementById('turnCounter').innerText = '0 lượt chat';
                document.getElementById('traceCardsContainer').innerHTML = '<div class="empty-inspector">Phiên làm việc đã được làm mới.</div>';
            } catch (err) {
                alert('Lỗi khi reset: ' + err.message);
            }
        }

        function updateMemoryBox(sess) {
            if (!sess) return;
            const profile = sess.detected_profile || {};
            const name = sess.customer_name || profile.name;
            const phone = sess.customer_phone || profile.phone;
            document.getElementById('memName').innerText = name ? name : 'Chưa nhận diện';
            document.getElementById('memPhone').innerText = phone ? phone : 'Chưa có';
            document.getElementById('turnCounter').innerText = `${sess.total_turns || 0} lượt chat`;

            const s = sess.current_search || {};
            const parts = [];
            if (s.city) parts.push(`TP: ${s.city}`);
            if (s.district) parts.push(`Khu vực: ${s.district}`);
            if (s.num_guests) parts.push(`${s.num_guests} khách`);
            if (s.has_bathtub) parts.push(`Có bồn tắm`);
            if (s.allows_pets) parts.push(`Nhận thú cưng`);
            if (s.has_pool) parts.push(`Có hồ bơi`);
            if (s.has_bbq) parts.push(`Có BBQ`);

            document.getElementById('memContext').innerText = parts.length > 0 ? parts.join(' • ') : 'Chưa có bộ lọc';
        }

        function quickSend(txt) {
            document.getElementById('userInput').value = txt;
            sendMessage();
        }

        function appendMessage(sender, text) {
            const list = document.getElementById('messagesList');
            const msgDiv = document.createElement('div');
            msgDiv.className = `message msg-${sender}`;
            const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            msgDiv.innerHTML = `
                <div class="bubble">${text}</div>
                <div class="msg-meta">${sender === 'user' ? 'Bạn' : 'EkkoStay Assistant'} • ${now}</div>
            `;
            list.appendChild(msgDiv);
            list.scrollTop = list.scrollHeight;
        }

        function renderTraces(traces) {
            const container = document.getElementById('traceCardsContainer');
            if (!traces || traces.length === 0) {
                container.innerHTML = '<div class="empty-inspector">Không có trace nào.</div>';
                return;
            }

            container.innerHTML = traces.map(t => {
                let badgeClass = 'stage-nlu';
                if (t.type === 'tool') badgeClass = 'stage-tool';
                if (t.type === 'vector') badgeClass = 'stage-vector';
                if (t.type === 'result') badgeClass = 'stage-result';

                return `
                    <div class="trace-card">
                        <div class="trace-card-header">
                            <div>
                                <span class="badge-stage ${badgeClass}">${t.stage}</span>
                                <span style="margin-left: 8px;">${t.title}</span>
                            </div>
                        </div>
                        <div class="trace-card-body">
                            <pre>${JSON.stringify(t.data, null, 2)}</pre>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // =========================================================================
        // REAL-TIME FACEBOOK MONITORING
        // =========================================================================
        let fbLogsData = [];
        function toggleFbModal() {
            const modal = document.getElementById('fbModal');
            const isOpening = (modal.style.display === 'none' || modal.style.display === '');
            modal.style.display = isOpening ? 'flex' : 'none';
            if (isOpening) {
                fetchFbLogs();
            }
        }

        async function fetchFbLogs() {
            try {
                const res = await fetch('/api/fb_logs');
                const data = await res.json();
                fbLogsData = data.logs || [];
                const modalCount = document.getElementById('fbModalCount');
                if (modalCount) modalCount.innerText = `${fbLogsData.length} tin`;

                if (fbLogsData.length > 0) {
                    const listEl = document.getElementById('fbLogsList');
                    listEl.innerHTML = fbLogsData.map((log, idx) => `
                        <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <span style="font-weight: 700; font-size: 13px; color: #0284c7;">👤 Khách Messenger (PSID: ${log.sender_id})</span>
                                <span style="font-size: 11px; color: #64748b; background: #f1f5f9; padding: 2px 6px; border-radius: 4px;">⏰ ${log.time}</span>
                            </div>
                            <div style="font-size: 13px; color: #1e293b; margin-bottom: 8px; background: #eff6ff; border-left: 3px solid #3b82f6; padding: 8px 12px; border-radius: 4px;">
                                <strong>Khách hỏi:</strong> ${log.user_message}
                            </div>
                            <div style="font-size: 13px; color: #334155; margin-bottom: 12px; white-space: pre-wrap; background: #f8fafc; padding: 8px 12px; border-radius: 4px; border: 1px solid #f1f5f9;">
                                <strong>AI trả lời:</strong> ${log.response}
                            </div>
                            <div style="display: flex; justify-content: flex-end; gap: 8px;">
                                <button onclick="selectAndInspectPsid('${log.sender_id}')" style="background: #2563eb; color: white; border: none; padding: 6px 14px; border-radius: 6px; font-size: 12px; cursor: pointer; font-weight: 600;">
                                    👉 Mở toàn bộ cuộc hội thoại của khách này
                                </button>
                            </div>
                        </div>
                    `).join('');
                }
            } catch (e) {
                // Silently ignore
            }
        }

        function selectAndInspectPsid(senderId) {
            toggleFbModal();
            const dropdown = document.getElementById('sessionDropdown');
            if (dropdown) {
                dropdown.value = senderId;
                onSessionChange(senderId);
            }
        }

        async function refreshSessions() {
            await updateSessionDropdown();
            if (currentSessionMode !== '__WEB_LOCAL__') {
                await loadFbSessionDetail(currentSessionMode);
            }
        }

        // Tải danh sách session một lần duy nhất khi mở trang (không polling ngầm)
        updateSessionDropdown();
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index_page():
    return HTML_TEMPLATE

def main():
    parser = argparse.ArgumentParser(description="EkkoStay AI Chatbot Tester")
    parser.add_argument("--ui", action="store_true", help="Khởi động giao diện Web UI và tự động mở trình duyệt")
    parser.add_argument("--port", type=int, default=8000, help="Cổng chạy server (mặc định 8000)")
    args = parser.parse_args()

    if args.ui:
        url = f"http://localhost:{args.port}"
        print("=" * 80)
        print(f"🚀 Đang khởi động EkkoStay AI Agent Inspector tại: {url}")
        print("💡 Đã tích hợp Session Memory & Lịch sử hội thoại đa lượt")
        print("=" * 80)
        webbrowser.open(url)
        uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    else:
        print("=" * 80)
        print("🤖 CHẾ ĐỘ TERMINAL CHAT (Mẹo: dùng 'python3 app.py --ui' để mở giao diện Web)")
        print("=" * 80)
        sess_id = "cli_session"
        while True:
            try:
                user_msg = input("\n👤 Bạn: ")
                if user_msg.strip().lower() in ["exit", "quit"]:
                    break
                res = agent.process_message(user_msg, sess_id)
                print(f"\n🤖 AI: {res['response']}")
            except (KeyboardInterrupt, EOFError):
                break

if __name__ == "__main__":
    main()
