"""Placeholder routes — Auth."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/me")
async def get_me():
    """Placeholder — authentication not yet implemented."""
    return {"message": "Auth not yet implemented. Use /api/search directly for now."}
