from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.db.postgres import cursor, EXISTING_LAYOUT

router = APIRouter(prefix='/devices', tags=['devices'])
MODEL_COLUMN = 'model' if EXISTING_LAYOUT else 'device_name'
COLUMNS = f'device_id, user_id, device_type, brand, {MODEL_COLUMN} AS model, registered_at'


class DeviceData(BaseModel):
    user_id: str = Field(min_length=1, max_length=20)
    device_type: str = Field(min_length=1, max_length=50)
    brand: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)


class DeviceCreate(DeviceData):
    device_id: str = Field(min_length=1, max_length=20, pattern=r'^[A-Za-z0-9_-]+$')


@router.get('')
def list_devices():
    with cursor() as cur:
        cur.execute(f'SELECT {COLUMNS} FROM devices ORDER BY device_id')
        return cur.fetchall()


@router.get('/{device_id}')
def get_device(device_id: str):
    with cursor() as cur:
        cur.execute(f'SELECT {COLUMNS} FROM devices WHERE device_id = %s', (device_id,))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(404, 'Device not found.')
        return row


@router.post('', status_code=201)
def create_device(data: DeviceCreate):
    with cursor() as cur:
        cur.execute(f'''INSERT INTO devices (device_id, user_id, device_type, brand, {MODEL_COLUMN})
            VALUES (%s, %s, %s, %s, %s) RETURNING {COLUMNS}''',
            (data.device_id, data.user_id, data.device_type, data.brand, data.model))
        return cur.fetchone()


@router.put('/{device_id}')
def update_device(device_id: str, data: DeviceData):
    with cursor() as cur:
        cur.execute(f'''UPDATE devices SET user_id = %s, device_type = %s, brand = %s, {MODEL_COLUMN} = %s
            WHERE device_id = %s RETURNING {COLUMNS}''',
            (data.user_id, data.device_type, data.brand, data.model, device_id))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(404, 'Device not found.')
        return row


@router.delete('/{device_id}')
def delete_device(device_id: str):
    with cursor() as cur:
        cur.execute('DELETE FROM devices WHERE device_id = %s RETURNING device_id', (device_id,))
        if cur.fetchone() is None:
            raise HTTPException(404, 'Device not found.')
        return {'message': 'Device deleted.'}

