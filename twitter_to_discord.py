import os
import time
import json
from typing import List, Set

from twitter_api import TwitterAPIClient
from discord_webhook import DiscordWebhookClient


SEEN_FILE = "seen_tweets.json"


class TwitterToDiscordBot:
    def __init__(self):
        self.username = os.getenv("TWITTER_USERNAME", "SoJ_JP")
        self.interval = int(os.getenv("CHECK_INTERVAL", "3600"))

        self.twitter = TwitterAPIClient()
        self.discord = DiscordWebhookClient()

        self.seen: Set[str] = self._load_seen()

    # -----------------------------
    # Load / Save seen tweets
    # -----------------------------
    def _load_seen(self) -> Set[str]:
        if not os.path.exists(SEEN_FILE):
            return set()

        try:
            with open(SEEN_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()

    def _save_seen(self):
        with open(SEEN_FILE, "w") as f:
            json.dump(list(self.seen), f)

    # -----------------------------
    # Fetch + filter tweets
    # -----------------------------
    def fetch_new_tweets(self) -> List[dict]:
        tweets = self.twitter.get_latest_tweets(self.username, limit=10)

        new_tweets = [
            t for t in tweets
            if t["id"] not in self.seen
        ]

        # chronological order (oldest → newest)
        new_tweets.reverse()

        return new_tweets

    # -----------------------------
    # Process tweets
    # -----------------------------
    def process(self):
        print(f"\n[Bot] Checking @{self.username}...")

        tweets = self.fetch_new_tweets()

        if not tweets:
            print("[Bot] No new tweets")
            return

        print(f"[Bot] {len(tweets)} new tweets found")

        for i, tweet in enumerate(tweets, 1):
            tweet_id = tweet["id"]

            print(f"[Bot] Posting {i}/{len(tweets)} tweet {tweet_id}")

            success = self.discord.send_tweet(tweet)

            if success:
                self.seen.add(tweet_id)
                self._save_seen()
                print("[Bot] Posted successfully")
            else:
                print("[Bot] Failed to post tweet")

    # -----------------------------
    # Startup safety
    # -----------------------------
    def bootstrap(self):
        """
        IMPORTANT:
        Prevents spam on first run.
        Marks latest tweets as seen.
        """
        if self.seen:
            return

        print("[Bot] First run detected — bootstrapping seen tweets")

        tweets = self.twitter.get_latest_tweets(self.username, limit=10)

        for t in tweets:
            self.seen.add(t["id"])

        self._save_seen()

        print(f"[Bot] Marked {len(tweets)} tweets as already seen")

    # -----------------------------
    # Main loop
    # -----------------------------
    def run(self):
        self.bootstrap()

        print("[Bot] Started successfully")

        while True:
            try:
                self.process()

            except Exception as e:
                print(f"[Bot] Error: {e}")

            print(f"[Bot] Sleeping {self.interval} seconds...\n")
            time.sleep(self.interval)


if __name__ == "__main__":
    bot = TwitterToDiscordBot()
    bot.run()
