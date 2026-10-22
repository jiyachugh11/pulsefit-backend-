"""Read-only local connectivity check; does not print passwords or change data."""
import os
import socket
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
for name, port in [('PostgreSQL', 5432), ('MongoDB', 27017), ('Cassandra', 9042), ('Neo4j', 7687), ('Redis', 6379)]:
    with socket.socket() as connection:
        connection.settimeout(2)
        reachable = connection.connect_ex(('127.0.0.1', port)) == 0
        print(f'{name} default port {port}: {"reachable" if reachable else "not reachable"}', flush=True)

try:
    from pymongo import MongoClient
    with MongoClient(os.environ['MONGO_URI'], serverSelectionTimeoutMS=3000) as client:
        client.admin.command('ping')
        print('MongoDB ping: OK')
        print('MongoDB pulsefit collections:', client['pulsefit'].list_collection_names())
except Exception as error:
    print('MongoDB check:', type(error).__name__)

try:
    from neo4j import GraphDatabase
    with GraphDatabase.driver(os.environ['NEO4J_URI'],
                              auth=(os.environ['NEO4J_USER'], os.environ['NEO4J_PASSWORD']),
                              connection_timeout=3, connection_acquisition_timeout=3) as driver:
        driver.verify_connectivity()
        print('Neo4j authentication: OK')
except Exception as error:
    print('Neo4j check:', type(error).__name__)

try:
    from cassandra.cluster import Cluster
    from cassandra.io.asyncorereactor import AsyncoreConnection
    cluster = Cluster([os.getenv('CASSANDRA_HOST', '127.0.0.1')],
                      connection_class=AsyncoreConnection, connect_timeout=3)
    try:
        session = cluster.connect()
        rows = session.execute("SELECT table_name FROM system_schema.tables WHERE keyspace_name = %s",
                               ('pulsefit',), timeout=5)
        print('Cassandra pulsefit tables:', [row.table_name for row in rows])
    finally:
        cluster.shutdown()
except Exception as error:
    print('Cassandra check:', type(error).__name__)
