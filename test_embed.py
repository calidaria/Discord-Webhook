#!/usr/bin/env python3
"""
Test Script v2 - Sends a sample embed to Discord
Creates a mock tweet embed so you can see the format even if APIs are down
"""

import requests
import os
from datetime import datetime

def send_sample_embed():
    """Send a sample embed to show the format"""
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL', '')
    
    if not webhook_url:
        print("❌ Error: DISCORD_WEBHOOK_URL environment variable not set")
        return
    
    print("🧪 TEST EMBED SCRIPT v2")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    # Create a sample embed showing what the real ones will look like
    sample_embed = {
        "title": "New post from @SoJ_Global",
        "description": "Blossom Pandapuff Surprise Box – Arriving February 19th! 🐼🌸\n\nUse Ornate Jade (Bound) to unlock this special surprise box—each open brings a chance to discover the enchanting [Mount: Blossom Pandapuff], exquisite accessories, or the utterly adorable [Hat: National Treasure]!\n\nA bundle of whimsy and fortune awaits. Will you be the lucky one?\n\n#SwordOfJustice #SOJ",
        "url": "https://twitter.com/SoJ_Global/status/1234567890",
        "color": 1942002,  # Twitter blue
        "author": {
            "name": "Sword of Justice (@SoJ_Global)",
            "url": "https://twitter.com/SoJ_Global",
            "icon_url": "https://abs.twimg.com/icons/apple-touch-icon-192x192.png"
        },
        "footer": {
            "text": "Twitter/X • This is a SAMPLE embed showing format",
            "icon_url": "https://abs.twimg.com/icons/apple-touch-icon-192x192.png"
        },
        "timestamp": datetime.now().isoformat(),
        "image": {
            "url": "https://pbs.twimg.com/media/GgXxXxXXxXxXxXx?format=jpg&name=large"
        }
    }
    
    print("📊 Sample Embed Details:")
    print("  Title: New post from @SoJ_Global")
    print("  Author: Sword of Justice (@SoJ_Global)")
    print("  Color: Twitter blue (#1DA1F2)")
    print("  Includes: Author icon, footer, timestamp, clickable link")
    print("  Image: Placeholder (real tweets will show actual images)")
    print()
    
    print("📤 Sending sample embed to Discord...\n")
    
    payload = {
        "content": "**🧪 TEST EMBED** - This is how tweets from @SoJ_Global will appear:",
        "embeds": [sample_embed]
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        
        print("✅ SUCCESS! Sample embed sent to Discord!")
        print("\n📋 What you should see in Discord:")
        print("  ✓ Message saying 'TEST EMBED'")
        print("  ✓ Blue embed with Twitter branding")
        print("  ✓ Author name with Twitter icon")
        print("  ✓ Tweet text")
        print("  ✓ Clickable link to Twitter")
        print("  ✓ Timestamp at bottom")
        print("  ✓ (Real tweets will include actual images)")
        print("\n🎨 This is the exact format your bot will use!")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
    except Exception as e:
        print(f"❌ Error sending to Discord: {e}")

if __name__ == "__main__":
    send_sample_embed()
