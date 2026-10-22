import os
from contextlib import contextmanager
from fastapi import HTTPException
from pymongo import MongoClient
from pymongo.errors import PyMongoError, DuplicateKeyError


@contextmanager
def metadata_collection():
    client = None
    try:
        client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'),
                             serverSelectionTimeoutMS=5000, socketTimeoutMS=5000)
        yield client['pulsefit']['device_metadata']
    except DuplicateKeyError as exc:
        raise HTTPException(409, 'Metadata already exists for this device.') from exc
    except PyMongoError as exc:
        raise HTTPException(503, 'MongoDB unavailable. Check setup and .env.') from exc
    finally:
        if client is not None:
            client.close()
