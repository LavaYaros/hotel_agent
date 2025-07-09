from pydantic import BaseModel, Field
from typing import List

class Room(BaseModel):
    id: int
    room_type: str
    room_area_sq_m: float
    beds: int
    free_wifi: bool
    kitchen: bool
    mini_bar: bool
    access_to_pool: bool
    price_per_day: float
    short_description: str

class HotelResponse(BaseModel):
    reply: str = Field(..., description="Concise answer for the guest")
    recommendations: List[Room]
    tools_used: List[str]