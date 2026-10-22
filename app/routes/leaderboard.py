from datetime import date
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.db.redis_db import client
from app.routes.users import get_user

router = APIRouter(prefix='/leaderboard', tags=['leaderboard'])
SAMPLE_DAY = date(2026, 10, 11)


class Score(BaseModel):
    steps: int = Field(ge=0, le=2147483647)


def key(day: date):
    return f'pulsefit:leaderboard:steps:{day.isoformat()}'


@router.get('')
def leaderboard(day: date = SAMPLE_DAY):
    with client() as connection:
        rows = connection.zrevrange(key(day), 0, -1, withscores=True)
        return [{'rank': rank, 'user_id': user_id, 'steps': int(score)}
                for rank, (user_id, score) in enumerate(rows, start=1)]


@router.get('/{user_id}')
def user_rank(user_id: str, day: date = SAMPLE_DAY):
    with client() as connection:
        with connection.pipeline() as pipe:
            pipe.zrevrank(key(day), user_id)
            pipe.zscore(key(day), user_id)
            rank, score = pipe.execute()
        if rank is None:
            raise HTTPException(404, 'User has no score for this day.')
        return {'rank': rank + 1, 'user_id': user_id, 'steps': int(score)}


@router.put('/{user_id}')
def update_score(user_id: str, data: Score, day: date = SAMPLE_DAY):
    get_user(user_id)
    with client() as connection:
        with connection.pipeline() as pipe:
            pipe.zadd(key(day), {user_id: data.steps})
            pipe.zrevrank(key(day), user_id)
            _, rank = pipe.execute()
        return {'rank': rank + 1, 'user_id': user_id, 'steps': data.steps}
