from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.recommendations import RecommendationsOut
from app.services.recommendations import get_recommendations

router = APIRouter(tags=["recommendations"])


@router.get("/recommendations", response_model=RecommendationsOut)
async def recommendations(current_user: CurrentUser, db: DbSession):
    return await get_recommendations(db, current_user)
