import os
import time
import requests
from typing import List, Dict, Any, Optional


class TwitterAPIError(Exception):
    pass


class TwitterAPIClient:
    """
    Simple wrapper around twitterapi.io
    """

    BASE_URL = "https://api.twitterapi.io/twitter"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TWITTER_API_KEY")

        if not self.api_key:
            raise ValueError("TWITTER_API_KEY is missing")

        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": self.api_key
        })

    # -----------------------------
    # Core request handler
    # -----------------------------
    def _get(self, endpoint: str, params: dict = None, retries: int = 3):
        url = f"{self.BASE_URL}/{endpoint}"

        for attempt in range(retries):
            try:
                resp = self.session.get(url, params=params, timeout=15)

                if resp.status_code == 200:
                    return resp.json()

                # rate limit / temporary errors
                if resp.status_code in (429, 500, 502, 503, 504):
                    wait = 2 ** attempt
                    print(f"[TwitterAPI] retry {attempt+1}/{retries} in {wait}s (status {resp.status_code})")
                    time.sleep(wait)
                    continue

                raise TwitterAPIError(f"HTTP {resp.status_code}: {resp.text}")

            except requests.RequestException as e:
                print(f"[TwitterAPI] network error: {e}")
                time.sleep(2 ** attempt)

        raise TwitterAPIError("Max retries exceeded")

    # -----------------------------
    # Fetch latest tweets
    # -----------------------------
    def get_latest_tweets(self, username: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Uses:
        /user/tweet_timeline
        """
        data = self._get(
            "user/tweet_timeline",
            params={
                "userName": username,
                "count": limit
            }
        )

        tweets = data.get("tweets", data if isinstance(data, list) else [])

        return [self._normalize_tweet(t) for t in tweets]

    # -----------------------------
    # Normalize tweet structure
    # -----------------------------
    def _normalize_tweet(self, tweet: Dict[str, Any]) -> Dict[str, Any]:
        """
        Makes all tweets consistent regardless of API response shape
        """

        media = []

        raw_media = tweet.get("media", {}) or {}

        # images
        for img in raw_media.get("images", []) or []:
            media.append({
                "type": "image",
                "url": img
            })

        # videos
        for vid in raw_media.get("videos", []) or []:
            media.append({
                "type": "video",
                "url": vid.get("url") if isinstance(vid, dict) else vid
            })

        return {
            "id": str(tweet.get("id")),
            "text": tweet.get("text", ""),
            "created_at": tweet.get("createdAt") or tweet.get("created_at"),
            "author": tweet.get("author", {}).get("userName") if isinstance(tweet.get("author"), dict) else None,
            "media": media,
            "raw": tweet
        }

    # -----------------------------
    # Convenience method (optional)
    # -----------------------------
    def get_user(self, username: str) -> Dict[str, Any]:
        return self._get(
            "user/info",
            params={"userName": username}
        )
