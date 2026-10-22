"""Redis sorted-set leaderboard: scores are total daily steps in this toy example."""
import os
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
KEY = "pulsefit:leaderboard:steps:2026-10-11"


def main():
    client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    client.ping()  # fail early if Redis is not running

    # ZADD creates/updates each member's score. These are illustrative sample totals.
    client.zadd(KEY, {"U101": 25200, "U102": 24700, "U103": 23100, "U104": 18900})

    print("Top 3 users by daily steps:")
    for rank, (user_id, score) in enumerate(client.zrevrange(KEY, 0, 2, withscores=True), start=1):
        print(f"{rank}. {user_id}: {int(score)} steps")

    user_id = "U102"
    rank_zero_based = client.zrevrank(KEY, user_id)
    score = client.zscore(KEY, user_id)
    if rank_zero_based is None:
        print(f"{user_id} is not on the leaderboard.")
    else:
        print(f"\n{user_id} rank: {rank_zero_based + 1}; score: {int(score)} steps")

    # Example score update for a new total.
    client.zadd(KEY, {"U103": 26000})
    print("\nTop 3 after updating U103:")
    for rank, (member, score) in enumerate(client.zrevrange(KEY, 0, 2, withscores=True), start=1):
        print(f"{rank}. {member}: {int(score)} steps")


if __name__ == "__main__":
    main()
