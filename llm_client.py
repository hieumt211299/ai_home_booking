import httpx
from dotenv import dotenv_values

class LLMClient:
    def __init__(self):
        env = dotenv_values(".env")
        self.api_key = env.get("GOOGLE_API_KEY", "")
        self.base_url = env.get("GOOGLE_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/").rstrip("/")
        self.model = env.get("GOOGLE_MODEL", "gemini-3.1-flash-lite")

    def generate(self, messages: list[dict], system_prompt: str = None, temperature: float = 0.5) -> dict:
        """
        Gọi Gemini API qua endpoint chuẩn OpenAI-compatible.
        Trả về dict gồm: 'content', 'model', 'usage', 'success'
        """
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        
        full_messages.extend(messages)

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": full_messages,
            "temperature": temperature
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code != 200:
                    return {
                        "success": False,
                        "error": f"API Error {resp.status_code}: {resp.text}",
                        "content": None
                    }
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                return {
                    "success": True,
                    "content": content,
                    "model": data.get("model", self.model),
                    "usage": usage
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": None
            }

llm = LLMClient()

