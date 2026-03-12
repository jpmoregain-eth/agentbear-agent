"""
Binance Market Data Analyzer
Uses official binance-connector-python for real-time market data
"""

import time
import logging
from binance.spot import Spot
from binance.error import ClientError

logger = logging.getLogger(__name__)


class BinanceAnalyzer:
    """Fetch and analyze Binance market data"""
    
    def __init__(self, api_key=None, api_secret=None, testnet=False):
        """
        Initialize Binance analyzer
        
        Args:
            api_key: Binance API key (can be None for public data)
            api_secret: Binance API secret (can be None for public data)
            testnet: Use testnet instead of mainnet
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        # Initialize Spot client
        try:
            self.client = Spot(
                api_key=api_key or "",
                api_secret=api_secret or "",
                base_url="https://testnet.binance.vision" if testnet else "https://api.binance.com"
            )
            logger.info(f"Binance Analyzer initialized (testnet={testnet})")
        except Exception as e:
            logger.error(f"Failed to initialize Binance client: {e}")
            self.client = None
    
    def fetch_prices(self, pairs):
        """
        Fetch current prices for multiple pairs
        
        Args:
            pairs: List of pairs like ["BTCUSDT", "ETHUSDT", ...]
        
        Returns:
            Dict of {pair: {price, bid, ask, timestamp, volume_24h}}
        """
        if not self.client:
            return {pair: {"error": "Client not initialized"} for pair in pairs}
        
        results = {}
        
        for pair in pairs:
            try:
                # Get ticker (price + 24h data)
                ticker = self.client.ticker_price(symbol=pair)
                stats_24h = self.client.ticker_24hr(symbol=pair)
                
                # Get order book depth (top 5)
                depth = self.client.depth(symbol=pair, limit=5)
                
                results[pair] = {
                    "exchange": "binance",
                    "price": float(ticker.get('price', 0)),
                    "bid": float(depth['bids'][0][0]) if depth.get('bids') else None,
                    "ask": float(depth['asks'][0][0]) if depth.get('asks') else None,
                    "bid_quantity": float(depth['bids'][0][1]) if depth.get('bids') else None,
                    "ask_quantity": float(depth['asks'][0][1]) if depth.get('asks') else None,
                    "volume_24h": float(stats_24h.get('volume', 0)),
                    "quote_asset_volume": float(stats_24h.get('quoteAssetVolume', 0)),
                    "high_24h": float(stats_24h.get('high', 0)),
                    "low_24h": float(stats_24h.get('low', 0)),
                    "price_change_24h": float(stats_24h.get('priceChange', 0)),
                    "price_change_percent_24h": float(stats_24h.get('priceChangePercent', 0)),
                    "timestamp": time.time()
                }
                logger.debug(f"{pair}: ${results[pair]['price']}")
                
            except ClientError as e:
                logger.warning(f"Error fetching {pair}: {e}")
                results[pair] = {"error": str(e)}
            except Exception as e:
                logger.error(f"Unexpected error for {pair}: {e}")
                results[pair] = {"error": str(e)}
        
        return results
    
    def get_order_book(self, symbol, limit=20):
        """
        Get detailed order book for a symbol
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            limit: Order book depth (1, 5, 10, 20, 50, 100, 500, 1000)
        
        Returns:
            Order book with bids and asks
        """
        if not self.client:
            return {"error": "Client not initialized"}
        
        try:
            return self.client.depth(symbol=symbol, limit=limit)
        except ClientError as e:
            logger.error(f"Error fetching order book for {symbol}: {e}")
            return {"error": str(e)}
    
    def get_klines(self, symbol, interval="1h", limit=24):
        """
        Get candlestick data
        
        Args:
            symbol: Trading pair
            interval: Time interval (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            limit: Number of candles
        
        Returns:
            List of candlesticks with OHLCV data
        """
        if not self.client:
            return {"error": "Client not initialized"}
        
        try:
            klines = self.client.klines(symbol=symbol, interval=interval, limit=limit)
            
            # Format klines
            formatted = []
            for k in klines:
                formatted.append({
                    "open_time": k[0],
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "quote_asset_volume": float(k[7]),
                    "trades": int(k[8])
                })
            
            return formatted
        
        except ClientError as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            return {"error": str(e)}
    
    def detect_opportunities(self, pairs_data):
        """
        Analyze price data for opportunities
        
        Current logic: Find high volatility and unusual volume
        
        Args:
            pairs_data: Dict from fetch_prices()
        
        Returns:
            List of opportunities with scores
        """
        opportunities = []
        
        for pair, data in pairs_data.items():
            if "error" in data:
                continue
            
            # Skip low volume pairs (<$10M 24h)
            if data['quote_asset_volume'] < 10_000_000:
                continue
            
            # Opportunity 1: High volatility (>3% change in 24h)
            price_change_pct = abs(data['price_change_percent_24h'])
            if price_change_pct > 3.0:
                opportunities.append({
                    "pair": pair,
                    "type": "volatility",
                    "metric": price_change_pct,
                    "description": f"High volatility: {price_change_pct:.2f}% 24h change",
                    "price": data['price'],
                    "volume_24h": data['quote_asset_volume'],
                    "confidence": min(price_change_pct / 10.0, 1.0)  # Normalize to 0-1
                })
            
            # Opportunity 2: Wide bid-ask spread (>0.1% on high-volume pairs)
            if data['bid'] and data['ask']:
                spread_pct = ((data['ask'] - data['bid']) / data['price']) * 100
                if spread_pct > 0.15 and data['quote_asset_volume'] > 100_000_000:  # Only on major pairs
                    opportunities.append({
                        "pair": pair,
                        "type": "spread",
                        "metric": spread_pct,
                        "description": f"Wide spread opportunity: {spread_pct:.3f}%",
                        "price": data['price'],
                        "bid": data['bid'],
                        "ask": data['ask'],
                        "volume_24h": data['quote_asset_volume'],
                        "confidence": min(spread_pct / 0.5, 1.0)
                    })
        
        # Sort by confidence
        opportunities.sort(key=lambda x: x['confidence'], reverse=True)
        
        return opportunities[:10]  # Top 10 opportunities
    
    def get_symbol_info(self, symbol):
        """
        Get symbol trading info (filters, min order, etc.)
        
        Args:
            symbol: Trading pair
        
        Returns:
            Symbol info
        """
        if not self.client:
            return {"error": "Client not initialized"}
        
        try:
            info = self.client.exchange_info(symbol=symbol)
            return info
        except ClientError as e:
            logger.error(f"Error fetching symbol info for {symbol}: {e}")
            return {"error": str(e)}
