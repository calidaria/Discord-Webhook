#!/usr/bin/env python3
"""
Test Script - Sends the latest @SoJ_Global tweet to Discord
Use this to preview the embed format
"""

import requests
import os
import xml.etree.ElementTree as ET
import re
from html import unescape
from email.utils import parsedate_to_datetime

def extract_images_from_description(description: str):
    """Extract all image URLs from RSS description HTML"""
    images = []
    if not description:
        return images
    
    description = unescape(description)
    
    patterns = [
        r'<img[^>]+src=["\']([^"\']+)["\']',
        r'https://[^"\s]+\.(?:jpg|jpeg|png|gif|webp)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, description, re.IGNORECASE)
        for url in matches:
            if all(x not in url.lower() for x in ['twemoji', 'profile_images', 'emoji', 'icon']):
                url = url.split('?')[0]
                
                if '/media%2F' in url or '/media/' in url:
                    media_match = re.search(r'media%2F([^?&\s]+)', url)
                    if not media_match:
                        media_match = re.search(r'media/([^?&\s]+)', url)
                    
                    if media_match:
                        media_id = media_match.group(1)
                        url = f"https://pbs.twimg.com/media/{media_id}"
                
                if url.startswith('http') and (any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']) or 'pbs.twimg.com' in url):
                    if url not in images:
                        images.append(url)
    
    return images

def fetch_latest_tweet():
    """Fetch the latest tweet from @SoJ_Global"""
    nitter_instances = [
        "nitter.poast.org",
        "nitter.privacydev.net",
        "nitter.net",
    ]
    
    for instance in nitter_instances:
        try:
            url = f"https://{instance}/SoJ_Global/rss"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            print(f"📡 Trying {instance}...")
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                print(f"✅ Successfully fetched from {instance}\n")
                
                # Parse RSS
                root = ET.fromstring(response.text)
                items = root.findall('.//item')
                
                if not items:
                    print("⚠️  No tweets found in RSS feed")
                    continue
                
                # Get the first (most recent) tweet
                item = items[0]
                
                title = item.find('title')
                description = item.find('description')
                pub_date = item.find('pubDate')
                link = item.find('link')
                
                if title is None or link is None:
                    continue
                
                tweet_id = link.text.split('/')[-1].split('#')[0]
                tweet_text = title.text if title.text else ""
                tweet_text = re.sub(r'^RT by @\w+:\s*', '', tweet_text)
                
                # Extract images
                images = []
                if description is not None and description.text:
                    images = extract_images_from_description(description.text)
                
                twitter_link = link.text.replace(instance, 'twitter.com')
                
                # Parse timestamp
                timestamp = None
                if pub_date is not None:
                    try:
                        dt = parsedate_to_datetime(pub_date.text)
                        timestamp = dt.isoformat()
                    except:
                        pass
                
                return {
                    'id': tweet_id,
                    'text': tweet_text,
                    'link': twitter_link,
                    'images': images,
                    'timestamp': timestamp
                }
                
        except Exception as e:
            print(f"❌ Failed {instance}: {e}")
            continue
    
    return None

def create_discord_embed(tweet):
    """Create Discord embed from tweet data"""
    embed = {
        "title": "New post from @SoJ_Global",
        "description": tweet['text'][:4096] if tweet['text'] else "No text content",
        "url": tweet['link'],
        "color": 1942002,  # Twitter blue
        "author": {
            "name": "Sword of Justice (@SoJ_Global)",
            "url": "https://twitter.com/SoJ_Global",
            "icon_url": "https://abs.twimg.com/icons/apple-touch-icon-192x192.png"
        },
        "footer": {
            "text": "Twitter/X",
            "icon_url": "https://abs.twimg.com/icons/apple-touch-icon-192x192.png"
        }
    }
    
    if tweet['timestamp']:
        embed["timestamp"] = tweet['timestamp']
    
    # Add first image
    if tweet['images']:
        embed["image"] = {"url": tweet['images'][0]}
    
    return embed

def create_additional_embeds(tweet):
    """Create embeds for additional images"""
    additional = []
    if len(tweet['images']) > 1:
        for img_url in tweet['images'][1:4]:
            additional.append({
                "url": tweet['link'],
                "image": {"url": img_url}
            })
    return additional

def send_test_embed():
    """Send test embed to Discord"""
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL', '')
    
    if not webhook_url:
        print("❌ Error: DISCORD_WEBHOOK_URL environment variable not set")
        print("\nTo run this test:")
        print("  export DISCORD_WEBHOOK_URL='your_webhook_url'")
        print("  python test_embed.py")
        return
    
    print("🧪 TEST EMBED SCRIPT")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    # Fetch latest tweet
    print("📥 Fetching latest tweet from @SoJ_Global...\n")
    tweet = fetch_latest_tweet()
    
    if not tweet:
        print("\n❌ Could not fetch latest tweet")
        return
    
    print("📊 Tweet Details:")
    print(f"  ID: {tweet['id']}")
    print(f"  Text: {tweet['text'][:100]}...")
    print(f"  Images: {len(tweet['images'])} found")
    if tweet['images']:
        for i, img in enumerate(tweet['images'], 1):
            print(f"    {i}. {img[:80]}...")
    print()
    
    # Create embeds
    main_embed = create_discord_embed(tweet)
    additional_embeds = create_additional_embeds(tweet)
    all_embeds = [main_embed] + additional_embeds
    
    # Send to Discord
    print("📤 Sending test embed to Discord...\n")
    
    payload = {"embeds": all_embeds[:10]}
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        
        print("✅ SUCCESS! Test embed sent to Discord!")
        print(f"\nCheck your Discord channel to see the format!")
        print(f"\nEmbed details:")
        print(f"  - Title: New post from @SoJ_Global")
        print(f"  - Color: Twitter blue")
        print(f"  - Images: {len(tweet['images'])} included")
        print(f"  - Link: {tweet['link']}")
        
    except Exception as e:
        print(f"❌ Error sending to Discord: {e}")

if __name__ == "__main__":
    send_test_embed()
