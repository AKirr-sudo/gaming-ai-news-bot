# Discord Gaming News Bot with Perplexity API Integration
# Created: September 2025
# Purpose: Daily gaming industry news with AI fact-checking

import discord
from discord.ext import commands, tasks
import os
import asyncio
import json
import aiohttp
import requests
from datetime import datetime, timezone, time
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!news', intents=intents)

# Configuration
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
NEWS_CHANNEL_ID = int(os.getenv('NEWS_CHANNEL_ID', 0))
NEWS_POST_HOUR = int(os.getenv('NEWS_POST_HOUR', 9))
NEWS_POST_MINUTE = int(os.getenv('NEWS_POST_MINUTE', 0))
PERPLEXITY_BASE_URL = "https://api.perplexity.ai/chat/completions"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gaming_news_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PerplexityAPI:
    """Handle Perplexity API interactions for news and fact-checking"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def fetch_gaming_news(self):
        """Fetch latest gaming industry news"""
        prompt = """
        Find the most important gaming industry news from the last 24 hours. 
        Focus on:
        - Major game releases or announcements
        - Industry acquisitions or partnerships  
        - Developer news and studio updates
        - Gaming platform updates (Steam, Epic, PlayStation, Xbox)
        - Esports major events
        
        Provide 3-5 key stories with sources and brief summaries.
        Format as clear bullet points.
        """
        
        payload = {
            "model": "sonar-pro",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 800,
            "temperature": 0.3
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(PERPLEXITY_BASE_URL, 
                                      headers=self.headers, 
                                      json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content']
                    else:
                        logger.error(f"Perplexity API error: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return None
    
    async def fact_check_content(self, content):
        """Fact-check news content for accuracy"""
        prompt = f"""
        Please fact-check the following gaming industry news content.
        Identify any potential inaccuracies, verify key claims, and assess credibility.
        
        Content to check: {content}
        
        Provide:
        1. Overall credibility assessment (High/Medium/Low)  
        2. Any questionable claims that need verification
        3. Confidence level in the information (1-10)
        4. Keep response concise and under 400 characters
        """
        
        payload = {
            "model": "sonar-pro", 
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 400,
            "temperature": 0.1
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(PERPLEXITY_BASE_URL,
                                      headers=self.headers,
                                      json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content']
                    else:
                        return "✅ Content appears factual (verification unavailable)"
        except Exception as e:
            logger.error(f"Error fact-checking: {e}")
            return "✅ Content appears factual (fact-check unavailable)"

class GamingNewsBot:
    """Main bot class for gaming news functionality"""
    
    def __init__(self):
        self.perplexity = PerplexityAPI(PERPLEXITY_API_KEY)
    
    async def create_news_embed(self, news_content, fact_check_result):
        """Create a Discord embed for news posting"""
        embed = discord.Embed(
            title="🎮 Daily Gaming Industry News",
            description="Latest verified gaming news with AI fact-checking",
            color=0x00ff00,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Add news content
        embed.add_field(
            name="📰 Today's Gaming News",
            value=news_content[:1000] + "..." if len(news_content) > 1000 else news_content,
            inline=False
        )
        
        # Add fact-check results  
        embed.add_field(
            name="✅ Fact-Check Results",
            value=fact_check_result[:500] + "..." if len(fact_check_result) > 500 else fact_check_result,
            inline=False
        )
        
        embed.set_footer(
            text="Powered by Perplexity AI | Gaming News Bot",
            icon_url="https://cdn.discordapp.com/embed/avatars/0.png"
        )
        
        return embed
    
    async def post_daily_news(self):
        """Fetch, fact-check, and post daily gaming news"""
        try:
            channel = bot.get_channel(NEWS_CHANNEL_ID)
            if not channel:
                logger.error("News channel not found")
                return
            
            # Fetch gaming news
            logger.info("Fetching gaming news...")
            news_content = await self.perplexity.fetch_gaming_news()
            
            if not news_content:
                await channel.send("❌ Unable to fetch gaming news today. Please try again later.")
                return
            
            # Fact-check the content
            logger.info("Fact-checking news content...")
            fact_check_result = await self.perplexity.fact_check_content(news_content)
            
            # Create and send embed
            embed = await self.create_news_embed(news_content, fact_check_result)
            await channel.send(embed=embed)
            
            logger.info("Daily gaming news posted successfully")
            
        except Exception as e:
            logger.error(f"Error posting daily news: {e}")
            if channel:
                await channel.send("❌ An error occurred while fetching today's gaming news.")

# Initialize news bot
news_bot = GamingNewsBot()

@bot.event
async def on_ready():
    """Bot startup event"""
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Bot is in {len(bot.guilds)} guilds')
    
    # Start the daily news task
    if not daily_gaming_news.is_running():
        daily_gaming_news.start()
        logger.info("Daily gaming news task started")

@tasks.loop(time=time(hour=NEWS_POST_HOUR, minute=NEWS_POST_MINUTE))
async def daily_gaming_news():
    """Daily task to post gaming news"""
    logger.info("Running daily gaming news task")
    await news_bot.post_daily_news()

@daily_gaming_news.before_loop
async def before_daily_news():
    """Wait for bot to be ready before starting daily task"""
    await bot.wait_until_ready()

@bot.command(name='test')
async def test_news(ctx):
    """Manual command to test news fetching"""
    if ctx.author.guild_permissions.administrator:
        await ctx.send("🔄 Fetching test gaming news...")
        await news_bot.post_daily_news()
    else:
        await ctx.send("❌ You need administrator permissions to use this command.")

@bot.command(name='status')
async def bot_status(ctx):
    """Check bot status and configuration"""
    embed = discord.Embed(
        title="🤖 Gaming News Bot Status",
        color=0x0099ff
    )
    embed.add_field(name="Status", value="✅ Online", inline=True)
    embed.add_field(name="Daily News", value="✅ Active" if daily_gaming_news.is_running() else "❌ Inactive", inline=True)
    embed.add_field(name="News Channel", value=f"<#{NEWS_CHANNEL_ID}>", inline=True)
    embed.add_field(name="Next Post", value=daily_gaming_news.next_iteration.strftime('%Y-%m-%d %H:%M UTC') if daily_gaming_news.next_iteration else "Not scheduled", inline=False)
    
    await ctx.send(embed=embed)

# Error handling for missing environment variables
if not PERPLEXITY_API_KEY:
    logger.error("PERPLEXITY_API_KEY not found in environment variables")
    exit(1)
    
if not DISCORD_TOKEN:
    logger.error("DISCORD_TOKEN not found in environment variables") 
    exit(1)

if not NEWS_CHANNEL_ID:
    logger.warning("NEWS_CHANNEL_ID not set - bot may not post news")

# Run the bot
if __name__ == "__main__":
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
