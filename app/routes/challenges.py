from datetime import date
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator
from app.db.postgres import cursor

router = APIRouter(prefix='/challenges', tags=['challenges'])
COLUMNS = 'challenge_id, challenge_name, start_date, end_date'


class ChallengeData(BaseModel):
    challenge_name: str = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date

    @model_validator(mode='after')
    def check_dates(self):
        if self.end_date < self.start_date:
            raise ValueError('End date must be on or after start date.')
        return self


class ChallengeCreate(ChallengeData):
    challenge_id: str = Field(min_length=1, max_length=20, pattern=r'^[A-Za-z0-9_-]+$')


@router.get('')
def list_challenges():
    with cursor() as cur:
        cur.execute(f'SELECT {COLUMNS} FROM challenges ORDER BY challenge_id')
        return cur.fetchall()


@router.get('/{challenge_id}')
def get_challenge(challenge_id: str):
    with cursor() as cur:
        cur.execute(f'SELECT {COLUMNS} FROM challenges WHERE challenge_id = %s', (challenge_id,))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(404, 'Challenge not found.')
        return row


@router.post('', status_code=201)
def create_challenge(data: ChallengeCreate):
    with cursor() as cur:
        cur.execute(f'''INSERT INTO challenges (challenge_id, challenge_name, start_date, end_date)
            VALUES (%s, %s, %s, %s) RETURNING {COLUMNS}''',
            (data.challenge_id, data.challenge_name, data.start_date, data.end_date))
        return cur.fetchone()


@router.put('/{challenge_id}')
def update_challenge(challenge_id: str, data: ChallengeData):
    with cursor() as cur:
        cur.execute(f'''UPDATE challenges SET challenge_name = %s, start_date = %s, end_date = %s
            WHERE challenge_id = %s RETURNING {COLUMNS}''',
            (data.challenge_name, data.start_date, data.end_date, challenge_id))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(404, 'Challenge not found.')
        return row


@router.delete('/{challenge_id}')
def delete_challenge(challenge_id: str):
    with cursor() as cur:
        cur.execute('DELETE FROM challenges WHERE challenge_id = %s RETURNING challenge_id', (challenge_id,))
        if cur.fetchone() is None:
            raise HTTPException(404, 'Challenge not found.')
        return {'message': 'Challenge deleted.'}

