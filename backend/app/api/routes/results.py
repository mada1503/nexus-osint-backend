"""Placeholder routes — Results."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/{job_id}")
async def get_results(job_id: str):
    """Placeholder — see /api/search/status/{task_id} for results."""
    return {"message": f"Results for job {job_id} — see /api/search/status/{{task_id}}"}
