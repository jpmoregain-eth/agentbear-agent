"""
Code Memory Module
Stores and retrieves code analysis history and patterns
"""

import json
import sqlite3
import hashlib
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class CodeMemory:
    """Manages persistent memory of code analyses"""
    
    def __init__(self, db_path: str = "coding_memory.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Code analyses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS code_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                analysis_json TEXT NOT NULL,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Patterns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS code_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                pattern_data TEXT NOT NULL,
                file_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Issues history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS issues_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                issue_type TEXT NOT NULL,
                issue_data TEXT NOT NULL,
                severity TEXT NOT NULL,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Code memory database initialized")
    
    def _get_file_hash(self, file_path: str) -> str:
        """Get hash of file contents"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""
    
    def store_analysis(self, file_path: str, analysis: Dict[str, Any]):
        """Store code analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        file_hash = self._get_file_hash(file_path)
        analysis_json = json.dumps(analysis)
        
        cursor.execute('''
            INSERT INTO code_analyses (file_path, file_hash, analysis_json)
            VALUES (?, ?, ?)
        ''', (file_path, file_hash, analysis_json))
        
        conn.commit()
        conn.close()
        
        # Store issues separately for tracking
        if 'issues' in analysis:
            for issue in analysis['issues']:
                self._store_issue(file_path, issue)
        
        logger.info(f"Stored analysis for {file_path}")
    
    def _store_issue(self, file_path: str, issue: Dict[str, Any]):
        """Store an issue"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO issues_history (file_path, issue_type, issue_data, severity)
            VALUES (?, ?, ?, ?)
        ''', (
            file_path,
            issue.get('rule', 'unknown'),
            json.dumps(issue),
            issue.get('severity', 'info')
        ))
        
        conn.commit()
        conn.close()
    
    def get_last_analysis(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get most recent analysis for a file"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT analysis_json FROM code_analyses
            WHERE file_path = ?
            ORDER BY analyzed_at DESC
            LIMIT 1
        ''', (file_path,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        return None
    
    def has_file_changed(self, file_path: str) -> bool:
        """Check if file has changed since last analysis"""
        current_hash = self._get_file_hash(file_path)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT file_hash FROM code_analyses
            WHERE file_path = ?
            ORDER BY analyzed_at DESC
            LIMIT 1
        ''', (file_path,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return True  # Never analyzed
        
        return row[0] != current_hash
    
    def get_common_issues(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most common issues across all files"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT issue_type, severity, COUNT(*) as count
            FROM issues_history
            WHERE resolved = FALSE
            GROUP BY issue_type, severity
            ORDER BY count DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'issue_type': row[0],
                'severity': row[1],
                'count': row[2]
            }
            for row in rows
        ]
    
    def get_project_health(self) -> Dict[str, Any]:
        """Get overall project health metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total files analyzed
        cursor.execute('SELECT COUNT(DISTINCT file_path) FROM code_analyses')
        total_files = cursor.fetchone()[0]
        
        # Total issues
        cursor.execute('SELECT COUNT(*) FROM issues_history WHERE resolved = FALSE')
        total_issues = cursor.fetchone()[0]
        
        # Issues by severity
        cursor.execute('''
            SELECT severity, COUNT(*) FROM issues_history
            WHERE resolved = FALSE
            GROUP BY severity
        ''')
        issues_by_severity = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Average complexity
        cursor.execute('''
            SELECT AVG(
                CAST(json_extract(analysis_json, '$.complexity_score') AS FLOAT)
            )
            FROM code_analyses
            WHERE analyzed_at = (
                SELECT MAX(analyzed_at) FROM code_analyses AS sub
                WHERE sub.file_path = code_analyses.file_path
            )
        ''')
        avg_complexity = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_files_analyzed': total_files,
            'total_open_issues': total_issues,
            'issues_by_severity': issues_by_severity,
            'average_complexity': round(avg_complexity, 2),
            'health_score': self._calculate_health_score(total_issues, total_files)
        }
    
    def _calculate_health_score(self, issues: int, files: int) -> int:
        """Calculate project health score (0-100)"""
        if files == 0:
            return 100
        
        issues_per_file = issues / files
        
        if issues_per_file < 1:
            return 90 + min(10, int(10 - issues_per_file * 10))
        elif issues_per_file < 3:
            return 70 + min(20, int(20 - (issues_per_file - 1) * 10))
        elif issues_per_file < 5:
            return 50 + min(20, int(20 - (issues_per_file - 3) * 10))
        else:
            return max(0, 50 - int((issues_per_file - 5) * 5))
    
    def store_pattern(self, pattern_type: str, pattern_data: Dict[str, Any], file_path: str = None):
        """Store a code pattern"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO code_patterns (pattern_type, pattern_data, file_path)
            VALUES (?, ?, ?)
        ''', (pattern_type, json.dumps(pattern_data), file_path))
        
        conn.commit()
        conn.close()
    
    def get_patterns(self, pattern_type: str = None) -> List[Dict[str, Any]]:
        """Get stored patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if pattern_type:
            cursor.execute('''
                SELECT pattern_type, pattern_data, file_path, created_at
                FROM code_patterns
                WHERE pattern_type = ?
                ORDER BY created_at DESC
            ''', (pattern_type,))
        else:
            cursor.execute('''
                SELECT pattern_type, pattern_data, file_path, created_at
                FROM code_patterns
                ORDER BY created_at DESC
            ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'pattern_type': row[0],
                'pattern_data': json.loads(row[1]),
                'file_path': row[2],
                'created_at': row[3]
            }
            for row in rows
        ]
    
    def mark_issue_resolved(self, issue_id: int):
        """Mark an issue as resolved"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE issues_history
            SET resolved = TRUE
            WHERE id = ?
        ''', (issue_id,))
        
        conn.commit()
        conn.close()
    
    def store_file_write(self, file_path: str, content_length: int):
        """Track file write operation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create file_operations table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                operation TEXT NOT NULL,
                content_length INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            INSERT INTO file_operations (file_path, operation, content_length)
            VALUES (?, 'write', ?)
        ''', (file_path, content_length))
        
        conn.commit()
        conn.close()
    
    def clear_memory(self):
        """Clear all memory (use with caution)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM code_analyses')
        cursor.execute('DELETE FROM code_patterns')
        cursor.execute('DELETE FROM issues_history')
        
        conn.commit()
        conn.close()
        
        logger.warning("Code memory cleared")