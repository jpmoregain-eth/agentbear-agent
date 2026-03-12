"""
Crypto Agent Orchestrator - CEX Analysis + Claude Integration
Week 1 MVP: Binance only
"""

import logging
from anthropic import Anthropic
from binance_analyzer import BinanceAnalyzer
from memory import Memory

logger = logging.getLogger(__name__)


class CryptoAgent:
    """Main agent for analyzing crypto opportunities"""
    
    # Top 20 pairs to analyze
    TOP_PAIRS = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
        "DOGEUSDT", "LINKUSDT", "MATICUSDT", "AVAXUSDT", "ARBUSDT",
        "BNBUSDT", "USDCUSDT", "LTCUSDT", "SUIUSDT", "OPUSDT",
        "APTUSDT", "DYDXUSDT", "TRXUSDT", "NEARUSDT", "ATOMUSDT"
    ]
    
    def __init__(self, config, memory):
        """
        Initialize crypto agent
        
        Args:
            config: Config manager
            memory: Memory system
        """
        self.config = config
        self.memory = memory
        
        # Initialize Anthropic client
        api_key = config.get("model_keys.claude_api_key")
        if not api_key:
            raise ValueError("Claude API key not configured")
        
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
        
        # Initialize Binance analyzer
        binance_config = config.get("exchanges.cex.binance", {})
        self.binance = BinanceAnalyzer(
            api_key=binance_config.get("api_key"),
            api_secret=binance_config.get("api_secret"),
            testnet=binance_config.get("testnet", False)
        )
        
        # Load user info
        self.user_name = memory.get_preference("user_name", "Trader")
        self.agent_name = memory.get_preference("agent_name", "Sentinel")
        
        logger.info(f"Agent {self.agent_name} initialized for {self.user_name}")
    
    def find_opportunities(self, language="en"):
        """
        Main function: Find trading opportunities on Binance
        
        Args:
            language: Response language (en, zh, es, ja, ko)
        
        Returns:
            Dict with opportunities and analysis
        """
        try:
            logger.info("Fetching prices for top 20 pairs...")
            
            # 1. Fetch prices
            prices_data = self.binance.fetch_prices(self.TOP_PAIRS)
            
            # Count successes
            success_count = sum(1 for p in prices_data.values() if "error" not in p)
            logger.info(f"Successfully fetched {success_count}/{len(self.TOP_PAIRS)} pairs")
            
            # 2. Detect opportunities
            opportunities = self.binance.detect_opportunities(prices_data)
            
            if not opportunities:
                return {
                    "status": "no_opportunities",
                    "message": "No opportunities detected at this time. Market conditions are stable."
                }
            
            # 3. Ask Claude to analyze
            analysis = self._analyze_with_claude(opportunities)
            
            # 4. Save to memory
            for opp in opportunities:
                self.memory.save_opportunity({
                    "pair": opp['pair'],
                    "type": opp['type'],
                    "metric": opp['metric'],
                    "price": opp.get('price'),
                    "confidence": opp['confidence']
                })
            
            logger.info(f"Found {len(opportunities)} opportunities")
            
            return {
                "status": "success",
                "opportunities_count": len(opportunities),
                "opportunities": opportunities,
                "analysis": analysis
            }
        
        except Exception as e:
            logger.error(f"Error in find_opportunities: {e}")
            return {
                "status": "error",
                "message": f"Error analyzing opportunities: {str(e)}"
            }
    
    def analyze_pair(self, pair, interval="1h", limit=24):
        """
        Deep dive analysis of a specific pair
        
        Args:
            pair: Trading pair (e.g., "BTCUSDT")
            interval: Candle interval
            limit: Number of candles
        
        Returns:
            Detailed analysis
        """
        try:
            # Fetch current data
            price_data = self.binance.fetch_prices([pair])
            
            if pair not in price_data or "error" in price_data[pair]:
                return {
                    "status": "error",
                    "message": f"Could not fetch data for {pair}"
                }
            
            # Get historical data
            klines = self.binance.get_klines(pair, interval=interval, limit=limit)
            
            if "error" in klines:
                klines = []
            
            # Ask Claude for analysis
            analysis = self._analyze_pair_with_claude(pair, price_data[pair], klines)
            
            # Save to memory
            self.memory.save_conversation(
                user_input=f"/analyze {pair}",
                agent_response=analysis
            )
            
            return {
                "status": "success",
                "pair": pair,
                "current_data": price_data[pair],
                "analysis": analysis
            }
        
        except Exception as e:
            logger.error(f"Error analyzing pair {pair}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _analyze_with_claude(self, opportunities):
        """
        Use Claude to analyze opportunities and format response
        
        Args:
            opportunities: List of opportunities from detect_opportunities
        
        Returns:
            Formatted analysis string
        """
        try:
            # Format opportunities for Claude
            opp_text = "\n".join([
                f"**{i+1}. {opp['pair']}** - {opp['type'].upper()}\n"
                f"   Description: {opp['description']}\n"
                f"   Price: ${opp.get('price', 'N/A'):.2f}\n"
                f"   24h Volume: ${opp.get('volume_24h', 0):.0f}\n"
                f"   Confidence: {opp['confidence']*100:.0f}%"
                for i, opp in enumerate(opportunities[:5])
            ])
            
            prompt = f"""You are {self.agent_name}, a professional crypto analyst for {self.user_name}.

Analyze these market opportunities I detected on Binance:

{opp_text}

For each opportunity:
1. Explain why this is interesting
2. What drives this opportunity (volatility, spread, etc.)
3. Risk factors to consider
4. Brief action suggestion

Keep it professional, concise, and actionable. No guarantees - this is educational analysis only."""
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
        
        except Exception as e:
            logger.error(f"Error in Claude analysis: {e}")
            return f"Error: Could not analyze opportunities. {str(e)}"
    
    def _analyze_pair_with_claude(self, pair, price_data, klines):
        """
        Detailed analysis of a single pair
        
        Args:
            pair: Trading pair
            price_data: Current price data
            klines: Historical klines
        
        Returns:
            Detailed analysis
        """
        try:
            # Format price data
            price_info = f"""
Current Price: ${price_data['price']:.2f}
24h Change: {price_data['price_change_percent_24h']:.2f}%
24h High: ${price_data['high_24h']:.2f}
24h Low: ${price_data['low_24h']:.2f}
24h Volume: ${price_data['quote_asset_volume']:.0f}
Bid/Ask: ${price_data['bid']:.2f} / ${price_data['ask']:.2f}
Spread: {((price_data['ask'] - price_data['bid']) / price_data['price'] * 100):.3f}%
"""
            
            # Format recent candles
            recent_candles = ""
            if klines and "error" not in klines:
                recent_candles = "\nRecent price action (last 24 hours):\n"
                for k in klines[-5:]:  # Last 5 candles
                    recent_candles += f"  Open: ${k['open']:.2f}, High: ${k['high']:.2f}, Low: ${k['low']:.2f}, Close: ${k['close']:.2f}\n"
            
            prompt = f"""You are {self.agent_name}, analyzing {pair} for {self.user_name}.

{price_info}
{recent_candles}

Provide a brief technical and fundamental analysis:
1. Current price action (trending, consolidating, etc.)
2. Support/resistance levels
3. Volume analysis
4. Risk/reward considerations
5. Short-term outlook

Keep it concise and actionable."""
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
        
        except Exception as e:
            logger.error(f"Error in pair analysis: {e}")
            return f"Error: Could not analyze pair. {str(e)}"
    
    def get_status(self):
        """Get agent status"""
        return {
            "agent_name": self.agent_name,
            "user_name": self.user_name,
            "exchange": "binance",
            "top_pairs": len(self.TOP_PAIRS),
            "model": self.model,
            "status": "operational"
        }
