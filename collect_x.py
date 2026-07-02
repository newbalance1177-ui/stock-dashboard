"""X (Twitter) API v2 で指定ユーザーの新規ポストのみを差分取得し、DBへ保存する。

前提: config.X_TARGET_USERNAMES に収集対象のユーザー名(@なし)をカンマ区切りで設定。
X_BEARER_TOKEN が .env に設定されている必要がある。
"""
import sys
import time

import requests

import db
from config import X_BEARER_TOKEN, X_TARGET_USERNAMES

API_BASE = "https://api.twitter.com/2"


def _headers() -> dict:
    return {"Authorization": f"Bearer {X_BEARER_TOKEN}"}


def get_user_id(username: str) -> str | None:
    resp = requests.get(
        f"{API_BASE}/users/by/username/{username}", headers=_headers(), timeout=30
    )
    resp.raise_for_status()
    data = resp.json().get("data")
    return data["id"] if data else None


def fetch_new_tweets(user_id: str, since_id: str | None) -> list[dict]:
    params = {
        "max_results": 25,
        "tweet.fields": "created_at",
        "exclude": "retweets,replies",
    }
    if since_id:
        params["since_id"] = since_id

    resp = requests.get(
        f"{API_BASE}/users/{user_id}/tweets",
        headers=_headers(),
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def collect_for_user(username: str) -> int:
    user_id = get_user_id(username)
    if not user_id:
        print(f"[collect_x] user not found: {username}", file=sys.stderr)
        return 0

    since_id = db.get_since_id(username)
    tweets = fetch_new_tweets(user_id, since_id)
    if not tweets:
        return 0

    # API は新しい順に返す。最新IDを次回の since_id として保存する。
    newest_id = tweets[0]["id"]
    for tweet in tweets:
        url = f"https://x.com/{username}/status/{tweet['id']}"
        db.insert_post(
            post_id=tweet["id"],
            username=username,
            created_at=tweet["created_at"],
            text=tweet["text"],
            url=url,
        )
    db.set_since_id(username, newest_id)
    return len(tweets)


def main() -> None:
    if not X_BEARER_TOKEN:
        print("[collect_x] X_BEARER_TOKEN is not set in .env", file=sys.stderr)
        sys.exit(1)
    if not X_TARGET_USERNAMES:
        print("[collect_x] X_TARGET_USERNAMES is not set in .env", file=sys.stderr)
        sys.exit(1)

    db.init_db()
    total = 0
    for username in X_TARGET_USERNAMES:
        count = collect_for_user(username)
        print(f"[collect_x] {username}: {count} new post(s)")
        total += count
        time.sleep(1)  # レート制限対策

    print(f"[collect_x] done. total new posts: {total}")


if __name__ == "__main__":
    main()
