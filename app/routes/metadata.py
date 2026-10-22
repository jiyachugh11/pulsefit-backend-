from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.db.mongo import metadata_collection
from app.routes.devices import get_device

router = APIRouter(prefix='/metadata', tags=['metadata'])


class Metadata(BaseModel):
    # Keep model-specific fields such as PW501's ecg_enabled.
    model_config = ConfigDict(extra='allow')
    device_id: str = Field(min_length=1, max_length=20)
    model: str = Field(min_length=1, max_length=100)
    schema_version: int = Field(default=1, ge=1)
    sensors: list[str]
    settings: dict

    @model_validator(mode='after')
    def reject_internal_fields(self):
        def check(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == '_id' or key.startswith('$') or '.' in key:
                        raise ValueError('Metadata keys cannot contain dots, start with $, or use _id.')
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)
        check(self.model_dump())
        return self


@router.get('/{device_id}')
def get_metadata(device_id: str):
    with metadata_collection() as collection:
        doc = collection.find_one({'device_id': device_id}, {'_id': 0})
        if doc is None:
            raise HTTPException(404, 'Device metadata not found.')
        return doc


@router.post('', status_code=201)
def create_metadata(data: Metadata):
    get_device(data.device_id)
    doc = data.model_dump()
    with metadata_collection() as collection:
        collection.insert_one(dict(doc))
    return doc


@router.put('/{device_id}')
def update_metadata(device_id: str, data: Metadata):
    if data.device_id != device_id:
        raise HTTPException(422, 'Body device_id must match the URL.')
    get_device(device_id)
    with metadata_collection() as collection:
        # Retain the supplied $set pattern, including fields not sent in this update.
        result = collection.update_one({'device_id': device_id}, {'$set': data.model_dump()})
        if result.matched_count == 0:
            raise HTTPException(404, 'Device metadata not found; create it first.')
        return collection.find_one({'device_id': device_id}, {'_id': 0})


@router.delete('/{device_id}')
def delete_metadata(device_id: str):
    with metadata_collection() as collection:
        if collection.delete_one({'device_id': device_id}).deleted_count == 0:
            raise HTTPException(404, 'Device metadata not found.')
    return {'message': 'Metadata deleted.'}
