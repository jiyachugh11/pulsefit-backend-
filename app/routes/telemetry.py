from datetime import date, datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, AwareDatetime, model_validator
from app.db.cassandra_db import session
from app.routes.devices import get_device

router = APIRouter(prefix='/telemetry', tags=['telemetry'])


class Reading(BaseModel):
    device_id: str = Field(min_length=1, max_length=20)
    reading_date: date
    reading_ts: AwareDatetime
    heart_rate: int = Field(ge=0, le=300)
    steps: int = Field(ge=0, le=2147483647)
    spo2: int = Field(ge=0, le=100)
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)

    @model_validator(mode='after')
    def check_timestamp(self):
        self.reading_ts = self.reading_ts.astimezone(timezone.utc)
        if self.reading_ts.date() != self.reading_date:
            raise ValueError('reading_date must equal the UTC date of reading_ts.')
        if self.reading_ts.microsecond % 1000:
            raise ValueError('Cassandra timestamps support millisecond precision.')
        return self


@router.get('/{device_id}')
def get_readings(device_id: str, reading_date: date, limit: int = Query(200, ge=1, le=1000)):
    with session() as connection:
        rows = connection.execute('''SELECT * FROM sensor_readings_by_device_day
            WHERE device_id = %s AND reading_date = %s LIMIT %s''',
            (device_id, reading_date, limit))
        result = []
        for row in rows:
            item = dict(row._asdict())
            item['reading_date'] = str(item['reading_date'])
            item['reading_ts'] = item['reading_ts'].replace(tzinfo=timezone.utc).isoformat()
            result.append(item)
        return result


@router.post('', status_code=201)
def add_reading(data: Reading):
    get_device(data.device_id)
    with session() as connection:
        insert = connection.prepare('''INSERT INTO sensor_readings_by_device_day
            (device_id, reading_date, reading_ts, heart_rate, steps, spo2, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''')
        connection.execute(insert, (data.device_id, data.reading_date, data.reading_ts,
                                   data.heart_rate, data.steps, data.spo2, data.latitude, data.longitude))
    return data.model_dump()


@router.delete('/{device_id}/{reading_date}/{reading_ts}')
def delete_reading(device_id: str, reading_date: date, reading_ts: AwareDatetime):
    ts = reading_ts.astimezone(timezone.utc)
    if ts.date() != reading_date or ts.microsecond % 1000:
        raise HTTPException(422, 'Use the UTC date and exact millisecond timestamp returned by GET.')
    with session() as connection:
        result = connection.execute('''DELETE FROM sensor_readings_by_device_day
            WHERE device_id = %s AND reading_date = %s AND reading_ts = %s IF EXISTS''',
            (device_id, reading_date, ts))
        if not result.one().applied:
            raise HTTPException(404, 'Reading not found.')
    return {'message': 'Reading deleted.'}
