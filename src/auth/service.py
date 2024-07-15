import logging
from sqlalchemy import insert
from sqlalchemy.exc import SQLAlchemyError
from tenacity import retry, wait_fixed, stop_after_attempt, retry_if_exception_type
import httpx
from fastapi import HTTPException

from auth.models import AuthData
from auth.schemas import AuthDataCreateDTO

logger = logging.getLogger(__name__)

class SteamAuthService:

    async def save_auth_data(self, auth_data: AuthDataCreateDTO):
        try:
            stmt = insert(AuthData).values(
                user_ip=auth_data.user_ip,
                steam_id=auth_data.steam_id,
                username=auth_data.username,
                domain_id=auth_data.domain_id
            )
            await self.session.execute(stmt)
            await self.session.commit()
        except SQLAlchemyError as e:
            logger.error(f"Database error: {e}")
            raise HTTPException(status_code=500, detail="Internal Server Error")

    @staticmethod
    def create_auth_url(redirect_uri):
        '''
            Function that creates steam oauth url. User will authenticate via this link, 
            and steam will redirect to our site, so there will be parsed his acc data
        '''
        auth_url = (
            f"https://steamcommunity.com/openid/login"
            f"?openid.ns=http://specs.openid.net/auth/2.0"
            f"&openid.mode=checkid_setup"
            f"&openid.return_to={redirect_uri}"
            f"&openid.realm={redirect_uri}"
            f"&openid.ns.sreg=http://openid.net/extensions/sreg/1.1"
            f"&openid.claimed_id=http://specs.openid.net/auth/2.0/identifier_select"
            f"&openid.identity=http://specs.openid.net/auth/2.0/identifier_select"
        )
        return {"auth_url": auth_url}
    
    @staticmethod
    @retry(wait=wait_fixed(2), stop=stop_after_attempt(5), retry=retry_if_exception_type(httpx.RequestError))
    async def get_steam_user_data(steam_id: str, steam_api_key: str):
        '''
            Function that parse account data by steamid64 and requires apikey
        '''
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
                    f"?key={steam_api_key}&steamids={steam_id}"
                )
                response.raise_for_status()
                user_data = response.json()
                if not user_data["response"]["players"]:
                    raise HTTPException(status_code=404, detail="User not found")
                return user_data["response"]["players"][0]
            except httpx.RequestError as exc:
                raise HTTPException(status_code=502, detail="Failed to fetch data from Steam API") from exc
