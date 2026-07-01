import os
import time

from twitter_api import TwitterAPIClient
from discord_webhook import DiscordWebhookClient


def main():
    username = os.getenv("TWITTER_USERNAME", "SoJ_JP")

    twitter = TwitterAPIClient()
    discord = DiscordWebhookClient()

    print(f"\n[Test] Fetching latest tweets from @{username}")

    tweets = twitter.get_latest_tweets(
        username=username,
        limit=10
    )

    if not tweets:
        print("[Test] No tweets found")
        return

    # oldest -> newest
    tweets.reverse()

    print(f"[Test] Found {len(tweets)} tweets")

    for index, tweet in enumerate(tweets, start=1):
        tweet_id = tweet["id"]

        print(
            f"[Test] Sending {index}/{len(tweets)} "
            f"Tweet ID {tweet_id}"
        )

        try:
            discord.send_tweet(tweet)
            print("[Test] Success")

        except Exception as e:
            print(f"[Test] Failed: {e}")

        # avoid webhook spam/rate limits
        time.sleep(1)

    print("\n[Test] Done")


if __name__ == "__main__":
    main()
