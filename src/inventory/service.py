import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from inventory.models import Inventory
from inventory.schemas import InventoryCreateDTO
from typing import Optional

class InventoryService:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def fetch_inventory_from_steam(self, steam_id: str) -> dict:
        steam_api_url = f"https://steamcommunity.com/inventory/{steam_id}/730/2?l=english&count=5000"
        async with httpx.AsyncClient() as client:
            response = await client.get(steam_api_url)
            if response.status_code != 200:
                raise Exception("Failed to fetch inventory from Steam")
            return response.json()

    async def save_inventory(self, inventory_data: InventoryCreateDTO, existing_inventory: Optional[Inventory] = None) -> Inventory:
        if existing_inventory:
            for key, value in inventory_data.model_dump().items():
                setattr(existing_inventory, key, value)
            await self.session.commit()
            await self.session.refresh(existing_inventory)
            return existing_inventory
        new_inventory = Inventory(**inventory_data.model_dump())
        self.session.add(new_inventory)
        await self.session.commit()
        await self.session.refresh(new_inventory)
        return new_inventory

    async def get_inventory(self, steam_id: str) -> Inventory:
        result = await self.session.execute(select(Inventory).filter(Inventory.steam_id == steam_id))
        inventory = result.scalars().first()
        if inventory is None:
            raise Exception("Inventory not found")
        return inventory
