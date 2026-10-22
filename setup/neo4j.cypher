CREATE CONSTRAINT pulsefit_user_id IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE;
MERGE (u:User {user_id:'U101'}) SET u.name='Jiya';
MERGE (u:User {user_id:'U102'}) SET u.name='Rahul';
MERGE (u:User {user_id:'U103'}) SET u.name='Priya';
MERGE (u:User {user_id:'U104'}) SET u.name='Aman';
MATCH (a:User {user_id:'U101'}), (b:User {user_id:'U102'}) MERGE (a)-[:FOLLOWS]->(b);
MATCH (a:User {user_id:'U101'}), (b:User {user_id:'U103'}) MERGE (a)-[:FOLLOWS]->(b);
MATCH (a:User {user_id:'U102'}), (b:User {user_id:'U104'}) MERGE (a)-[:FOLLOWS]->(b);
MATCH (a:User {user_id:'U103'}), (b:User {user_id:'U104'}) MERGE (a)-[:FOLLOWS]->(b);
