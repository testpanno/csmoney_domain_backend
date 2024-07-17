from pydantic import BaseModel
from typing import Dict, Any

class InventoryBase(BaseModel):
    skins: Dict[str, Any]

class InventoryCreateDTO(InventoryBase):
    steam_id: str

class InventoryResponseDTO(InventoryBase):
    id: int
    steam_id: str
    last_updated: str

    class Config:
        from_attributes = True
