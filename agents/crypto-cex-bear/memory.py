"""
AgentBear Memory System
SQLite-based conversation and opportunity tracking
"""

import sqlite3
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class Memory:
    """SQLite-based memory system for crypto agent"""
    
    def __init__(self, db_path="agentbear_memory.db"):
        """Initialize memory system"""
        self.db_path = db_path
        self.init_db()
        logger.info(f"Memory initialized: {db_path}")
    
    def init_db(self):
        """Create database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_input TEXT,
                agent_response TEXT,
                language TEXT DEFAULT 'en'
            )
        ''')
        
        # Opportunities table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                pair TEXT,
                type TEXT,
                metric REAL,
                price REAL,
                confidence REAL,
                description TEXT
            )
        ''')
        
        # Preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_conversation(self, user_input, agent_response, language="en"):
        """Save conversation to memory"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO conversations (user_input, agent_response, language)
                VALUES (?, ?, ?)
            ''', (user_input, agent_response, language))
            
            conn.commit()
            conn.close()
            logger.debug(f"Saved conversation: {user_input[:50]}...")
        
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
    
    def save_opportunity(self, opportunity):
        """Save detected opportunity"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO opportunities 
                (pair, type, metric, price, confidence, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                opportunity.get('pair'),
                opportunity.get('type'),
                opportunity.get('metric'),
                opportunity.get('price'),
                opportunity.get('confidence'),
                opportunity.get('description', '')
            ))
            
            conn.commit()
            conn.close()
            logger.debug(f"Saved opportunity: {opportunity.get('pair')}")
        
        except Exception as e:
            logger.error(f"Error saving opportunity: {e}")
    
    def get_recent_conversations(self, limit=10, days=7):
        """Get recent conversations"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT user_input, agent_response, timestamp 
                FROM conversations 
                WHERE timestamp > ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (cutoff_date.isoformat(), limit))
            
            results = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'user_input': row[0],
                    'agent_response': row[1],
                    'timestamp': row[2]
                }
                for row in results
            ]
        
        except Exception as e:
            logger.error(f"Error retrieving conversations: {e}")
            return []
    
    def get_recent_opportunities(self, limit=10, days=7):
        """Get recent opportunities"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT pair, type, metric, price, confidence, timestamp 
                FROM opportunities 
                WHERE timestamp > ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (cutoff_date.isoformat(), limit))
            
            results = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'pair': row[0],
                    'type': row[1],
                    'metric': row[2],
                    'price': row[3],
                    'confidence': row[4],
                    'timestamp': row[5]
                }
                for row in results
            ]
        
        except Exception as e:
            logger.error(f"Error retrieving opportunities: {e}")
            return []
    
    def set_preference(self, key, value):
        """Set user preference"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO preferences (key, value)
                VALUES (?, ?)
            ''', (key, str(value)))
            
            conn.commit()
            conn.close()
            logger.debug(f"Set preference: {key}")
        
        except Exception as e:
            logger.error(f"Error setting preference: {e}")
    
    def get_preference(self, key, default=None):
        """Get user preference"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT value FROM preferences WHERE key = ?', (key,))
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else default
        
        except Exception as e:
            logger.error(f"Error getting preference: {e}")
            return default
    
    def cleanup_old_data(self, days=30):
        """Clean up old conversations and opportunities"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor.execute(
                'DELETE FROM conversations WHERE timestamp < ?',
                (cutoff_date.isoformat(),)
            )
            
            cutoff_opp = datetime.now() - timedelta(days=7)
            cursor.execute(
                'DELETE FROM opportunities WHERE timestamp < ?',
                (cutoff_opp.isoformat(),)
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"Cleaned up data older than {days} days")
        
        except Exception as e:
            logger.error(f"Error cleaning up data: {e}")
    
    def get_stats(self):
        """Get memory statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM conversations')
            conv_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM opportunities')
            opp_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM preferences')
            pref_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'conversations': conv_count,
                'opportunities': opp_count,
                'preferences': pref_count
            }
        
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
