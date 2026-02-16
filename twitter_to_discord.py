#!/usr/bin/env python3
"""
Twitter/X to Discord Webhook Bot - Version 2
Monitors @SoJ_Global and posts new tweets to Discord via webhook
Uses RSS feed method (more reliable)
"""

import requests
import time
import json
import os
from datetime import datetime
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import re

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
        
    def load_seen_tweets(self) -> set:
        """Load previously seen tweet IDs from file"""
        if os.path.exists(self.seen_tweets_file):
            try:
                with open(self.seen_tweets_file, 'r') as f:
                    return set(json.load(f))
            except:
                return set()
        return set()
    
    def save_seen_tweets(self):
        """Save seen tweet IDs to file"""
        try:
            with open(self.seen_tweets_file, 'w') as f:
                json.dump(list(self.seen_tweets), f)
        except Exception as e:
            print(f"Warning: Could not save seen tweets: {e}")
    
    def fetch_tweets_rss(self, username: str = "SoJ_Global") -> List[Dict]:
        """
        Fetch recent tweets using Nitter RSS (more reliable)
        """
        # Try multiple Nitter instances
        nitter_instances = [
            "nitter.poast.org",
            "nitter.net",
            "nitter.privacydev.net",
        ]
        
        for instance in nitter_instances:
            try:
                url = f"https://{instance}/{username}/rss"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    return self.parse_rss(response.text, username)
            except Exception as e:
                print(f"Failed to fetch from {instance}: {e}")
                continue
        
        # Fallback: try vxtwitter scraping
        return self.fetch_tweets_vxtwitter(username)
    
    def fetch_tweets_vxtwitter(self, username: str) -> List[Dict]:
        """
        Fallback method using vxtwitter
        """
        try:
            # This is a simple fallback that checks the profile
            url = f"https://api.vxtwitter.com/{username}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Extract tweet data
                tweets = []
                if 'tweets' in data:
                    for tweet in data['tweets'][:5]:  # Get last 5 tweets
                        tweets.append({
                            'id': tweet.get('tweetID', ''),
                            'text': tweet.get('text', ''),
                            'created_at': tweet.get('date', ''),
                            'user_name': tweet.get('user_name', username),
                            'user_screen_name': tweet.get('user_screen_name', username),
                            'media_url': tweet.get('media_extended', [{}])[0].get('url', '') if tweet.get('media_extended') else ''
                        })
                return tweets
        except Exception as e:
            print(f"VXTwitter fallback failed: {e}")
        
        return []
    
    def parse_rss(self, rss_content: str, username: str) -> List[Dict]:
        """Parse RSS feed and extract tweet information"""
        tweets = []
        try:
            root = ET.fromstring(rss_content)
            
            # Find all items (tweets)
            for item in root.findall('.//item')[:10]:  # Get last 10 tweets
                try:
                    title = item.find('title')
                    description = item.find('description')
                    pub_date = item.find('pubDate')
                    link = item.find('link')
                    
                    if title is not None and link is not None:
                        # Extract tweet ID from link
                        tweet_id = link.text.split('/')[-1].split('#')[0]
                        
                        # Get tweet text
                        tweet_text = title.text if title.text else ""
                        
                        # Try to extract image URL from description
                        media_url = ""
                        if description is not None and description.text:
                            # Look for image URLs in description
                            img_match = re.search(r'<img src="([^"]+)"', description.text)
                            if img_match:
                                media_url = img_match.group(1)
                        
                        tweets.append({
                            'id': tweet_id,
                            'text': tweet_text,
                            'created_at': pub_date.text if pub_date is not None else '',
                            'user_name': username.replace('_', ' ').title(),
                            'user_screen_name': username,
                            'link': link.text,
                            'media_url': media_url
                        })
                except Exception as e:
                    print(f"Error parsing tweet item: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error parsing RSS: {e}")
        
        return tweets
    
    def create_discord_embed(self, tweet: Dict) -> Dict:
        """Create a Discord embed from tweet data"""
        tweet_id = tweet.get('id')
        username = tweet.get('user_screen_name', 'SoJ_Global')
        user_display_name = tweet.get('user_name', 'Sword of Justice')
        text = tweet.get('text', '')
        created_at = tweet.get('created_at')
        
        # Build tweet URL
        tweet_url = tweet.get('link', f"https://twitter.com/{username}/status/{tweet_id}")
        
        # Parse timestamp
        timestamp = None
        if created_at:
            try:
                # Try to parse RFC 2822 format (RSS standard)
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(created_at)
                timestamp = dt.isoformat()
            except:
                pass
        
        # Create embed
        embed = {
            "title": f"New post from @{username}",
            "description": text[:4096],  # Discord limit
            "url": tweet_url,
            "color": 1942002,  # Twitter blue color
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
        
        # Add media if present
        media_url = tweet.get('media_url', '')
        if media_url and media_url.startswith('http'):
            embed["image"] = {"url": media_url}
        
        return embed
    
    def send_to_discord(self, embed: Dict) -> bool:
        """Send embed to Discord webhook"""
        payload = {
            "embeds": [embed]
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            print(f"✓ Sent tweet to Discord: {embed.get('url', '')}")
            return True
        except Exception as e:
            print(f"✗ Error sending to Discord: {e}")
            return False
    
    def run(self):
        """Main bot loop"""
        print(f"🤖 Starting Twitter to Discord bot (v2)...")
        print(f"📡 Monitoring: @SoJ_Global")
        print(f"🔄 Check interval: {self.check_interval} seconds")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        while True:
            try:
                print(f"🔍 Checking for new tweets...")
                tweets = self.fetch_tweets_rss()
                
                if not tweets:
                    print(f"⚠️  Could not fetch tweets (API may be down)")
                else:
                    # Process tweets in reverse order (oldest first)
                    new_tweets = []
                    for tweet in reversed(tweets):
                        tweet_id = tweet.get('id')
                        if tweet_id and tweet_id not in self.seen_tweets:
                            new_tweets.append(tweet)
                            self.seen_tweets.add(tweet_id)
                    
                    # Send new tweets to Discord
                    for tweet in new_tweets:
                        embed = self.create_discord_embed(tweet)
                        self.send_to_discord(embed)
                        time.sleep(2)  # Rate limit: wait 2s between posts
                    
                    if new_tweets:
                        self.save_seen_tweets()
                        print(f"📊 Processed {len(new_tweets)} new tweet(s)")
                    else:
                        print(f"⏳ No new tweets (checked at {datetime.now().strftime('%H:%M:%S')})")
                
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
            
            # Wait before next check
            print(f"💤 Sleeping for {self.check_interval} seconds...")
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
    
    # Create and run bot
    bot = TwitterToDiscord(
        discord_webhook_url=DISCORD_WEBHOOK_URL,
        check_interval=300  # Check every 5 minutes
    )
    bot.run()

if __name__ == "__main__":
    main()
