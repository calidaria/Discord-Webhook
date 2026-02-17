#!/usr/bin/env python3
"""
Test Script - Sends latest 3 posts from @SoJ_Global with real images/videos
Uses RSSHub + fxtwitter for reliability
"""

import requests
import os
import re
import time
from datetime import datetime
import xml.etree.ElementTree as ET

USERNAME = "SoJ_Global"

def get_latest_tweet_ids():
    """Get latest 3 tweet IDs using RSSHub (more reliable than Nitter)"""
    
    rsshub_instances = [
        f"https://rsshub.app/twitter/user/{USERNAME}",
        f"https://rsshub.feeded.app/twitter/user/{USERNAME}",
        f"https://rss.shab.fun/twitter/user/{USERNAME}",
        f"https://rsshub.rssforever.com/twitter/user/{USERNAME}",
    ]

    nitter_instances = [
        f"https://nitter.net/{USERNAME}/rss",
        f"https://nitter.poast.org/{USERNAME}/rss",
    ]

    headers = {'User-Agent': 'Mozilla/5.0'}

    print("🔄 Trying RSSHub instances...")
    for url in rsshub_instances:
        try:
            print(f"  📡 {url.split('/')[2]}...")
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                ids = parse_ids(response.text)
                if ids:
                    print(f"  ✅ Got {len(ids)} IDs!\n")
                    return ids[:3]
        except Exception as e:
            print(f"  ❌ {str(e)[:50]}")

    print("🔄 Trying Nitter as fallback...")
    for url in nitter_instances:
        try:
            print(f"  📡 {url.split('/')[2]}...")
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                ids = parse_ids(response.text)
                if ids:
                    print(f"  ✅ Got {len(ids)} IDs!\n")
                    return ids[:3]
        except Exception as e:
            print(f"  ❌ {str(e)[:50]}")

    return []

def parse_ids(rss_content: str) -> list:
    ids = []
    try:
        root = ET.fromstring(rss_content)
        for item in root.findall('.//item')[:3]:
            link = item.find('link')
            if link is not None and link.text:
                tweet_id = re.sub(r'[^0-9]', '', link.text.rstrip('/').split('/')[-1].split('#')[0])
                if tweet_id and len(tweet_id) > 5:
                    ids.append(tweet_id)
    except:
        pass
    return ids

def get_tweet_details(tweet_id: str) -> dict:
    """Get full tweet with images/videos from fxtwitter"""
    try:
        url = f"https://api.fxtwitter.com/{USERNAME}/status/{tweet_id}"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)

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
    except Exception as e:
        print(f"  ❌ fxtwitter error: {e}")
    return None

def send_to_discord(tweet: dict, webhook_url: str, index: int) -> bool:
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
            "name": f"{tweet.get('user_name', 'Sword of Justice')} (@{USERNAME})",
            "url": f"https://twitter.com/{USERNAME}",
            "icon_url": "https://abs.twimg.com/icons/apple-touch-icon-192x192.png"
        },
        "footer": {
            "text": f"Twitter/X • TEST #{index}",
            "icon_url": "https://abs.twimg.com/icons/apple-touch-icon-192x192.png"
        }
    }

    if tweet.get('timestamp'):
        main_embed["timestamp"] = tweet['timestamp']

    if images:
        main_embed["image"] = {"url": images[0]}

    embeds = [main_embed]
    for extra_img in images[1:4]:
        if extra_img:
            embeds.append({"url": tweet['link'], "image": {"url": extra_img}})

    try:
        response = requests.post(
            webhook_url,
            json={"content": f"**🧪 TEST #{index}** - Latest @{USERNAME} post:", "embeds": embeds[:10]},
            timeout=10
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"  ❌ Discord error: {e}")
        return False

def main():
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL', '')
    if not webhook_url:
        print("❌ DISCORD_WEBHOOK_URL not set")
        return

    print("🧪 TEST SCRIPT - Latest 3 posts from @SoJ_Global")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    tweet_ids = get_latest_tweet_ids()
    if not tweet_ids:
        print("❌ Could not fetch tweet IDs - all sources down")
        return

    print(f"📋 Found tweet IDs: {tweet_ids}\n")

    success = 0
    for i, tweet_id in enumerate(tweet_ids, 1):
        print(f"━━━ Tweet {i}/3 (ID: {tweet_id}) ━━━")
        tweet = get_tweet_details(tweet_id)

        if not tweet:
            print(f"  ⚠️  Could not get details, skipping\n")
            continue

        print(f"  📝 {tweet['text'][:80]}...")
        print(f"  🖼️  Images: {len(tweet['images'])}")
        for j, img in enumerate(tweet['images'], 1):
            print(f"      {j}. {img[:80]}")
        if tweet.get('video_url'):
            print(f"  🎬 Has video!")

        if send_to_discord(tweet, webhook_url, i):
            print(f"  ✅ Sent to Discord!")
            success += 1

        if i < len(tweet_ids):
            time.sleep(2)
        print()

    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ Done! Sent {success}/{len(tweet_ids)} posts to Discord.")
    print(f"👀 Check your Discord channel!")

if __name__ == "__main__":
    main()
