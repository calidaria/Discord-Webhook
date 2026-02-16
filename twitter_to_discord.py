#!/usr/bin/env python3
"""
Twitter/X to Discord Webhook Bot - Version 4
Fixed: Duplicate prevention and enhanced image extraction
"""

import requests
import time
import json
import os
from datetime import datetime
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import re
from html import unescape

class TwitterToDiscord:
    def __init__(self, discord_webhook_url: str, check_interval: int = 300):
        """
        Initialize the bot
        
        Args:
            discord_webhook_url: Your Discord webhook URL
            check_interval: How often to check for new tweets (in seconds, default 5 minutes)
        """
        self.webhook_url = discord_webhook_url
        self.check_interval = check_interval
        self.seen_tweets_file = "seen_tweets.json"
        self.seen_tweets = self.load_seen_tweets()
        self.first_run = len(self.seen_tweets) == 0  # Track if this is first run
        
    def load_seen_tweets(self) -> set:
        """Load previously seen tweet IDs from file"""
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
        """Save seen tweet IDs to file"""
        try:
            with open(self.seen_tweets_file, 'w') as f:
                json.dump(list(self.seen_tweets), f)
            print(f"💾 Saved {len(self.seen_tweets)} seen tweets to file")
        except Exception as e:
            print(f"⚠️  Warning: Could not save seen tweets: {e}")
    
    def extract_images_from_description(self, description: str) -> List[str]:
        """Extract all image URLs from RSS description HTML"""
        images = []
        if not description:
            return images
        
        # Unescape HTML entities
        description = unescape(description)
        
        # Find all img tags - try multiple patterns
        patterns = [
            r'<img[^>]+src=["\']([^"\']+)["\']',  # Standard img tags
            r'https://[^"\s]+\.(?:jpg|jpeg|png|gif|webp)',  # Direct image URLs
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            for url in matches:
                # Filter out icons, emojis, and profile images
                if all(x not in url.lower() for x in ['twemoji', 'profile_images', 'emoji', 'icon']):
                    # Clean up the URL
                    url = url.split('?')[0]  # Remove query parameters
                    
                    # Convert Nitter media URLs to Twitter CDN
                    if '/pic/' in url or 'nitter' in url:
                        # Try to extract media filename
                        if '/media%2F' in url or '/media/' in url:
                            # Extract the media ID
                            media_match = re.search(r'media%2F([^?&\s]+)', url)
                            if not media_match:
                                media_match = re.search(r'media/([^?&\s]+)', url)
                            
                            if media_match:
                                media_id = media_match.group(1)
                                # Construct proper Twitter media URL
                                url = f"https://pbs.twimg.com/media/{media_id}"
                    
                    # Only add valid image URLs
                    if url.startswith('http') and any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']) or 'pbs.twimg.com' in url:
                        if url not in images:
                            images.append(url)
        
        return images
    
    def fetch_tweets_rss(self, username: str = "SoJ_Global") -> List[Dict]:
        """
        Fetch recent tweets using Nitter RSS
        """
        # Try multiple Nitter instances
        nitter_instances = [
            "nitter.poast.org",
            "nitter.privacydev.net",
            "nitter.net",
        ]
        
        for instance in nitter_instances:
            try:
                url = f"https://{instance}/{username}/rss"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                print(f"  📡 Trying {instance}...")
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    print(f"  ✅ Successfully fetched from {instance}")
                    tweets = self.parse_rss(response.text, username, instance)
                    if tweets:
                        return tweets
                else:
                    print(f"  ❌ Got status code {response.status_code}")
            except Exception as e:
                print(f"  ❌ Failed {instance}: {str(e)[:50]}")
                continue
        
        print(f"  ⚠️  All Nitter instances failed")
        return []
    
    def parse_rss(self, rss_content: str, username: str, instance: str) -> List[Dict]:
        """Parse RSS feed and extract tweet information including images"""
        tweets = []
        try:
            root = ET.fromstring(rss_content)
            
            # Find all items (tweets)
            items = root.findall('.//item')
            print(f"  📊 Found {len(items)} total items in RSS feed")
            
            for item in items[:10]:  # Get last 10 tweets
                try:
                    title = item.find('title')
                    description = item.find('description')
                    pub_date = item.find('pubDate')
                    link = item.find('link')
                    
                    if title is None or link is None:
                        continue
                    
                    # Extract tweet ID from link
                    link_text = link.text
                    tweet_id = link_text.split('/')[-1].split('#')[0]
                    
                    # Skip if we've already seen this tweet
                    if tweet_id in self.seen_tweets:
                        continue
                    
                    # Get tweet text (clean up)
                    tweet_text = title.text if title.text else ""
                    # Remove "RT by @username:" prefix if present
                    tweet_text = re.sub(r'^RT by @\w+:\s*', '', tweet_text)
                    
                    # Extract images from description
                    images = []
                    if description is not None and description.text:
                        images = self.extract_images_from_description(description.text)
                        
                        # Also try to get direct media links from the description
                        desc_text = description.text
                        # Look for nitter pic links
                        pic_links = re.findall(r'https://[^/]+/pic/[^"\s]+', desc_text)
                        for pic_link in pic_links:
                            # Convert to Twitter CDN
                            if '/media%2F' in pic_link:
                                media_id = re.search(r'media%2F([^/?]+)', pic_link)
                                if media_id:
                                    twitter_url = f"https://pbs.twimg.com/media/{media_id.group(1)}"
                                    if twitter_url not in images:
                                        images.append(twitter_url)
                    
                    # Convert link to Twitter URL
                    twitter_link = link_text.replace(instance, 'twitter.com')
                    
                    tweet_data = {
                        'id': tweet_id,
                        'text': tweet_text,
                        'created_at': pub_date.text if pub_date is not None else '',
                        'user_name': username.replace('_', ' ').title(),
                        'user_screen_name': username,
                        'link': twitter_link,
                        'images': images
                    }
                    
                    tweets.append(tweet_data)
                    
                    if images:
                        print(f"  🖼️  Tweet {tweet_id}: Found {len(images)} image(s)")
                    else:
                        print(f"  📝 Tweet {tweet_id}: Text only")
                        
                except Exception as e:
                    print(f"  ⚠️  Error parsing tweet item: {e}")
                    continue
            
            print(f"  ✅ Parsed {len(tweets)} new tweets from RSS")
                    
        except Exception as e:
            print(f"  ❌ Error parsing RSS: {e}")
        
        return tweets
    
    def create_discord_embed(self, tweet: Dict) -> Dict:
        """Create a Discord embed from tweet data with images"""
        tweet_id = tweet.get('id')
        username = tweet.get('user_screen_name', 'SoJ_Global')
        user_display_name = tweet.get('user_name', 'Sword of Justice')
        text = tweet.get('text', '')
        created_at = tweet.get('created_at')
        images = tweet.get('images', [])
        
        # Build tweet URL
        tweet_url = tweet.get('link', f"https://twitter.com/{username}/status/{tweet_id}")
        
        # Parse timestamp
        timestamp = None
        if created_at:
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(created_at)
                timestamp = dt.isoformat()
            except:
                pass
        
        # Create embed
        embed = {
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
            embed["timestamp"] = timestamp
        
        # Add the first image to the main embed
        if images and len(images) > 0:
            first_image = images[0]
            if first_image.startswith('http'):
                embed["image"] = {"url": first_image}
                print(f"    🎨 Added image to embed: {first_image[:60]}...")
        
        return embed
    
    def create_additional_image_embeds(self, tweet: Dict) -> List[Dict]:
        """Create additional embeds for extra images"""
        additional_embeds = []
        images = tweet.get('images', [])
        
        # If there are more than 1 image, create simple embeds for the rest
        if len(images) > 1:
            for image_url in images[1:4]:  # Up to 3 additional images
                if image_url.startswith('http'):
                    additional_embeds.append({
                        "url": tweet.get('link', ''),
                        "image": {"url": image_url}
                    })
        
        return additional_embeds
    
    def send_to_discord(self, tweet: Dict) -> bool:
        """Send tweet to Discord with all images"""
        # Create main embed
        main_embed = self.create_discord_embed(tweet)
        
        # Create additional embeds for extra images
        additional_embeds = self.create_additional_image_embeds(tweet)
        
        # Combine all embeds
        all_embeds = [main_embed] + additional_embeds
        
        payload = {
            "embeds": all_embeds[:10]  # Discord limit
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            image_count = len(tweet.get('images', []))
            if image_count > 0:
                print(f"  ✅ Sent tweet with {image_count} image(s)")
            else:
                print(f"  ✅ Sent text-only tweet")
            return True
        except Exception as e:
            print(f"  ❌ Error sending to Discord: {e}")
            return False
    
    def run(self):
        """Main bot loop"""
        print(f"🤖 Twitter to Discord Bot v4 (Fixed Duplicates & Images)")
        print(f"📡 Monitoring: @SoJ_Global")
        print(f"🔄 Check interval: {self.check_interval} seconds")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        
        while True:
            try:
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f"🔍 [{current_time}] Checking for new tweets...")
                
                tweets = self.fetch_tweets_rss()
                
                if not tweets:
                    print(f"  ℹ️  No new tweets found (or API unavailable)\n")
                else:
                    # On first run, just mark all tweets as seen without posting
                    if self.first_run:
                        print(f"  🎯 First run - marking {len(tweets)} existing tweets as seen")
                        for tweet in tweets:
                            self.seen_tweets.add(tweet.get('id'))
                        self.save_seen_tweets()
                        self.first_run = False
                        print(f"  ✅ Ready! Will now post only NEW tweets from this point forward\n")
                    else:
                        # Process new tweets in chronological order (oldest first)
                        new_tweets = []
                        for tweet in reversed(tweets):
                            tweet_id = tweet.get('id')
                            if tweet_id and tweet_id not in self.seen_tweets:
                                new_tweets.append(tweet)
                        
                        if new_tweets:
                            print(f"  🆕 Found {len(new_tweets)} new tweet(s)!\n")
                            
                            # Send each new tweet to Discord
                            for i, tweet in enumerate(new_tweets, 1):
                                print(f"  📤 Posting tweet {i}/{len(new_tweets)} (ID: {tweet.get('id')})")
                                
                                if self.send_to_discord(tweet):
                                    # Mark as seen immediately after successful send
                                    self.seen_tweets.add(tweet.get('id'))
                                    self.save_seen_tweets()
                                
                                # Rate limit between posts
                                if i < len(new_tweets):
                                    time.sleep(2)
                            
                            print(f"\n  ✅ Successfully posted {len(new_tweets)} new tweet(s)!\n")
                        else:
                            print(f"  ℹ️  All tweets already posted\n")
                
            except Exception as e:
                print(f"❌ Error in main loop: {e}\n")
                import traceback
                traceback.print_exc()
            
            # Wait before next check
            print(f"💤 Sleeping for {self.check_interval} seconds...")
            print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
            time.sleep(self.check_interval)

def main():
    # Configuration
    DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL', '')
    
    if not DISCORD_WEBHOOK_URL:
        print("❌ Error: DISCORD_WEBHOOK_URL environment variable not set")
        print("\nUsage:")
        print("  export DISCORD_WEBHOOK_URL='your_webhook_url_here'")
        print("  python twitter_to_discord.py")
        return
    
    print("🚀 Initializing bot...\n")
    
    # Create and run bot
    bot = TwitterToDiscord(
        discord_webhook_url=DISCORD_WEBHOOK_URL,
        check_interval=3600  # Check every 1 hour (3600 seconds)
    )
    bot.run()

if __name__ == "__main__":
    main()
