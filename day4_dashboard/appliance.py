"""appliance.py — Monday's appliance list: the same four methods (GET, POST, PUT, DELETE), now stored in the database.
app.py plugs this group of endpoints in with  app.include_router(appliance.router)."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

import ee
import queries

router = APIRouter()


class Appliance(BaseModel):
    name: str = Field(min_length=1, max_length=40, description="e.g. 'Room AC'")
    watts: float = Field(gt=0, le=50000, description="power on the label, in watts")
    hours: float = Field(gt=0, le=24, description="hours of use in a day")


def _found(item, appliance_id):
    if item is None:
        raise HTTPException(status_code=404, detail=f"no appliance {appliance_id}")
    return item


@router.get("/appliances")
def list_appliances():
    return queries.list_appliances()


@router.get("/appliances/{appliance_id}")
def get_appliance(appliance_id: int):
    return _found(queries.get_appliance(appliance_id), appliance_id)


@router.post("/appliances", status_code=201)
def add_appliance(item: Appliance):
    return queries.add_appliance(**item.model_dump())


@router.put("/appliances/{appliance_id}")
def update_appliance(appliance_id: int, item: Appliance):
    return _found(queries.update_appliance(appliance_id, **item.model_dump()), appliance_id)


@router.delete("/appliances/{appliance_id}")
def delete_appliance(appliance_id: int):
    if not queries.delete_appliance(appliance_id):
        raise HTTPException(status_code=404, detail=f"no appliance {appliance_id}")
    return {"deleted": appliance_id}


@router.get("/appliances/{appliance_id}/cost")
def appliance_cost(appliance_id: int, rate: float = Query(8.0, gt=0, le=50)):
    """Monday's list joined with Monday's homework function: the daily cost of a saved appliance."""
    a = get_appliance(appliance_id)
    return {"appliance": a["name"], **ee.energy_cost(a["watts"], a["hours"], rate)}
