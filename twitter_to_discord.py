#!/usr/bin/env python3
"""
Twitter/X to Discord Webhook Bot - Version 5
Uses fxtwitter API for reliable image AND video support
"""

import requests
import time
import json
import os
import re
from datetime import datetime
import xml.etree.ElementTree as ET
from html import unescape

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

    def get_tweet_ids_from_rss(self, username: str) -> list:
        """Get list of recent tweet IDs from Nitter RSS"""
        nitter_instances = [
            "nitter.poast.org",
            "nitter.net",
            "nitter.privacydev.net",
            "nitter.mutant.tech",
        ]

        for instance in nitter_instances:
            try:
                url = f"https://{instance}/{username}/rss"
                headers = {'User-Agent': 'Mozilla/5.0'}
                print(f"  📡 Trying {instance}...")
                response = requests.get(url, headers=headers, timeout=15)

                if response.status_code == 200:
                    print(f"  ✅ Got RSS from {instance}")
                    return self.parse_tweet_ids(response.text)
            except Exception as e:
                print(f"  ❌ Failed {instance}: {str(e)[:60]}")
                continue

        print("  ⚠️  All Nitter instances failed")
        return []

    def parse_tweet_ids(self, rss_content: str) -> list:
        """Extract tweet IDs and basic info from RSS"""
        tweet_ids = []
        try:
            root = ET.fromstring(rss_content)
            for item in root.findall('.//item')[:10]:
                link = item.find('link')
                pub_date = item.find('pubDate')
                if link is not None and link.text:
                    # Extract tweet ID from URL
                    tweet_id = link.text.rstrip('/').split('/')[-1].split('#')[0]
                    # Clean up ID (remove any non-numeric chars)
                    tweet_id = re.sub(r'[^0-9]', '', tweet_id)
                    if tweet_id and len(tweet_id) > 5:
                        tweet_ids.append({
                            'id': tweet_id,
                            'pub_date': pub_date.text if pub_date is not None else ''
                        })
        except Exception as e:
            print(f"  ❌ Error parsing RSS: {e}")
        print(f"  📊 Found {len(tweet_ids)} tweet IDs in RSS")
        return tweet_ids

    def get_tweet_details(self, tweet_id: str, username: str) -> dict:
        """
        Get full tweet details including images/videos using fxtwitter API
        This is the key method that gets media reliably!
        """
        try:
            # fxtwitter has a great API for getting tweet details with media
            url = f"https://api.fxtwitter.com/{username}/status/{tweet_id}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                tweet = data.get('tweet', {})
                
                if not tweet:
                    return None
                
                # Extract media
                images = []
                video_url = None
                video_thumbnail = None
                
                media = tweet.get('media', {})
                
                # Get photos
                photos = media.get('photos', [])
                for photo in photos:
                    img_url = photo.get('url', '')
                    if img_url:
                        images.append(img_url)
                
                # Get videos
                videos = media.get('videos', [])
                if videos:
                    video = videos[0]  # Get first video
                    video_url = video.get('url', '')
                    video_thumbnail = video.get('thumbnail_url', '')
                    # Use thumbnail as image if no photos
                    if video_thumbnail and not images:
                        images.append(video_thumbnail)
                
                # Get GIFs (treated as videos in Twitter)
                gifs = media.get('gifs', [])
                if gifs and not video_url:
                    gif = gifs[0]
                    video_url = gif.get('url', '')
                    if video_url and not images:
                        images.append(gif.get('thumbnail_url', ''))

                # Parse timestamp
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
                    'link': f"https://twitter.com/{username}/status/{tweet_id}",
                    'images': images,
                    'video_url': video_url,
                    'video_thumbnail': video_thumbnail,
                    'has_media': len(images) > 0 or video_url is not None,
                    'timestamp': timestamp,
                    'user_name': tweet.get('author', {}).get('name', username),
                    'user_screen_name': username,
                }
            else:
                print(f"  ⚠️  fxtwitter returned status {response.status_code}")
                return None
                
        except Exception as e:
            print(f"  ❌ Error fetching tweet details: {e}")
            return None

    def create_discord_embeds(self, tweet: dict) -> list:
        """Create Discord embeds with images for a tweet"""
        username = tweet.get('user_screen_name', 'SoJ_Global')
        user_display_name = tweet.get('user_name', 'Sword of Justice')
        text = tweet.get('text', '')
        tweet_url = tweet.get('link', '')
        images = tweet.get('images', [])
        video_url = tweet.get('video_url')
        timestamp = tweet.get('timestamp')

        # Main embed
        main_embed = {
            "title": f"New post from @{username}",
            "description": text[:4096] if text else "No text content",
            "url": tweet_url,
            "color": 1942002,  # Twitter blue
            "author": {
                "name": f"{user_display_name} (@{username})",
                "url": f"https://twitter.com/{username}",
                "icon_url": "https://abs.twimg.com/icons/apple-touch-icon-192x192.png"
            },
            "footer": {
                "text": "Twitter/X",
                "icon_url": "https://abs.twimg.com/icons/apple-touch-icon-192x192.png"
            }
        }

        if timestamp:
            main_embed["timestamp"] = timestamp

        # Add first image to main embed
        if images and images[0]:
            main_embed["image"] = {"url": images[0]}
            print(f"  🖼️  Added image: {images[0][:70]}...")

        # If there's a video, add a note
        if video_url:
            current_desc = main_embed.get("description", "")
            main_embed["description"] = current_desc + f"\n\n🎬 **[Click to watch video]({tweet_url})**"
            print(f"  🎬 Tweet has video: {video_url[:70]}...")

        embeds = [main_embed]

        # Add additional images as extra embeds (Discord trick for galleries)
        if len(images) > 1:
            for extra_image in images[1:4]:  # Max 4 images total
                if extra_image:
                    embeds.append({
                        "url": tweet_url,  # Same URL groups them as a gallery!
                        "image": {"url": extra_image}
                    })
                    print(f"  🖼️  Added extra image: {extra_image[:70]}...")

        return embeds

    def send_to_discord(self, tweet: dict) -> bool:
        """Send tweet embed to Discord"""
        embeds = self.create_discord_embeds(tweet)

        payload = {"embeds": embeds[:10]}

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()

            media_count = len(tweet.get('images', []))
            has_video = tweet.get('video_url') is not None

            if has_video:
                print(f"  ✅ Sent tweet with video + {media_count} image(s)")
            elif media_count > 0:
                print(f"  ✅ Sent tweet with {media_count} image(s)")
            else:
                print(f"  ✅ Sent text-only tweet")
            return True

        except Exception as e:
            print(f"  ❌ Error sending to Discord: {e}")
            return False

    def run(self):
        """Main bot loop"""
        print(f"🤖 Twitter to Discord Bot v5 (fxtwitter - Reliable Images & Videos)")
        print(f"📡 Monitoring: @SoJ_Global")
        print(f"🔄 Check interval: {self.check_interval} seconds ({self.check_interval // 3600}h)")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

        username = "SoJ_Global"

        while True:
            try:
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f"🔍 [{current_time}] Checking for new tweets...")

                # Step 1: Get tweet IDs from RSS
                tweet_items = self.get_tweet_ids_from_rss(username)

                if not tweet_items:
                    print(f"  ⚠️  Could not fetch tweet IDs\n")
                else:
                    # Step 2: Find new tweet IDs
                    new_tweet_items = [
                        t for t in tweet_items
                        if t['id'] not in self.seen_tweets
                    ]

                    if self.first_run:
                        print(f"  🎯 First run - marking {len(tweet_items)} existing tweets as seen (no posting)")
                        for t in tweet_items:
                            self.seen_tweets.add(t['id'])
                        self.save_seen_tweets()
                        self.first_run = False
                        print(f"  ✅ Ready! Will now post only NEW tweets\n")

                    elif not new_tweet_items:
                        print(f"  ℹ️  No new tweets found\n")

                    else:
                        print(f"  🆕 Found {len(new_tweet_items)} new tweet(s)!\n")

                        # Process oldest first
                        for i, item in enumerate(reversed(new_tweet_items), 1):
                            tweet_id = item['id']
                            print(f"  📥 Fetching details for tweet {i}/{len(new_tweet_items)} (ID: {tweet_id})")

                            # Step 3: Get full details including media from fxtwitter
                            tweet = self.get_tweet_details(tweet_id, username)

                            if tweet:
                                print(f"  📤 Sending to Discord...")
                                if self.send_to_discord(tweet):
                                    self.seen_tweets.add(tweet_id)
                                    self.save_seen_tweets()
                            else:
                                # Even if we can't get details, mark as seen
                                self.seen_tweets.add(tweet_id)
                                self.save_seen_tweets()
                                print(f"  ⚠️  Could not get tweet details, skipping")

                            print()
                            if i < len(new_tweet_items):
                                time.sleep(2)

                        print(f"  ✅ Done processing new tweets!\n")

            except Exception as e:
                print(f"❌ Error in main loop: {e}\n")
                import traceback
                traceback.print_exc()

            print(f"💤 Sleeping for {self.check_interval} seconds ({self.check_interval // 3600}h)...")
            print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
            time.sleep(self.check_interval)


def main():
    DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL', '')

    if not DISCORD_WEBHOOK_URL:
        print("❌ Error: DISCORD_WEBHOOK_URL not set")
        return

    print("🚀 Initializing bot...\n")

    bot = TwitterToDiscord(
        discord_webhook_url=DISCORD_WEBHOOK_URL,
        check_interval=3600  # 1 hour
    )
    bot.run()


if __name__ == "__main__":
    main()
