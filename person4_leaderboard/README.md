# Person 4 — Leaderboard (Redis)

## What this demonstrates
- Store user scores in a Redis sorted set.
- Retrieve the top 3 users using descending score order.
- Retrieve one user's rank and score.
- Update a score and show the changed ranking.

## Setup
1. Start Redis locally or use a class-approved Redis instance. On Windows, Redis may require a compatible local setup, WSL, Docker, or a hosted/class instance.
2. Install the Python dependency: `python -m pip install -r requirements.txt`.
3. Run: `python leaderboard_demo.py`.
4. If Redis is not at `localhost:6379`, set `REDIS_URL` to your connection URL.

## Screenshot ideas
Show the Python code and successful terminal output with top users and rank. If using `redis-cli`, you can also show `ZRANGE pulsefit:leaderboard:steps:2026-10-11 0 -1 WITHSCORES` (ascending) or `ZREVRANGE pulsefit:leaderboard:steps:2026-10-11 0 -1 WITHSCORES` (descending).
