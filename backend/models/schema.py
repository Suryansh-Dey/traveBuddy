from pydantic import BaseModel
from typing import List, Optional

class UserQuery(BaseModel):
    user_id: str
    query: str

class Constraint(BaseModel):
    trip_id: str
    user_id: str
    budget: int
    deadline: int
    transport_modes: List[str]

class Component(BaseModel):
    type: str
    mode: str
    price: int


class ContractState(BaseModel):
    app_id: int
    app_address: str
    create_tx_id: str
    lock_tx_id: str
    lock_amount: int
    user_address: str
    receiver_address: str
    itinerary_hash: Optional[str] = None
    itinerary_commit_tx_id: Optional[str] = None
    release_tx_id: Optional[str] = None

class TripState(BaseModel):
    trip_id: str
    constraints: Constraint
    status: str  # PENDING, ACTIVE, EXECUTED
    contract: Optional[ContractState] = None