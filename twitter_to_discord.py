#!/usr/bin/env python3
"""
Twitter/X to Discord Webhook Bot
Monitors @SoJ_Global and posts new tweets to Discord via webhook
"""

import requests
import time
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

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
            with open(self.seen_tweets_file, 'r') as f:
                return set(json.load(f))
        return set()
    
    def save_seen_tweets(self):
        """Save seen tweet IDs to file"""
        with open(self.seen_tweets_file, 'w') as f:
            json.dump(list(self.seen_tweets), f)
    
    def fetch_tweets(self, username: str = "SoJ_Global") -> List[Dict]:
        """
        Fetch recent tweets from the user
        Note: This uses Twitter's syndication API (public, no auth required)
        """
        # Using Twitter's syndication endpoint (publicly accessible)
        url = f"https://cdn.syndication.twimg.com/timeline/profile?screen_name={username}&limit=20"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('timeline', [])
        except Exception as e:
            print(f"Error fetching tweets: {e}")
            return []
    
    def create_discord_embed(self, tweet: Dict) -> Dict:
        """Create a Discord embed from tweet data"""
        tweet_id = tweet.get('tweet_id')
        username = tweet.get('user', {}).get('screen_name', 'SoJ_Global')
        user_display_name = tweet.get('user', {}).get('name', 'Sword of Justice')
        text = tweet.get('text', '')
        created_at = tweet.get('created_at')
        
        # Parse timestamp
        timestamp = None
        if created_at:
            try:
                # Twitter timestamp format
                dt = datetime.strptime(created_at, '%a %b %d %H:%M:%S %z %Y')
                timestamp = dt.isoformat()
            except:
                pass
        
        # Build tweet URL
        tweet_url = f"https://twitter.com/{username}/status/{tweet_id}"
        
        # Create embed
        embed = {
            "title": f"New post from @{username}",
            "description": text,
            "url": tweet_url,
            "color": 1942002,  # Twitter blue color
            "author": {
                "name": f"{user_display_name} (@{username})",
                "url": f"https://twitter.com/{username}",
                "icon_url": tweet.get('user', {}).get('profile_image_url_https', '')
            },
            "footer": {
                "text": "Twitter",
                "icon_url": "https://abs.twimg.com/icons/apple-touch-icon-192x192.png"
            }
        }
        
        if timestamp:
            embed["timestamp"] = timestamp
        
        # Add media if present
        media = tweet.get('media', [])
        if media and len(media) > 0:
            first_media = media[0]
            if first_media.get('type') == 'photo':
                embed["image"] = {"url": first_media.get('media_url_https')}
        
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
        print(f"🤖 Starting Twitter to Discord bot...")
        print(f"📡 Monitoring: @SoJ_Global")
        print(f"🔄 Check interval: {self.check_interval} seconds")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        while True:
            try:
                tweets = self.fetch_tweets()
                
                # Process tweets in reverse order (oldest first)
                new_tweets = []
                for tweet in reversed(tweets):
                    tweet_id = tweet.get('tweet_id')
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
