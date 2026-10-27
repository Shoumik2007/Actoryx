"""Day 1 · Step 5 — GET, POST, PUT, DELETE on the hostel's appliance list.
These endpoints live in their own file as an APIRouter — a group of endpoints. app.py plugs the group in with one line:
    app.include_router(appliance.router)
The list is kept in memory: it disappears when the server stops (Day 2 fixes that)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class Appliance(BaseModel):
    """What the JSON body of POST and PUT must contain — and its limits."""
    name: str = Field(min_length=1, max_length=40, description="e.g. 'Room AC'")
    watts: float = Field(gt=0, le=50000, description="power on the label, in watts")
    hours: float = Field(gt=0, le=24, description="hours of use in a day")


appliances: dict[int, dict] = {}
next_id = 1


@router.get("/appliances")                                    # GET    = read the whole list
def list_appliances():
    return [{"id": i, **a} for i, a in appliances.items()]


@router.get("/appliances/{appliance_id}")                     # GET    = read one item (by its id in the address)
def get_appliance(appliance_id: int):
    if appliance_id not in appliances:
        raise HTTPException(status_code=404, detail=f"no appliance {appliance_id}")
    return {"id": appliance_id, **appliances[appliance_id]}


@router.post("/appliances", status_code=201)                  # POST   = add a new item (data in the JSON body)
def add_appliance(item: Appliance):
    global next_id
    appliances[next_id] = item.model_dump()
    next_id += 1
    return {"id": next_id - 1, **item.model_dump()}


@router.put("/appliances/{appliance_id}")                     # PUT    = replace an existing item
def update_appliance(appliance_id: int, item: Appliance):
    if appliance_id not in appliances:
        raise HTTPException(status_code=404, detail=f"no appliance {appliance_id}")
    appliances[appliance_id] = item.model_dump()
    return {"id": appliance_id, **item.model_dump()}


@router.delete("/appliances/{appliance_id}")                  # DELETE = remove an item
def delete_appliance(appliance_id: int):
    if appliances.pop(appliance_id, None) is None:
        raise HTTPException(status_code=404, detail=f"no appliance {appliance_id}")
    return {"deleted": appliance_id}
