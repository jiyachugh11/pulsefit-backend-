// Run these statements in Neo4j Browser. Example shared IDs/names.
MERGE (jiya:User {user_id: 'U101', name: 'Jiya'})
MERGE (rahul:User {user_id: 'U102', name: 'Rahul'})
MERGE (priya:User {user_id: 'U103', name: 'Priya'})
MERGE (aman:User {user_id: 'U104', name: 'Aman'})
MERGE (jiya)-[:FOLLOWS]->(rahul)
MERGE (jiya)-[:FOLLOWS]->(priya)
MERGE (rahul)-[:FOLLOWS]->(aman)
MERGE (priya)-[:FOLLOWS]->(aman);

// 1. Who does Jiya follow?
MATCH (:User {user_id: 'U101'})-[:FOLLOWS]->(person)
RETURN person.user_id AS user_id, person.name AS name;

// 2. Friends-of-friends of Jiya, excluding Jiya and direct follows.
MATCH (me:User {user_id: 'U101'})-[:FOLLOWS]->()-[:FOLLOWS]->(candidate:User)
WHERE candidate <> me
  AND NOT EXISTS { MATCH (me)-[:FOLLOWS]->(candidate) }
RETURN DISTINCT candidate.user_id AS user_id, candidate.name AS name;

// 3. People followed by both Jiya and Rahul (mutual follow targets).
MATCH (:User {user_id: 'U101'})-[:FOLLOWS]->(p:User)<-[:FOLLOWS]-(:User {user_id: 'U102'})
RETURN p.user_id AS user_id, p.name AS name;

// 4. Recommendations for Jiya: friends-of-friends not already followed.
MATCH (me:User {user_id: 'U101'})-[:FOLLOWS]->()-[:FOLLOWS]->(candidate:User)
WHERE candidate <> me
  AND NOT EXISTS { MATCH (me)-[:FOLLOWS]->(candidate) }
RETURN candidate.user_id AS recommended_user_id, candidate.name AS recommended_name,
       count(*) AS shared_paths
ORDER BY shared_paths DESC;
