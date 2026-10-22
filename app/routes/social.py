from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator
from app.db.neo4j_db import session
from app.routes.users import get_user

router = APIRouter(prefix='/social', tags=['social'])


class Follow(BaseModel):
    user_id: str = Field(min_length=1, max_length=20)
    target_id: str = Field(min_length=1, max_length=20)

    @model_validator(mode='after')
    def no_self_follow(self):
        if self.user_id == self.target_id:
            raise ValueError('A user cannot follow themselves.')
        return self


@router.post('/follow')
def follow(data: Follow):
    user, target = get_user(data.user_id), get_user(data.target_id)
    with session() as graph:
        graph.run('''MERGE (a:User {user_id: $user_id}) SET a.name = $name
            MERGE (b:User {user_id: $target_id}) SET b.name = $target_name
            MERGE (a)-[:FOLLOWS]->(b)''', user_id=data.user_id, target_id=data.target_id,
            name=user['full_name'], target_name=target['full_name']).consume()
    return {'message': 'Follow relationship saved.'}


@router.delete('/follow')
def unfollow(data: Follow):
    with session() as graph:
        record = graph.run('''MATCH (:User {user_id: $user_id})-[r:FOLLOWS]->(:User {user_id: $target_id})
            DELETE r RETURN count(r) AS removed''', **data.model_dump()).single()
        if not record or record['removed'] == 0:
            raise HTTPException(404, 'Follow relationship not found.')
    return {'message': 'Follow relationship removed.'}


@router.get('/{user_id}/following')
def following(user_id: str):
    get_user(user_id)
    with session() as graph:
        return graph.run('''MATCH (:User {user_id: $user_id})-[:FOLLOWS]->(person:User)
            RETURN person.user_id AS user_id, person.name AS name ORDER BY name''',
            user_id=user_id).data()


@router.get('/{user_id}/recommendations')
def recommendations(user_id: str):
    get_user(user_id)
    with session() as graph:
        return graph.run('''MATCH (me:User {user_id: $user_id})-[:FOLLOWS]->(shared:User)-[:FOLLOWS]->(candidate:User)
            WHERE candidate <> me AND NOT EXISTS { MATCH (me)-[:FOLLOWS]->(candidate) }
            RETURN candidate.user_id AS user_id, candidate.name AS name,
                   count(DISTINCT shared) AS shared_connections
            ORDER BY shared_connections DESC, user_id''', user_id=user_id).data()
