#!/usr/bin/env python3
"""
Twitter/X to Discord Webhook Bot - Version 8
Updated with currently-alive Nitter-style instances (2026) + fxtwitter for images/videos
"""

import requests
import time
import json
import os
import re
from datetime import datetime
import xml.etree.ElementTree as ET

USERNAME = "SoJ_JP"  # Change this to whichever account you want to monitor

class TwitterToDiscord:
    def __init__(self, discord_webhook_url: str, check_interval: int = 3600):
        self.webhook_url = discord_webhook_url
        self.check_interval = check_interval
        self.seen_tweets_file = "seen_tweets.json"
        self.seen_tweets = self.load_seen_tweets()
        self.first_run = len(self.seen_tweets) == 0

    def load_seen_tweets(self) -> set:
        if os.path.exists(self.seen_tweets_file):
            try:
                with open(self.seen_tweets_file, 'r') as f:
                    data = json.load(f)
                    print(f"📋 Loaded {len(data)} previously seen tweets")
                    return set(data)
            except:
                return set()
        return set()

    def save_seen_tweets(self):
        try:
            with open(self.seen_tweets_file, 'w') as f:
                json.dump(list(self.seen_tweets), f)
        except Exception as e:
            print(f"⚠️  Could not save seen tweets: {e}")

    def get_tweet_ids(self) -> list:
        """Try multiple methods to get recent tweet IDs, in order of reliability"""

        methods = [
            ("Twitter Syndication API", self.try_syndication_api),
            ("RSSHub",                  self.try_rsshub),
            ("Nitter-style instances",  self.try_nitter_instances),
        ]

        for name, method in methods:
            try:
                print(f"  🔄 Trying {name}...")
                ids = method()
                if ids:
                    print(f"  ✅ Got {len(ids)} tweet IDs via {name}!")
                    return ids
                else:
                    print(f"  ⚠️  {name} returned no results")
            except Exception as e:
                print(f"  ❌ {name} failed: {str(e)[:80]}")

        print("  ⚠️  All methods failed - will retry next check")
        return []

    def try_syndication_api(self) -> list:
        """Twitter's own syndication endpoint (no auth needed, when it works)"""
        url = f"https://cdn.syndication.twimg.com/timeline/profile?screen_name={USERNAME}&limit=10"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Origin': 'https://platform.twitter.com',
            'Referer': 'https://platform.twitter.com/',
        }
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            raise Exception(f"Status {response.status_code}")

        data = response.json()
        ids = []
        for item in data.get('timeline', [])[:10]:
            tweet_id = item.get('tweet_id') or item.get('id_str') or str(item.get('id', ''))
            tweet_id = re.sub(r'[^0-9]', '', str(tweet_id))
            if tweet_id and len(tweet_id) > 5:
                ids.append(tweet_id)
        return ids

    def try_rsshub(self) -> list:
        """RSSHub public instances"""
        instances = [
            f"https://rsshub.app/twitter/user/{USERNAME}",
            f"https://rsshub.rssforever.com/twitter/user/{USERNAME}",
            f"https://rsshub.feeded.app/twitter/user/{USERNAME}",
        ]
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/rss+xml, application/xml, text/xml',
        }
        for url in instances:
            try:
                print(f"    📡 {url.split('/')[2]}...")
                response = requests.get(url, headers=headers, timeout=20)
                if response.status_code == 200:
                    ids = self.parse_rss_ids(response.text)
                    if ids:
                        return ids
            except Exception as e:
                print(f"    ❌ {str(e)[:50]}")
        return []

    def try_nitter_instances(self) -> list:
        """
        Currently-alive Nitter-style instances (updated July 2026).
        This list will need occasional updates as instances come and go -
        check https://status.d420.de/ for the current live list.
        """
        instances = [
            f"https://xcancel.com/{USERNAME}/rss",
            f"https://nitter.privacyredirect.com/{USERNAME}/rss",
            f"https://lightbrd.com/{USERNAME}/rss",
            f"https://nitter.tiekoetter.com/{USERNAME}/rss",
            f"https://nuku.trabun.org/{USERNAME}/rss",
            f"https://nitter.catsarch.com/{USERNAME}/rss",
            f"https://nitter.kareem.one/{USERNAME}/rss",
            f"https://nt.vern.cc/{USERNAME}/rss",
            # Old instances kept as last resort in case they come back
            f"https://nitter.net/{USERNAME}/rss",
            f"https://nitter.poast.org/{USERNAME}/rss",
        ]
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        for url in instances:
            try:
                print(f"    📡 {url.split('/')[2]}...")
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    ids = self.parse_rss_ids(response.text)
                    if ids:
                        print(f"    ✅ Success from {url.split('/')[2]}!")
                        return ids
                else:
                    print(f"    ❌ Status {response.status_code}")
            except Exception as e:
                print(f"    ❌ {str(e)[:50]}")
        return []

    def parse_rss_ids(self, rss_content: str) -> list:
        """Parse RSS and extract tweet IDs"""
        ids = []
        try:
            root = ET.fromstring(rss_content)
            for item in root.findall('.//item')[:10]:
                link = item.find('link')
                if link is not None and link.text:
                    tweet_id = re.sub(r'[^0-9]', '', link.text.rstrip('/').split('/')[-1].split('#')[0])
                    if tweet_id and len(tweet_id) > 5:
                        ids.append(tweet_id)
        except Exception:
            pass
        return ids

    def get_tweet_details(self, tweet_id: str) -> dict:
        """Get full tweet details including images/videos from fxtwitter"""
        try:
            url = f"https://api.fxtwitter.com/{USERNAME}/status/{tweet_id}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                tweet = data.get('tweet', {})
                if not tweet:
                    return None

                images = []
                video_url = None
                media = tweet.get('media', {})

                for photo in media.get('photos', []):
                    if photo.get('url'):
                        images.append(photo['url'])

                videos = media.get('videos', [])
                if videos:
                    video_url = videos[0].get('url', '')
                    thumb = videos[0].get('thumbnail_url', '')
                    if thumb and not images:
                        images.append(thumb)

                gifs = media.get('gifs', [])
                if gifs and not video_url:
                    video_url = gifs[0].get('url', '')
                    thumb = gifs[0].get('thumbnail_url', '')
                    if thumb and not images:
                        images.append(thumb)

                created_at = tweet.get('created_at', '')
                timestamp = None
                if created_at:
                    try:
                        dt = datetime.strptime(created_at, '%a %b %d %H:%M:%S %z %Y')
                        timestamp = dt.isoformat()
                    except:
                        pass

                return {
                    'id': tweet_id,
                    'text': tweet.get('text', ''),
                    'link': f"https://twitter.com/{USERNAME}/status/{tweet_id}",
                    'images': images,
                    'video_url': video_url,
                    'timestamp': timestamp,
                    'user_name': tweet.get('author', {}).get('name', USERNAME),
                }
            else:
                print(f"  ❌ fxtwitter returned {response.status_code} for tweet {tweet_id}")
                return None

        except Exception as e:
            print(f"  ❌ Error fetching tweet {tweet_id}: {e}")
            return None

    def create_discord_embeds(self, tweet: dict) -> list:
        """Create Discord embeds with images/videos"""
        images = tweet.get('images', [])
        video_url = tweet.get('video_url')
        text = tweet.get('text', '')

        if video_url:
            text += f"\n\n🎬 **[Click to watch video]({tweet['link']})**"

        main_embed = {
            "title": f"New post from @{USERNAME}",
            "description": text[:4096],
            "url": tweet['link'],
            "color": 1942002,
            "author": {
                "name": f"{tweet.get('user_name', USERNAME)} (@{USERNAME})",
                "url": f"https://twitter.com/{USERNAME}",
                "icon_url": "https://abs.twimg.com/icons/apple-touch-icon-192x192.png"
            },
            "footer": {
                "text": "Twitter/X",
                "icon_url": "https://abs.twimg.com/icons/apple-touch-icon-192x192.png"
            }
        }

        if tweet.get('timestamp'):
            main_embed["timestamp"] = tweet['timestamp']

        if images:
            main_embed["image"] = {"url": images[0]}
            print(f"  🖼️  Image 1: {images[0][:70]}...")

        embeds = [main_embed]
        for extra_img in images[1:4]:
            if extra_img:
                embeds.append({"url": tweet['link'], "image": {"url": extra_img}})
                print(f"  🖼️  Extra image: {extra_img[:70]}...")

        return embeds

    def send_to_discord(self, tweet: dict) -> bool:
        """Send tweet to Discord"""
        embeds = self.create_discord_embeds(tweet)
        payload = {"embeds": embeds[:10]}

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            media = len(tweet.get('images', []))
            has_video = bool(tweet.get('video_url'))
            label = f"{media} image(s)" if media else "text only"
            label += " + video" if has_video else ""
            print(f"  ✅ Sent to Discord! ({label})")
            return True
        except Exception as e:
            print(f"  ❌ Error sending to Discord: {e}")
            return False

    def run(self):
        print(f"🤖 Twitter to Discord Bot v8 (Updated live instances)")
        print(f"📡 Monitoring: @{USERNAME}")
        print(f"🔄 Check interval: {self.check_interval // 3600}h")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

        while True:
            try:
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f"🔍 [{current_time}] Checking for new tweets...")

                tweet_ids = self.get_tweet_ids()

                if not tweet_ids:
                    print(f"  ⚠️  Could not fetch tweet IDs - will retry next check\n")
                else:
                    new_ids = [tid for tid in tweet_ids if tid not in self.seen_tweets]

                    if self.first_run:
                        print(f"  🎯 First run - marking {len(tweet_ids)} tweets as seen")
                        for tid in tweet_ids:
                            self.seen_tweets.add(tid)
                        self.save_seen_tweets()
                        self.first_run = False
                        print(f"  ✅ Ready! Will now post only NEW tweets\n")

                    elif not new_ids:
                        print(f"  ℹ️  No new tweets\n")

                    else:
                        print(f"  🆕 Found {len(new_ids)} new tweet(s)!\n")
                        for i, tweet_id in enumerate(reversed(new_ids), 1):
                            print(f"  📥 Fetching tweet {i}/{len(new_ids)} (ID: {tweet_id})")
                            tweet = self.get_tweet_details(tweet_id)
                            if tweet:
                                self.send_to_discord(tweet)
                                self.seen_tweets.add(tweet_id)
                                self.save_seen_tweets()
                            else:
                                self.seen_tweets.add(tweet_id)
                                self.save_seen_tweets()
                            print()
                            if i < len(new_ids):
                                time.sleep(2)

            except Exception as e:
                print(f"❌ Error: {e}\n")

            print(f"💤 Sleeping {self.check_interval // 3600}h...")
            print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
            time.sleep(self.check_interval)


def main():
    DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL', '')
    if not DISCORD_WEBHOOK_URL:
        print("❌ DISCORD_WEBHOOK_URL not set")
        return

    print("🚀 Initializing...\n")
    bot = TwitterToDiscord(discord_webhook_url=DISCORD_WEBHOOK_URL, check_interval=3600)
    bot.run()


if __name__ == "__main__":
    main()
