"""
Telegram Bot Interface for Crypto Agent
Handles user commands and agent responses
"""

import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv

from config import Config
from memory import Memory
from crypto_agent import CryptoAgent

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot for crypto agent"""
    
    def __init__(self, config_file="bond_config.yaml"):
        """
        Initialize bot
        
        Args:
            config_file: Path to config file
        """
        # Load configuration
        self.config = Config(config_file)
        
        # Initialize memory
        self.memory = Memory()
        
        # Initialize crypto agent
        try:
            self.agent = CryptoAgent(self.config, self.memory)
            logger.info("Crypto Agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Crypto Agent: {e}")
            raise
        
        # Get bot token
        self.bot_token = self.config.get("messaging.bot_token")
        if not self.bot_token:
            raise ValueError("Telegram bot token not configured")
        
        logger.info("Telegram Bot initialized")
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        
        logger.info(f"User {user_id} ({user_name}) started bot")
        
        message = f"""
👋 Welcome to {self.agent.agent_name}!

I'm your crypto analysis assistant. I scan Binance for market opportunities and provide actionable insights.

Available commands:
/opportunities - Find current trading opportunities
/analyze <pair> - Deep dive into a specific pair (e.g., /analyze BTCUSDT)
/status - Check my status
/help - Show this message

Just send a message like "What's happening with Bitcoin?" and I'll analyze it for you.

Stay safe and never risk more than you can afford to lose! 🚀
"""
        
        await update.message.reply_text(message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🤖 **Crypto Agent Help**

**Commands:**
/opportunities - Find trading opportunities on Binance
/analyze <pair> - Analyze specific pair (e.g., /analyze ETHUSDT)
/status - Show agent status
/help - Show this message

**How to use:**
1. Use /opportunities to find what's happening in the market
2. Use /analyze to deep-dive into specific pairs
3. Send natural language: "What about SOL?", "Find high volatility pairs"

**⚠️ Disclaimers:**
- This is educational analysis only
- Not financial advice
- Always DYOR (Do Your Own Research)
- Never risk more than you can afford to lose
"""
        
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def opportunities(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /opportunities command"""
        user_id = update.effective_user.id
        
        await update.message.reply_text("🔍 Scanning Binance for opportunities... Please wait.")
        
        try:
            result = self.agent.find_opportunities()
            
            if result['status'] == 'error':
                await update.message.reply_text(f"❌ Error: {result['message']}")
                return
            
            if result['status'] == 'no_opportunities':
                await update.message.reply_text("📊 No opportunities detected at this time. Market is stable.")
                return
            
            # Format opportunities
            opp_text = f"📈 **Found {result['opportunities_count']} opportunities:**\n\n"
            
            for i, opp in enumerate(result['opportunities'][:5], 1):
                confidence_emoji = "🟢" if opp['confidence'] > 0.7 else "🟡" if opp['confidence'] > 0.4 else "🔴"
                
                opp_text += f"{i}. **{opp['pair']}** {confidence_emoji}\n"
                opp_text += f"   Type: {opp['type']}\n"
                opp_text += f"   {opp['description']}\n"
                opp_text += f"   Confidence: {opp['confidence']*100:.0f}%\n\n"
            
            await update.message.reply_text(opp_text, parse_mode="Markdown")
            
            # Send analysis
            await update.message.reply_text(f"📋 **Analysis:**\n\n{result['analysis']}", parse_mode="Markdown")
            
            # Save to memory
            self.memory.save_conversation(
                user_input="/opportunities",
                agent_response=result['analysis']
            )
            
        except Exception as e:
            logger.error(f"Error in opportunities: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analyze <pair> command"""
        
        if not context.args:
            await update.message.reply_text("Usage: /analyze <pair>\nExample: /analyze BTCUSDT")
            return
        
        pair = context.args[0].upper()
        
        # Validate pair format
        if not pair.endswith("USDT"):
            pair = pair + "USDT"
        
        await update.message.reply_text(f"🔎 Analyzing {pair}... Please wait.")
        
        try:
            result = self.agent.analyze_pair(pair)
            
            if result['status'] == 'error':
                await update.message.reply_text(f"❌ Error: {result['message']}")
                return
            
            # Format current data
            data = result['current_data']
            price_text = f"""
📊 **{pair} - Current Data:**

Price: ${data['price']:.2f}
24h Change: {data['price_change_percent_24h']:+.2f}%
24h High: ${data['high_24h']:.2f}
24h Low: ${data['low_24h']:.2f}
24h Volume: ${data['quote_asset_volume']:.0f}
Bid/Ask: ${data['bid']:.2f} / ${data['ask']:.2f}
"""
            
            await update.message.reply_text(price_text, parse_mode="Markdown")
            
            # Send analysis
            await update.message.reply_text(f"📈 **Analysis:**\n\n{result['analysis']}", parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in analyze_command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            status = self.agent.get_status()
            
            status_text = f"""
✅ **Agent Status**

Agent: {status['agent_name']}
User: {status['user_name']}
Exchange: {status['exchange']}
Pairs Analyzed: {status['top_pairs']}
Model: {status['model']}
Status: {status['status']}
"""
            
            await update.message.reply_text(status_text, parse_mode="Markdown")
        
        except Exception as e:
            logger.error(f"Error in status: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle free-form messages"""
        user_message = update.message.text
        user_id = update.effective_user.id
        
        logger.info(f"User {user_id}: {user_message}")
        
        # If it looks like a pair name, analyze it
        if any(stablecoin in user_message.upper() for stablecoin in ["USDT", "USDC", "BUSD"]):
            pair = None
            for token in ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "LINK", "MATIC", "AVAX", "ARB", "BNB", "LTC", "SUI", "OP", "APT"]:
                if token in user_message.upper():
                    pair = token + "USDT"
                    break
            
            if pair:
                await self.analyze_command(update, context)
                context.args = [pair]
                return
        
        # Otherwise, treat as general inquiry - show opportunities
        await update.message.reply_text("Let me find relevant market opportunities for you...")
        await self.opportunities(update, context)
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
    
    def run(self):
        """Run the bot"""
        # Create application
        app = Application.builder().token(self.bot_token).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("opportunities", self.opportunities))
        app.add_handler(CommandHandler("analyze", self.analyze_command))
        app.add_handler(CommandHandler("status", self.status))
        
        # Handle all other messages
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Error handler
        app.add_error_handler(self.error_handler)
        
        logger.info("Starting Telegram bot...")
        print("🤖 Crypto Agent Bot is running! Send /help for commands.")
        
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    try:
        bot = TelegramBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
