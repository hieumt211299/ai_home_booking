import sqlite3
import json
import os
import chromadb
from chromadb.utils import embedding_functions

DB_FILE = "homestay.db"
CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "homestay_rag"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

def get_chroma_collection():
    """Khởi tạo ChromaDB lưu trữ persistent và dùng model paraphrase-multilingual-MiniLM-L12-v2"""
    # Khởi tạo embedding function bằng sentence-transformers
    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=MODEL_NAME
    )
    
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=emb_fn,
        metadata={"hnsw:space": "cosine"} # Tính độ tương đồng theo Cosine Similarity
    )
    return collection

def build_vector_store():
    """Đọc dữ liệu từ SQLite, thực hiện Semantic Chunking và lưu vào ChromaDB"""
    print(f"🚀 Đang tải mô hình Embedding '{MODEL_NAME}' và chuẩn bị dữ liệu...")
    collection = get_chroma_collection()

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Chunking dữ liệu Homestays (Không gian, Vibe, Trải nghiệm)
    cursor.execute("SELECT * FROM homestays WHERE status = 'ACTIVE'")
    homes = cursor.fetchall()

    documents = []
    metadatas = []
    ids = []

    for h in homes:
        amenities = json.loads(h['amenities']) if h['amenities'] else []
        amenities_text = ", ".join(amenities)

        # Chunk mô tả không gian & trải nghiệm (Vibe Chunk)
        vibe_text = (
            f"Tên căn: {h['name']}. Thành phố: {h['city']}, Quận/Khu vực: {h['district']}. "
            f"Vị trí: {h['address']}. Điểm nổi bật lân cận: {h['landmark']}. "
            f"Sức chứa: {h['max_guests']} người ({h['num_bedrooms']} phòng ngủ, {h['num_beds']} giường). "
            f"Giá: {int(h['price_per_night']):,} VNĐ/đêm. "
            f"Tiện nghi: {amenities_text}. "
            f"Mô tả không gian và trải nghiệm: {h['description']}"
        )

        documents.append(vibe_text)
        metadatas.append({
            "homestay_id": h["id"],
            "name": h["name"],
            "city": h["city"],
            "type": "vibe",
            "price": float(h["price_per_night"]),
            "has_bathtub": bool(h["has_bathtub"]),
            "allows_pets": bool(h["allows_pets"]),
            "has_swimming_pool": bool(h["has_swimming_pool"])
        })
        ids.append(f"vibe_{h['id']}")

    # 2. Chunking dữ liệu Chính sách & Nội quy (Policy Chunks)
    cursor.execute("""
        SELECT p.id, p.homestay_id, h.name as home_name, h.city, p.topic, p.title, p.content 
        FROM homestay_policies p
        JOIN homestays h ON p.homestay_id = h.id
    """)
    policies = cursor.fetchall()

    for p in policies:
        policy_text = (
            f"Chính sách của homestay '{p['home_name']}' tại {p['city']}. "
            f"Chủ đề: {p['title']} ({p['topic']}). "
            f"Nội dung quy định: {p['content']}"
        )

        documents.append(policy_text)
        metadatas.append({
            "homestay_id": p["homestay_id"],
            "name": p["home_name"],
            "city": p["city"],
            "type": "policy",
            "topic": p["topic"]
        })
        ids.append(f"policy_{p['id']}")

    conn.close()

    print(f"📦 Đang nạp {len(documents)} chunks (50 Vibe Chunks + {len(policies)} Policy Chunks) vào ChromaDB...")
    
    # Xoá collection cũ nếu có và ghi lại
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(model_name=MODEL_NAME),
        metadata={"hnsw:space": "cosine"}
    )

    # Thêm batch vào vector db
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

    print("✅ Đã tạo Vector Store thành công và lưu tại thư mục ./chroma_db !")

def search_vibe(query, city=None, top_k=3, candidate_ids=None):
    """
    Tìm kiếm cảm xúc, không gian trải nghiệm (VD: 'gần biển', 'lãng mạn săn mây', 'view biển hoàng hôn').
    Nếu có candidate_ids (tập ID đã được lọc cứng trước từ SQL), Vector DB sẽ chỉ xếp hạng trên tập ID này.
    """
    collection = get_chroma_collection()
    
    where_filter = {"type": "vibe"}
    if city:
        where_filter = {
            "$and": [
                {"type": "vibe"},
                {"city": city}
            ]
        }

    query_params = {
        "query_texts": [query],
        "where": where_filter
    }

    # Nếu có tập ID ứng viên từ SQL (Pre-filtering)
    if candidate_ids:
        vibe_ids = [f"vibe_{cid}" for cid in candidate_ids]
        query_params["ids"] = vibe_ids
        query_params["n_results"] = min(len(vibe_ids), top_k)
    else:
        query_params["n_results"] = top_k

    results = collection.query(**query_params)
    return results

def search_policy(query, homestay_id=None, top_k=2):
    """Tìm kiếm quy định/chính sách (VD: 'mang chó có phụ thu không', 'huỷ phòng trước 3 ngày')"""
    collection = get_chroma_collection()

    where_filter = {"type": "policy"}
    if homestay_id:
        where_filter = {
            "$and": [
                {"type": "policy"},
                {"homestay_id": homestay_id}
            ]
        }

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where=where_filter
    )
    return results

if __name__ == "__main__":
    build_vector_store()

