from fastapi import APIRouter, Depends, HTTPException, Request

from auth.schemas import AuthDataCreateDTO
from sqlalchemy.ext.asyncio import AsyncSession
from config import settings
from auth.service import SteamAuthService
from database import get_async_session

router = APIRouter(
    prefix="/api/auth",
    tags=["steam_auth"]
)

@router.get("/steam")
async def steam_login():
    return SteamAuthService.create_auth_url(settings.STEAM_REDIRECT_URI)

@router.get("/steam/callback")
async def steam_callback(request: Request, session: AsyncSession = Depends(get_async_session)):
    '''
        Handles original steam auth, and saves auth data to database
    '''
    params = request.query_params
    
    openid_claimed_id = params.get("openid.claimed_id")
    if not openid_claimed_id:
        raise HTTPException(status_code=400, detail="Missing openid.claimed_id parameter")

    steam_id = openid_claimed_id.split("/")[-1]
    user_ip = request.client.host

    player = await SteamAuthService.get_steam_user_data(steam_id, settings.STEAM_API_KEY)
    username = player["personaname"]

    auth_data = AuthDataCreateDTO(user_ip=user_ip, steam_id=steam_id, username=username, domain_id=1) # CSMONEY IS DOMAIN "1"

    await SteamAuthService(session).save_auth_data(auth_data)

    return {"status": "success"}