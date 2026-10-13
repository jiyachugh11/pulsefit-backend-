"""Neo4j example. The same operations are also provided in social_graph.cypher."""
import os
from neo4j import GraphDatabase

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "change_me")

SETUP = [
    "MERGE (u:User {user_id:'U101'}) SET u.name='Jiya'",
    "MERGE (u:User {user_id:'U102'}) SET u.name='Rahul'",
    "MERGE (u:User {user_id:'U103'}) SET u.name='Priya'",
    "MERGE (u:User {user_id:'U104'}) SET u.name='Aman'",
    "MATCH (a:User {user_id:'U101'}), (b:User {user_id:'U102'}) MERGE (a)-[:FOLLOWS]->(b)",
    "MATCH (a:User {user_id:'U101'}), (b:User {user_id:'U103'}) MERGE (a)-[:FOLLOWS]->(b)",
    "MATCH (a:User {user_id:'U102'}), (b:User {user_id:'U104'}) MERGE (a)-[:FOLLOWS]->(b)",
    "MATCH (a:User {user_id:'U103'}), (b:User {user_id:'U104'}) MERGE (a)-[:FOLLOWS]->(b)",
]


def main():
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    try:
        with driver.session() as session:
            for query in SETUP:
                session.run(query).consume()
            result = session.run("""
                MATCH (:User {user_id:'U101'})-[:FOLLOWS]->(person)
                RETURN person.user_id AS user_id, person.name AS name
                ORDER BY name
            """)
            print("Jiya follows:")
            for record in result:
                print(record["user_id"], record["name"])
            result = session.run("""
                MATCH (me:User {user_id:'U101'})-[:FOLLOWS]->()-[:FOLLOWS]->(candidate:User)
                WHERE candidate <> me
                  AND NOT EXISTS { MATCH (me)-[:FOLLOWS]->(candidate) }
                RETURN DISTINCT candidate.user_id AS user_id, candidate.name AS name
            """)
            print("Friends-of-friends recommendations:")
            for record in result:
                print(record["user_id"], record["name"])
    finally:
        driver.close()


if __name__ == "__main__":
    main()
