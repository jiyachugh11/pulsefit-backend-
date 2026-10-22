# Inspection and reuse audit

All **18 files** in the supplied extracted archive `PulseFit_All_Members_Code (1)/PulseFit_All_Members/` were read before implementation. The initial progress message's count of 20 was a counting error; the inventory below is exhaustive. Original files were left unchanged.

| Original file | Database | Reused/adapted |
|---|---|---|
| README.md | All five | Shared user/device IDs; module responsibilities; truthful execution evidence. |
| requirements-all.txt | All five | Retained the five driver families and version bounds. Added only web dependencies and portable asyncore support. |
| person1_telemetry/README.md | Cassandra | Require both device_id and reading_date for reads. |
| person1_telemetry/requirements.txt | Cassandra | cassandra-driver dependency. |
| person1_telemetry/schema.cql | Cassandra | Same keyspace, table, columns, partition/clustering keys, and ASC order. |
| person1_telemetry/telemetry_demo.py | Cassandra | Cluster([HOST]), pulsefit session, prepared INSERT, partition SELECT, same three measurements. Fixed sample date replaces moving now for repeatability. |
| person2_users_devices/README.md | PostgreSQL + MongoDB | SQL owns registration; MongoDB stores flexible per-model fields; application joins by device ID. |
| person2_users_devices/requirements.txt | PostgreSQL + MongoDB | psycopg2-binary and pymongo. |
| person2_users_devices/sample_documents.json | MongoDB | Copied byte-for-byte to setup/sample_documents.json. |
| person2_users_devices/schema.sql | PostgreSQL | Original users/devices tables, lengths, unique email, FK, timestamp defaults retained. Additive columns and challenges added. |
| person2_users_devices/users_devices_demo.py | PostgreSQL + MongoDB | psycopg2 connection, parameterized SQL and conflict-safe seed INSERT; legacy PG* environment fallback; MongoClient timeout; pulsefit.device_metadata and $set update/upsert. |
| person3_social_graph/README.md | Neo4j | Four users, directed follows, graph presentation and recommendation walkthrough. |
| person3_social_graph/requirements.txt | Neo4j | neo4j driver. |
| person3_social_graph/social_demo.py | Neo4j | GraphDatabase.driver, session.run, MERGE by user_id, following and two-hop query. |
| person3_social_graph/social_graph.cypher | Neo4j | Same four edges and exclusion rules. Counts distinct intermediates as shared_connections; adds unique user ID constraint. |
| person4_leaderboard/README.md | Redis | Sorted sets, descending ranks, explicit daily totals, CLI inspection. |
| person4_leaderboard/requirements.txt | Redis | redis driver. |
| person4_leaderboard/leaderboard_demo.py | Redis | Redis.from_url(decode_responses=True), original date/key and initial scores, ZADD, ZREVRANGE, ZREVRANK, ZSCORE and 1-based ranks. U103's 26000 demonstration update is performed interactively instead of during seeding. |

## Necessary changes

- Original `full_name` and `created_at` remain. New first/last columns support unambiguous edits, with a one-time best-effort split for preexisting full names. API writes keep full_name aligned. API joined_at aliases created_at.
- Original device_name remains the stored model. New device_type and brand are additive. The supplied watch metadata had no SQL watch registration; PW501 is now registered to U102 so both sample documents pass the integration's foreign-reference check. This ownership was added, not claimed to be in the original script.
- Add challenges because the original package has no challenge implementation.
- Extend existing queries with missing CRUD, parameterized path inputs, validation and HTTP errors. Per-request context managers guarantee cleanup and transactions without a service/repository layer.
- Social POST verifies SQL users and MERGEs their nodes, so newly registered users can participate without a separate node API. Recommendations retain original logic with distinct shared-user counting.
- Redis groups the update/rank or rank/score operations in a small native pipeline to keep each result coherent.
- Preserve arbitrary metadata fields and $set semantics. Add a unique device_id index to make POST duplicate behavior reliable.
- Retain Cassandra's native upsert behavior and require the complete primary key for deletes. UTC validation avoids wrong-day partitions and lost timestamp precision.
- Samples are setup data, never an in-memory replacement for a failed database. No automatic migration or reseeding runs when the app starts.

The five original scripts were independent demonstrations. This project shares the identifiers and validates references on writes, but deliberately avoids distributed transactions or automatic cross-store cascades. See the README for the resulting lifecycle limits.
