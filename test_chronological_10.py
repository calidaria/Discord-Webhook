#!/usr/bin/env python3
"""
Test Script - Posts the last 10 tweets in CHRONOLOGICAL order (oldest first)
Useful for testing the full flow and seeing how a "catch up" would look
"""

import requests
import os
import re
import time
from datetime import datetime
import xml.etree.ElementTree as ET

USERNAME = "SoJ_JP"  # Change this if needed

def get_latest_tweet_ids(limit=10):
    """Get latest tweet IDs - tries multiple sources"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, application/rss+xml, */*',
        'Origin': 'https://platform.twitter.com',
        'Referer': 'https://platform.twitter.com/',
    }

    # Try Twitter Syndication API first
    print("  🔄 Trying Twitter Syndication API...")
    try:
        url = f"https://cdn.syndication.twimg.com/timeline/profile?screen_name={USERNAME}&limit={limit}"
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            ids = []
            for item in data.get('timeline', [])[:limit]:
                tweet_id = str(item.get('tweet_id', '') or item.get('id_str', '') or item.get('id', ''))
                tweet_id = re.sub(r'[^0-9]', '', tweet_id)
                if tweet_id and len(tweet_id) > 5:
                    ids.append(tweet_id)
            if ids:
                print(f"  ✅ Got {len(ids)} IDs from Syndication API!\n")
                return ids
    except Exception as e:
        print(f"  ❌ Syndication failed: {str(e)[:60]}")

    # Try RSSHub
    print("  🔄 Trying RSSHub...")
    for instance in [
        f"https://rsshub.app/twitter/user/{USERNAME}",
        f"https://rsshub.rssforever.com/twitter/user/{USERNAME}",
    ]:
        try:
            response = requests.get(instance, headers=headers, timeout=20)
            if response.status_code == 200:
                ids = parse_rss_ids(response.text, limit)
                if ids:
                    print(f"  ✅ Got {len(ids)} IDs from RSSHub!\n")
                    return ids
        except Exception as e:
            print(f"  ❌ {str(e)[:60]}")

    # Try Nitter
    print("  🔄 Trying Nitter instances...")
    for instance in [
        f"https://nitter.net/{USERNAME}/rss",
        f"https://nitter.poast.org/{USERNAME}/rss",
        f"https://nitter.privacydev.net/{USERNAME}/rss",
        f"https://nitter.pussthecat.org/{USERNAME}/rss",
        f"https://nitter.fdn.fr/{USERNAME}/rss",
    ]:
        try:
            response = requests.get(instance, headers=headers, timeout=15)
            if response.status_code == 200:
                ids = parse_rss_ids(response.text, limit)
                if ids:
                    print(f"  ✅ Got {len(ids)} IDs from Nitter!\n")
                    return ids
        except Exception as e:
            print(f"  ❌ {str(e)[:60]}")

    return []

def parse_rss_ids(rss_content: str, limit: int) -> list:
    ids = []
    try:
        root = ET.fromstring(rss_content)
        for item in root.findall('.//item')[:limit]:
            link = item.find('link')
            if link is not None and link.text:
                tweet_id = re.sub(r'[^0-9]', '', link.text.rstrip('/').split('/')[-1].split('#')[0])
                if tweet_id and len(tweet_id) > 5:
                    ids.append(tweet_id)
    except:
        pass
    return ids

def get_tweet_details(tweet_id: str) -> dict:
    """Get full tweet details including images/videos from fxtwitter"""
    try:
        url = f"https://api.fxtwitter.com/{USERNAME}/status/{tweet_id}"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            tweet = data.get('tweet', {})
            if not tweet:
                return None

            images, video_url = [], None
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
                if not images and gifs[0].get('thumbnail_url'):
                    images.append(gifs[0]['thumbnail_url'])

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
                'timestamp_raw': created_at,
                'user_name': tweet.get('author', {}).get('name', USERNAME),
            }
    except Exception as e:
        print(f"  ❌ fxtwitter error: {e}")
    return None

def send_to_discord(tweet: dict, webhook_url: str, index: int, total: int):
    text = tweet.get('text', '')
    images = tweet.get('images', [])
    video_url = tweet.get('video_url')

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
            "text": f"Twitter/X • {index}/{total} (chronological test)",
            "icon_url": "https://abs.twimg.com/icons/apple-touch-icon-192x192.png"
        }
    }

    if tweet.get('timestamp'):
        main_embed["timestamp"] = tweet['timestamp']

    if images:
        main_embed["image"] = {"url": images[0]}

    embeds = [main_embed]
    for img in images[1:4]:
        if img:
            embeds.append({"url": tweet['link'], "image": {"url": img}})

    response = requests.post(webhook_url, json={"embeds": embeds[:10]}, timeout=10)
    response.raise_for_status()

def main():
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL', '')
    if not webhook_url:
        print("❌ DISCORD_WEBHOOK_URL not set")
        return

    print(f"🧪 CHRONOLOGICAL TEST - Last 10 posts from @{USERNAME}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    print("📥 Fetching latest tweet IDs...")
    tweet_ids = get_latest_tweet_ids(limit=10)

    if not tweet_ids:
        print("❌ Could not fetch any tweet IDs")
        return

    print(f"📋 Found {len(tweet_ids)} tweet IDs (newest first): {tweet_ids}\n")
    print("📥 Fetching full details for each tweet...\n")

    # Fetch all tweet details first
    tweets = []
    for tweet_id in tweet_ids:
        tweet = get_tweet_details(tweet_id)
        if tweet:
            tweets.append(tweet)
        time.sleep(1)  # Be nice to fxtwitter API

    if not tweets:
        print("❌ Could not fetch details for any tweets")
        return

    # Sort chronologically (oldest first) using the raw timestamp
    def sort_key(t):
        return t.get('timestamp') or ''
    
    tweets.sort(key=sort_key)

    print(f"✅ Got details for {len(tweets)} tweets. Posting in chronological order (oldest → newest)...\n")

    # Post each one in order, oldest first
    success = 0
    for i, tweet in enumerate(tweets, 1):
        print(f"━━━ Posting {i}/{len(tweets)} (ID: {tweet['id']}) ━━━")
        print(f"  📝 {tweet['text'][:70]}...")
        print(f"  🖼️  Images: {len(tweet['images'])}")
        if tweet.get('video_url'):
            print(f"  🎬 Has video!")

        try:
            send_to_discord(tweet, webhook_url, i, len(tweets))
            print(f"  ✅ Posted!")
            success += 1
        except Exception as e:
            print(f"  ❌ Failed: {e}")

        if i < len(tweets):
            time.sleep(2)  # Rate limit between Discord posts
        print()

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ Done! Posted {success}/{len(tweets)} tweets in chronological order.")
    print(f"👀 Check your Discord channel!")

if __name__ == "__main__":
    main()
