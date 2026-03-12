"""
Telegram Bot Module for Coding Bear
Handles Telegram interactions for code review and assistance
"""

import logging
import tempfile
import os
from typing import Optional
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from coding_agent import CodingBearAgent
from config import get_config

logger = logging.getLogger(__name__)


class CodingBearTelegramBot:
    """Telegram bot for Coding Bear agent"""
    
    def __init__(self, agent: CodingBearAgent = None):
        self.config = get_config()
        self.agent = agent or CodingBearAgent()
        self.application: Optional[Application] = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_text = f"""🐻 **{self.config.agent.name}** is ready to help!

I can assist you with:
• 🔍 Code review
• 🐛 Debugging
• ♻️ Refactoring  
• 🧪 Test generation
• 📚 Documentation

**Commands:**
/review - Review code file
/debug - Debug an error
/refactor - Refactor code
/test - Generate tests
/explain - Explain code
/help - Show help

Send me code directly or upload files!"""
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """🐻 **Coding Bear Commands**

**Code Review**
• Send a code file → Automatic review
• /review \<code\> - Review inline code

**Debugging**
• /debug \<error message\> - Debug an error
• Reply to error with /debug

**Refactoring**
• /refactor \<code\> - Get refactored code
• Send file with /refactor caption

**Testing**
• /test \<code\> - Generate unit tests
• Send file with /test caption

**Explanation**
• /explain \<code\> - Explain how code works
• Reply to code with /explain

**General**
• Just ask any coding question!
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def review_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /review command"""
        if not context.args and not update.message.reply_to_message:
            await update.message.reply_text(
                "Please provide code to review:\n`/review \<your code\>`",
                parse_mode='Markdown'
            )
            return
        
        # Get code from args or replied message
        if update.message.reply_to_message:
            code = update.message.reply_to_message.text
        else:
            code = ' '.join(context.args)
        
        await update.message.reply_text("🔍 Analyzing code...")
        
        try:
            review = self.agent.review_code("inline.py", code)
            # Split long messages
            if len(review) > 4000:
                for i in range(0, len(review), 4000):
                    await update.message.reply_text(review[i:i+4000])
            else:
                await update.message.reply_text(review)
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def debug_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /debug command"""
        if not context.args and not update.message.reply_to_message:
            await update.message.reply_text(
                "Please provide error message:\n`/debug \<error\>`",
                parse_mode='Markdown'
            )
            return
        
        if update.message.reply_to_message:
            error = update.message.reply_to_message.text
        else:
            error = ' '.join(context.args)
        
        await update.message.reply_text("🐛 Debugging...")
        
        try:
            debug_result = self.agent.debug_error(error)
            await update.message.reply_text(debug_result)
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def refactor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /refactor command"""
        if not context.args and not update.message.reply_to_message:
            await update.message.reply_text(
                "Please provide code to refactor:\n`/refactor \<code\>`",
                parse_mode='Markdown'
            )
            return
        
        if update.message.reply_to_message:
            code = update.message.reply_to_message.text
        else:
            code = ' '.join(context.args)
        
        await update.message.reply_text("♻️ Refactoring...")
        
        try:
            refactored = self.agent.refactor_code("inline.py", code)
            await update.message.reply_text(f"```\n{refactored[:4000]}\n```", parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /test command"""
        if not context.args and not update.message.reply_to_message:
            await update.message.reply_text(
                "Please provide code to test:\n`/test \<code\>`",
                parse_mode='Markdown'
            )
            return
        
        if update.message.reply_to_message:
            code = update.message.reply_to_message.text
        else:
            code = ' '.join(context.args)
        
        await update.message.reply_text("🧪 Generating tests...")
        
        try:
            tests = self.agent.generate_tests("inline.py", code)
            await update.message.reply_text(f"```\n{tests[:4000]}\n```", parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def explain_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /explain command"""
        if not context.args and not update.message.reply_to_message:
            await update.message.reply_text(
                "Please provide code to explain:\n`/explain \<code\>`",
                parse_mode='Markdown'
            )
            return
        
        if update.message.reply_to_message:
            code = update.message.reply_to_message.text
        else:
            code = ' '.join(context.args)
        
        await update.message.reply_text("📚 Analyzing...")
        
        try:
            explanation = self.agent.explain_code(code)
            await update.message.reply_text(explanation)
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle uploaded code files"""
        document = update.message.document
        
        # Check file size
        if document.file_size > self.config.agent.max_file_size:
            await update.message.reply_text("❌ File too large (max 100KB)")
            return
        
        # Download file
        await update.message.reply_text(f"📥 Downloading {document.file_name}...")
        
        try:
            file = await context.bot.get_file(document.file_id)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix=Path(document.file_name).suffix, delete=False) as tmp:
                await file.download_to_drive(tmp.name)
                tmp_path = tmp.name
            
            # Read file
            with open(tmp_path, 'r') as f:
                code = f.read()
            
            os.unlink(tmp_path)
            
            # Check caption for command
            caption = update.message.caption or ""
            
            if "/review" in caption.lower() or not caption:
                await update.message.reply_text("🔍 Reviewing code...")
                review = self.agent.review_code(document.file_name, code)
                
                # Send in chunks if needed
                for i in range(0, len(review), 4000):
                    await update.message.reply_text(review[i:i+4000])
                    
            elif "/refactor" in caption.lower():
                await update.message.reply_text("♻️ Refactoring...")
                refactored = self.agent.refactor_code(document.file_name, code)
                
                # Send as document if too long
                if len(refactored) > 4000:
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
                        tmp.write(refactored)
                        tmp_path = tmp.name
                    
                    await update.message.reply_document(
                        document=open(tmp_path, 'rb'),
                        filename=f"refactored_{document.file_name}"
                    )
                    os.unlink(tmp_path)
                else:
                    await update.message.reply_text(f"```\n{refactored}\n```", parse_mode='Markdown')
                    
            elif "/test" in caption.lower():
                await update.message.reply_text("🧪 Generating tests...")
                tests = self.agent.generate_tests(document.file_name, code)
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='_test.py', delete=False) as tmp:
                    tmp.write(tests)
                    tmp_path = tmp.name
                
                await update.message.reply_document(
                    document=open(tmp_path, 'rb'),
                    filename=f"test_{document.file_name}"
                )
                os.unlink(tmp_path)
                
        except Exception as e:
            await update.message.reply_text(f"❌ Error processing file: {str(e)}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        if not update.message or not update.message.text:
            return
        
        text = update.message.text
        
        # Check if it's a command
        if text.startswith('/'):
            return
        
        # Treat as general coding question
        await update.message.reply_text("💭 Thinking...")
        
        try:
            response = self.agent._call_llm(
                "You are a helpful coding assistant. Answer concisely and clearly.",
                text
            )
            await update.message.reply_text(response)
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    def setup_handlers(self):
        """Setup bot handlers"""
        self.application = Application.builder().token(self.config.telegram.bot_token).build()
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("review", self.review_command))
        self.application.add_handler(CommandHandler("debug", self.debug_command))
        self.application.add_handler(CommandHandler("refactor", self.refactor_command))
        self.application.add_handler(CommandHandler("test", self.test_command))
        self.application.add_handler(CommandHandler("explain", self.explain_command))
        
        # Document handler
        self.application.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        
        # Text handler
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    def run(self):
        """Run the bot"""
        if not self.config.telegram.bot_token:
            logger.error("Telegram bot token not configured")
            return
        
        self.setup_handlers()
        logger.info("Starting Coding Bear Telegram bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Main entry point"""
    bot = CodingBearTelegramBot()
    bot.run()


if __name__ == '__main__':
    main()