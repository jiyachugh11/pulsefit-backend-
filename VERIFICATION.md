# Verification

## Live verification completed October 22, 2026

All five real databases connected successfully. API reads returned four PostgreSQL users, four devices, three challenges, the existing PB101 MongoDB document, and existing Neo4j relationships/recommendations. Cassandra's existing PB101 partition is dated October 21, 2026. Redis was installed in Ubuntu WSL, its connection verified, and four missing sample scores initialized without overwriting scores.

`checks/live_crud.py` passed real create/read/update/delete operations across the five stores using unique temporary IDs; temporary records were cleaned up. MongoDB duplicate creation returned 409. The existing PostgreSQL FK uses ON DELETE CASCADE, so the router now explicitly rejects user deletion while devices exist. PostgreSQL counts after cleanup remained four users, four devices, and three rows in each existing challenge table. No original schema migration or wholesale reseeding was run. The October 21 limitations below are historical and are superseded by this live verification.

## Completed on October 21, 2026

- Inspected all 18 original files before building; originals remain unchanged.
- Installed requirements successfully in the project's local virtual environment on Python 3.14.3. Driver imports work, including Cassandra with its explicit AsyncoreConnection.
- Python compilation and JavaScript syntax checks passed.
- FastAPI generated its OpenAPI schema: 16 API paths and all 29 requested HTTP operations.
- Five optional smoke checks passed: dashboard/static files, complete API operation count, validation before database access, timezone/date and millisecond rules, and PostgreSQL error-to-HTTP mapping.
- Started Uvicorn successfully and loaded the real dashboard in the in-app browser. Reviewed the responsive layout at the sidebar width, tab switching, the metadata editor, and telemetry inputs. The PostgreSQL-offline error is clearly displayed rather than replaced by fake records.
- The test environment emitted an upstream Starlette warning that its httpx-based TestClient is deprecated; the five checks still passed. This is not an application runtime error.

## Not verified against running databases

Local ports 5432 (PostgreSQL), 27017 (MongoDB), 9042 (Cassandra), 7687 (Neo4j), and 6379 (Redis) were all unreachable during verification. No database server was installed or started, no credentials were inferred, and setup scripts were not run against a live store. Live SQL/CQL/Cypher execution and successful CRUD remain unverified. The mock error checks are not evidence of live database success.

## Live acceptance checklist

After following README setup steps, use the dashboard and `/docs`:

1. Confirm U101 is Jiya, PB101 is PulseBand X1 owned by U101, and PW501 is registered to U102. Confirm the four users and one challenge appear.
2. Create U199 with a unique email; read it via GET; edit its name/email. Create PB199 owned by U199; edit its model/type/brand. Deleting U199 while PB199 exists must return 409. Delete PB199 then U199. Duplicate IDs/emails must return 409; unknown IDs must return 404.
3. Create, view, edit and delete CH199. Verify an end date before the start date returns 422.
4. Load PB101 metadata. Confirm sensors and settings match the source. Add a custom field through Update and read it back. Use a disposable registered device to check POST duplicate handling and delete its metadata before deleting its registration.
5. Query PB101 on 2026-10-11; expect the three original sensor values in timestamp order. Add a new reading at 10:01 UTC, read it, and delete exactly that row. Confirm the three original readings remain. Missing date and naive/sub-millisecond timestamps must return 422.
6. Explore U101: following U102 and U103, recommendation U104 with shared_connections=2. Follow U104 and confirm it disappears from recommendations. Unfollow U104 and confirm it reappears. Self-follow must return 422. New registered users should be able to follow without a separate graph-node setup.
7. Load the 2026-10-11 leaderboard; expect U101 first with 25200. Update U103 to 26000, verify rank 1 in both GET endpoints, then restore 23100. Try a new date and confirm it has an independent key. Negative scores must return 422.
8. Stop one database intentionally and confirm the relevant section reports 503; the page should still render. Restart it and retry. Other stores' reads should continue except social reads, which intentionally verify the source user in PostgreSQL.

Use temporary IDs for deletion checks; do not delete the shared presentation samples. The original files and source listing explain the intended queries, but successful execution should only be claimed after this live checklist passes.
