#!/usr/bin/env python3
"""
Test Script - Always sends the latest 3 posts from @SoJ_Global
Use this to test if images and videos are working
"""

import requests
import os
import re
from datetime import datetime
import xml.etree.ElementTree as ET

USERNAME = "SoJ_Global"

def get_latest_tweet_ids():
    """Get the latest 3 tweet IDs from Nitter RSS"""
    nitter_instances = [
        "nitter.poast.org",
        "nitter.net",
        "nitter.privacydev.net",
        "nitter.mutant.tech",
    ]

    for instance in nitter_instances:
        try:
            url = f"https://{instance}/{USERNAME}/rss"
            headers = {'User-Agent': 'Mozilla/5.0'}
            print(f"📡 Trying {instance}...")
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                root = ET.fromstring(response.text)
                items = root.findall('.//item')
                
                tweet_ids = []
                for item in items[:3]:  # Get latest 3
                    link = item.find('link')
                    if link is not None and link.text:
                        tweet_id = link.text.rstrip('/').split('/')[-1].split('#')[0]
                        tweet_id = re.sub(r'[^0-9]', '', tweet_id)
                        if tweet_id:
                            tweet_ids.append(tweet_id)

                print(f"✅ Got {len(tweet_ids)} tweet IDs from {instance}")
                return tweet_ids

        except Exception as e:
            print(f"❌ Failed {instance}: {str(e)[:60]}")
            continue

    print("❌ All Nitter instances failed")
    return []

def get_tweet_details(tweet_id: str) -> dict:
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
            print(f"  ❌ fxtwitter returned status {response.status_code}")
            return None

    except Exception as e:
        print(f"  ❌ Error fetching tweet details: {e}")
        return None

def send_to_discord(tweet: dict, webhook_url: str, index: int) -> bool:
    """Send tweet embed to Discord"""
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

    # Add extra images
    for extra_img in images[1:4]:
        if extra_img:
            embeds.append({
                "url": tweet['link'],
                "image": {"url": extra_img}
            })

    payload = {
        "content": f"**🧪 TEST #{index}** - @{USERNAME} latest post:",
        "embeds": embeds[:10]
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"  ❌ Failed to send: {e}")
        return False

def main():
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL', '')

    if not webhook_url:
        print("❌ DISCORD_WEBHOOK_URL not set")
        return

    print("🧪 TEST SCRIPT - Sending latest 3 posts from @SoJ_Global")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    # Step 1: Get latest 3 tweet IDs
    tweet_ids = get_latest_tweet_ids()
    if not tweet_ids:
        print("❌ Could not get any tweet IDs")
        return

    print(f"\n📋 Got {len(tweet_ids)} tweet IDs: {tweet_ids}\n")

    # Step 2: Fetch and send each one
    success = 0
    for i, tweet_id in enumerate(tweet_ids, 1):
        print(f"━━━ Tweet {i}/3 (ID: {tweet_id}) ━━━")
        
        tweet = get_tweet_details(tweet_id)
        if not tweet:
            print(f"  ⚠️  Skipping - could not fetch details\n")
            continue

        print(f"  📝 Text: {tweet['text'][:60]}...")
        print(f"  🖼️  Images: {len(tweet['images'])}")
        for j, img in enumerate(tweet['images'], 1):
            print(f"      {j}. {img[:80]}")
        if tweet.get('video_url'):
            print(f"  🎬 Video: YES")

        if send_to_discord(tweet, webhook_url, i):
            print(f"  ✅ Sent to Discord!")
            success += 1
        
        import time
        time.sleep(2)  # Small delay between posts
        print()

    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ Done! Sent {success}/3 tweets to Discord.")
    print(f"Check your Discord channel to see if images/videos worked!")

if __name__ == "__main__":
    main()
