import logging
import httpx

from sqlalchemy import insert, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, wait_fixed, stop_after_attempt, retry_if_exception_type
from fastapi import HTTPException

from inventory.service import InventoryService
from inventory.schemas import InventoryCreateDTO

from auth.models import AuthData
from auth.schemas import AuthDataCreateDTO, AuthDataResponseDTO

from config import settings

logger = logging.getLogger(__name__)

class SteamAuthService:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def send_auth_data_to_main_panel(self, auth_data: AuthDataCreateDTO):
        url = settings.MAIN_PANEL_CREATE_AUTH_LINK

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        data = auth_data.model_dump()

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
            except httpx.RequestError as exc:
                logger.error(f"HTTPX request error: {exc}")
                raise HTTPException(status_code=502, detail="Failed to communicate with Main panel") from exc
            except httpx.HTTPStatusError as exc:
                logger.error(f"HTTPX HTTP status error: {exc}")
                raise HTTPException(status_code=exc.response.status_code, detail="Main panel returned an error")

    async def save_auth_data(self, auth_data: AuthDataCreateDTO):
        try:
            # Check if user already exists
            existing_user_query = select(AuthData).where(AuthData.steam_id == auth_data.steam_id)
            existing_user_result = await self.session.execute(existing_user_query)
            existing_user = existing_user_result.scalars().first()

            # Save or update auth data
            if existing_user:
                # Update the existing user's data
                for key, value in auth_data.model_dump().items():
                    setattr(existing_user, key, value)
                await self.session.commit()
                await self.session.refresh(existing_user)
                user = existing_user
            else:
                # Insert new user data
                stmt = insert(AuthData).values(
                    user_ip=auth_data.user_ip,
                    steam_id=auth_data.steam_id,
                    username=auth_data.username,
                    domain_id=auth_data.domain_id
                )
                await self.session.execute(stmt)
                await self.session.commit()

                # Retrieve the newly created user
                user_query = select(AuthData).where(AuthData.steam_id == auth_data.steam_id)
                user_result = await self.session.execute(user_query)
                user = user_result.scalars().first()

            # Handle inventory creation or refetching
            steam_inventory = await InventoryService(self.session).fetch_inventory_from_steam(auth_data.steam_id)

            inventory_data = InventoryCreateDTO(steam_id=auth_data.steam_id, skins=steam_inventory)

            try:
                existing_inventory = await InventoryService(self.session).get_inventory(auth_data.steam_id)
                # Refetch inventory if it already exists
                await InventoryService(self.session).save_inventory(inventory_data, existing_inventory)
            except Exception as e:
                # Create new inventory if it doesn't exist
                await InventoryService(self.session).save_inventory(inventory_data)

            # Send HTTP request to localhost:10000
            await self.send_auth_data_to_main_panel(auth_data)

            return user

        except SQLAlchemyError as e:
            logger.error(f"Database error: {e}")
            raise HTTPException(status_code=500, detail="Internal Server Error")
        
    async def filter_auth_data(self, domain_id: int = None, username: str = None, steam_id: str = None, user_ip: str = None, limit: int = 10, offset: int = 0):
        try:
            query = select(AuthData)

            if domain_id:
                query = query.where(AuthData.domain_id == domain_id)
            if username:
                query = query.where(AuthData.username == username)
            if steam_id:
                query = query.where(AuthData.steam_id == steam_id)
            if user_ip:
                query = query.where(AuthData.user_ip == user_ip)
            
            query = query.limit(limit).offset(offset)

            result = await self.session.execute(query)

            result_orm = result.scalars().all()

           
            # Build the response DTOs
            result_dto = [
                AuthDataResponseDTO(
                    id=row.id,
                    user_ip=row.user_ip,
                    created_at=row.created_at,
                    steam_id=row.steam_id,
                    username=row.username,
                    domain_id=row.domain_id,
                )
                for row in result_orm
            ]

            return result_dto
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

