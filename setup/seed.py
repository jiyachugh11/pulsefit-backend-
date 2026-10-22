"""Run from project root: python setup/seed.py mongo|neo4j|redis.

Reads the same .env as the app. Database errors stop setup visibly.
"""
import argparse
import json
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')


def mongo():
    from pymongo import MongoClient
    with MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'),
                     serverSelectionTimeoutMS=5000) as client:
        collection = client['pulsefit']['device_metadata']
        collection.create_index('device_id', unique=True)
        for doc in json.loads((ROOT / 'setup' / 'sample_documents.json').read_text()):
            collection.update_one({'device_id': doc['device_id']}, {'$set': doc}, upsert=True)
    print('MongoDB metadata and unique device_id index ready.')


def neo4j():
    from neo4j import GraphDatabase
    with GraphDatabase.driver(os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
                              auth=(os.getenv('NEO4J_USER', 'neo4j'),
                                    os.getenv('NEO4J_PASSWORD', ''))) as driver:
        with driver.session() as session:
            for query in (ROOT / 'setup' / 'neo4j.cypher').read_text().split(';'):
                if query.strip():
                    session.run(query).consume()
    print('Neo4j users and original four follows ready.')


def redis():
    from redis import Redis
    with Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
                        decode_responses=True) as client:
        client.zadd('pulsefit:leaderboard:steps:2026-10-11',
                    {'U101': 25200, 'U102': 24700, 'U103': 23100, 'U104': 18900})
    print('Redis leaderboard for 2026-10-11 ready.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('database', choices=['mongo', 'neo4j', 'redis'])
    args = parser.parse_args()
    {'mongo': mongo, 'neo4j': neo4j, 'redis': redis}[args.database]()
