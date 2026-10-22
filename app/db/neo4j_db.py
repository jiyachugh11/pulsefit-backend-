import os
from contextlib import contextmanager
from fastapi import HTTPException
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, DriverError


@contextmanager
def session():
    driver = None
    try:
        driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            auth=(os.getenv('NEO4J_USER', 'neo4j'), os.getenv('NEO4J_PASSWORD', '')),
            connection_timeout=5, connection_acquisition_timeout=5,
        )
        with driver.session() as connection:
            yield connection
    except (Neo4jError, DriverError) as exc:
        raise HTTPException(503, 'Neo4j unavailable. Check setup and .env.') from exc
    finally:
        if driver is not None:
            driver.close()
