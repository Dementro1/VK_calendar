import requests
import logging
from src.core.config import settings

logger = logging.getLogger(__name__)

class VKClient:
    def __init__(self):
        self.base_url = "https://api.vk.com/method/"
        self.token = settings.VK_GROUP_TOKEN
        self.api_version = settings.VK_API_VERSION

    # Отправка сообщения пользователю VK. Возвращает ответ API в виде словаря
    def send_message(self, user_vk_id: int, message: str) -> dict:
        url = f"{self.base_url}messages.send"
        params = {
            "user_id": user_vk_id,
            "message": message,
            "access_token": self.token,
            "v": self.api_version,
            "random_id": 0,
        }

        try:
            response = requests.post(url, data=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                error_msg = data["error"].get("error_msg", "Unknown VK error")
                logger.error(f"VK API error for user {user_vk_id}: {error_msg}")
                return {"error": error_msg}
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending to {user_vk_id}: {str(e)}")
            raise