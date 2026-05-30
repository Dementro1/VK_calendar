from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me")
async def get_current_user():
    return {"id": 1, "vk_id": 12345, "timezone": "Europe/Moscow"} # Заглушка