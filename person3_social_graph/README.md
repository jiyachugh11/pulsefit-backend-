# Person 3 — Social Graph (Neo4j)

## What this demonstrates
- User nodes and directed `FOLLOWS` relationships.
- Following list, friends-of-friends, mutual follow targets and recommendations.

## Setup
1. Start a local Neo4j database (Neo4j Desktop or another class-approved instance).
2. In Neo4j Browser, run `social_graph.cypher` in order; it creates the graph and shows query results.
3. Or install `python -m pip install -r requirements.txt`, set `NEO4J_PASSWORD`, and run `python social_demo.py`.

PowerShell example:

```powershell
$env:NEO4J_PASSWORD="YOUR_NEO4J_PASSWORD"
python social_demo.py
```

The `social_graph.cypher` file is enough for a direct screenshot-based Neo4j Browser demonstration; the Python driver is optional.

## Screenshot ideas
Show the graph visualization after running the setup, then show the results of the following-list and recommendation queries.
