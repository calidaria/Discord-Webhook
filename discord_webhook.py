import os
import time
import requests
from typing import Dict, Any, List, Optional


class DiscordWebhookError(Exception):
    pass


class DiscordWebhookClient:
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")

        if not self.webhook_url:
            raise ValueError("DISCORD_WEBHOOK_URL is missing")

        self.session = requests.Session()

    # -----------------------------
    # Core send method
    # -----------------------------
    def send_tweet(self, tweet: Dict[str, Any]) -> bool:
        payload = self._build_payload(tweet)

        for attempt in range(3):
            resp = self.session.post(self.webhook_url, json=payload, timeout=15)

            # success
            if resp.status_code in (200, 204):
                return True

            # rate limit
            if resp.status_code == 429:
                retry_after = 2 ** attempt
                print(f"[Discord] rate limited, retrying in {retry_after}s")
                time.sleep(retry_after)
                continue

            # temporary server issues
            if resp.status_code in (500, 502, 503, 504):
                wait = 2 ** attempt
                print(f"[Discord] server error {resp.status_code}, retrying in {wait}s")
                time.sleep(wait)
                continue

            raise DiscordWebhookError(
                f"Discord error {resp.status_code}: {resp.text}"
            )

        return False

    # -----------------------------
    # Payload builder
    # -----------------------------
    def _build_payload(self, tweet: Dict[str, Any]) -> Dict[str, Any]:
        embeds = []

        text = tweet.get("text", "")
        tweet_id = tweet.get("id")
        author = tweet.get("author") or "unknown"

        # base tweet URL
        tweet_url = f"https://twitter.com/{author}/status/{tweet_id}"

        embed = {
            "title": f"New tweet from @{author}",
            "description": text[:4000],  # Discord limit safety
            "url": tweet_url,
            "color": 0x1DA1F2,
            "footer": {
                "text": "Twitter Bot via twitterapi.io"
            }
        }

        # attach first image as main embed image (Discord limitation)
        media = tweet.get("media", [])

        images = [m["url"] for m in media if m.get("type") == "image"]
        videos = [m["url"] for m in media if m.get("type") == "video"]

        if images:
            embed["image"] = {"url": images[0]}

        embeds.append(embed)

        # optional extra media embeds
        for img in images[1:3]:
            embeds.append({
                "url": tweet_url,
                "image": {"url": img}
            })

        # optional video links (Discord doesn't embed Twitter videos well)
        if videos:
            embeds.append({
                "description": "🎥 Video content:\n" + "\n".join(videos[:2]),
                "color": 0x14171A
            })

        return {
            "username": "Twitter Bot",
            "embeds": embeds
        }
