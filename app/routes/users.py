from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator
from app.db.postgres import cursor, EXISTING_LAYOUT

router = APIRouter(prefix='/users', tags=['users'])
COLUMNS = 'user_id, first_name, last_name, full_name, email, created_at AS joined_at'
if EXISTING_LAYOUT:
    COLUMNS = "user_id, first_name, last_name, concat_ws(' ', first_name, last_name) AS full_name, email, COALESCE(joined_at::timestamp, created_at) AS joined_at"


class UserData(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(default='', max_length=100)
    email: str = Field(max_length=255, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')

    @model_validator(mode='after')
    def check_name(self):
        if not self.first_name.strip() or len((self.first_name + ' ' + self.last_name).strip()) > 100:
            raise ValueError('Full name must contain 1–100 characters.')
        return self


class UserCreate(UserData):
    user_id: str = Field(min_length=1, max_length=20, pattern=r'^[A-Za-z0-9_-]+$')


@router.get('')
def list_users():
    with cursor() as cur:
        cur.execute(f'SELECT {COLUMNS} FROM users ORDER BY user_id')
        return cur.fetchall()


@router.get('/{user_id}')
def get_user(user_id: str):
    with cursor() as cur:
        cur.execute(f'SELECT {COLUMNS} FROM users WHERE user_id = %s', (user_id,))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(404, 'User not found.')
        return row


@router.post('', status_code=201)
def create_user(data: UserCreate):
    with cursor() as cur:
        if EXISTING_LAYOUT:
            cur.execute(f'''INSERT INTO users (user_id, first_name, last_name, email, joined_at)
                VALUES (%s, %s, %s, %s, CURRENT_DATE) RETURNING {COLUMNS}''',
                (data.user_id, data.first_name, data.last_name, data.email))
            return cur.fetchone()
        cur.execute(f'''INSERT INTO users (user_id, first_name, last_name, email, full_name)
            VALUES (%s, %s, %s, %s, %s) RETURNING {COLUMNS}''',
            (data.user_id, data.first_name, data.last_name, data.email, (data.first_name + ' ' + data.last_name).strip()))
        return cur.fetchone()


@router.put('/{user_id}')
def update_user(user_id: str, data: UserData):
    with cursor() as cur:
        if EXISTING_LAYOUT:
            cur.execute(f'''UPDATE users SET first_name = %s, last_name = %s, email = %s
                WHERE user_id = %s RETURNING {COLUMNS}''',
                (data.first_name, data.last_name, data.email, user_id))
        else:
            cur.execute(f'''UPDATE users SET first_name = %s, last_name = %s, email = %s, full_name = %s
                WHERE user_id = %s RETURNING {COLUMNS}''',
                (data.first_name, data.last_name, data.email, (data.first_name + ' ' + data.last_name).strip(), user_id))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(404, 'User not found.')
        return row


@router.delete('/{user_id}')
def delete_user(user_id: str):
    with cursor() as cur:
        # Some existing schemas use ON DELETE CASCADE. Keep the app's explicit
        # remove-devices-first behavior without changing the database constraint.
        cur.execute('SELECT user_id FROM users WHERE user_id = %s FOR UPDATE', (user_id,))
        if cur.fetchone() is None:
            raise HTTPException(404, 'User not found.')
        cur.execute('SELECT device_id FROM devices WHERE user_id = %s LIMIT 1', (user_id,))
        if cur.fetchone() is not None:
            raise HTTPException(409, 'Remove this user\'s devices before deleting the user.')
        cur.execute('DELETE FROM users WHERE user_id = %s RETURNING user_id', (user_id,))
        if cur.fetchone() is None:
            raise HTTPException(404, 'User not found.')
        return {'message': 'User deleted.'}

