from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session
from inventory.schemas import InventoryCreateDTO, InventoryResponseDTO
from inventory.service import InventoryService

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
)


@router.post("/{steam_id}")
async def create_inventory(steam_id: str, session: AsyncSession = Depends(get_async_session)):
    try:
        steam_inventory = await InventoryService(session).fetch_inventory_from_steam(steam_id)
        inventory_data = InventoryCreateDTO(steam_id=steam_id, skins=steam_inventory)
        return await InventoryService(session).save_inventory(inventory_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{steam_id}")
async def get_inventory(steam_id: str, session: AsyncSession = Depends(get_async_session)):
    try:
        return await InventoryService(session).get_inventory(steam_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/refetch/{steam_id}")
async def refetch_inventory(steam_id: str, session: AsyncSession = Depends(get_async_session)):
    try:
        inventory_service = InventoryService(session)
        steam_inventory = await inventory_service.fetch_inventory_from_steam(steam_id)
        inventory_data = InventoryCreateDTO(steam_id=steam_id, skins=steam_inventory)
        existing_inventory = await inventory_service.get_inventory(steam_id)
        return await inventory_service.save_inventory(inventory_data, existing_inventory)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
