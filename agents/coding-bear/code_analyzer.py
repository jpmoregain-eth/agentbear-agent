"""
Code Analyzer Module
Analyzes code for metrics, complexity, and patterns
"""

import re
import ast
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CodeMetrics:
    """Code metrics data class"""
    lines_of_code: int
    lines_of_comments: int
    blank_lines: int
    functions: int
    classes: int
    imports: int
    complexity_score: float
    issues: List[Dict[str, Any]]


class CodeAnalyzer:
    """Analyzes code for various metrics and patterns"""
    
    def __init__(self):
        self.supported_languages = ['python', 'javascript', 'typescript', 'go', 'rust', 'java']
    
    def analyze(self, code: str, file_path: str) -> Dict[str, Any]:
        """Analyze code and return metrics"""
        language = self._detect_language(file_path)
        
        if language == 'python':
            return self._analyze_python(code)
        elif language in ['javascript', 'typescript']:
            return self._analyze_javascript(code)
        else:
            return self._analyze_generic(code)
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        ext = Path(file_path).suffix.lower()
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
        }
        return lang_map.get(ext, 'generic')
    
    def _analyze_python(self, code: str) -> Dict[str, Any]:
        """Analyze Python code"""
        lines = code.split('\n')
        
        metrics = {
            'language': 'python',
            'total_lines': len(lines),
            'code_lines': 0,
            'comment_lines': 0,
            'blank_lines': 0,
            'functions': 0,
            'classes': 0,
            'imports': 0,
            'complexity_score': 0,
            'issues': []
        }
        
        in_multiline_string = False
        
        for line in lines:
            stripped = line.strip()
            
            # Track multiline strings
            if '"""' in stripped or "'''" in stripped:
                if stripped.count('"""') % 2 == 1 or stripped.count("'''") % 2 == 1:
                    in_multiline_string = not in_multiline_string
                    continue
            
            if in_multiline_string:
                metrics['comment_lines'] += 1
                continue
            
            if not stripped:
                metrics['blank_lines'] += 1
            elif stripped.startswith('#'):
                metrics['comment_lines'] += 1
            else:
                metrics['code_lines'] += 1
                
                # Count functions and classes
                if stripped.startswith('def '):
                    metrics['functions'] += 1
                elif stripped.startswith('class '):
                    metrics['classes'] += 1
                elif stripped.startswith(('import ', 'from ')):
                    metrics['imports'] += 1
        
        # Calculate complexity
        metrics['complexity_score'] = self._calculate_complexity(code, 'python')
        
        # Detect common issues
        metrics['issues'] = self._detect_python_issues(code)
        
        return metrics
    
    def _analyze_javascript(self, code: str) -> Dict[str, Any]:
        """Analyze JavaScript/TypeScript code"""
        lines = code.split('\n')
        
        metrics = {
            'language': 'javascript',
            'total_lines': len(lines),
            'code_lines': 0,
            'comment_lines': 0,
            'blank_lines': 0,
            'functions': 0,
            'classes': 0,
            'imports': 0,
            'complexity_score': 0,
            'issues': []
        }
        
        in_multiline_comment = False
        
        for line in lines:
            stripped = line.strip()
            
            # Track multiline comments
            if '/*' in stripped:
                in_multiline_comment = True
            if '*/' in stripped:
                in_multiline_comment = False
                continue
            
            if in_multiline_comment:
                metrics['comment_lines'] += 1
                continue
            
            if not stripped:
                metrics['blank_lines'] += 1
            elif stripped.startswith('//'):
                metrics['comment_lines'] += 1
            else:
                metrics['code_lines'] += 1
                
                # Count functions and classes
                if re.search(r'\bfunction\b|\bconst\s+\w+\s*=\s*\(|\b\w+\s*=>', stripped):
                    metrics['functions'] += 1
                elif stripped.startswith('class '):
                    metrics['classes'] += 1
                elif stripped.startswith(('import ', 'require(')):
                    metrics['imports'] += 1
        
        metrics['complexity_score'] = self._calculate_complexity(code, 'javascript')
        metrics['issues'] = self._detect_javascript_issues(code)
        
        return metrics
    
    def _analyze_generic(self, code: str) -> Dict[str, Any]:
        """Generic code analysis"""
        lines = code.split('\n')
        
        return {
            'language': 'generic',
            'total_lines': len(lines),
            'code_lines': len([l for l in lines if l.strip()]),
            'comment_lines': 0,
            'blank_lines': len([l for l in lines if not l.strip()]),
            'functions': 0,
            'classes': 0,
            'imports': 0,
            'complexity_score': 5.0,
            'issues': []
        }
    
    def _calculate_complexity(self, code: str, language: str) -> float:
        """Calculate cyclomatic complexity score"""
        complexity = 1
        
        if language == 'python':
            # Count decision points
            complexity += len(re.findall(r'\bif\b|\belif\b|\bfor\b|\bwhile\b|\bexcept\b|\bwith\b', code))
            complexity += len(re.findall(r'\band\b|\bor\b', code)) * 0.5
        elif language == 'javascript':
            complexity += len(re.findall(r'\bif\b|\bfor\b|\bwhile\b|\bcatch\b|\b\?\b', code))
            complexity += len(re.findall(r'\b&&\b|\b\|\|\b', code)) * 0.5
        
        return min(complexity, 20)  # Cap at 20
    
    def _detect_python_issues(self, code: str) -> List[Dict[str, Any]]:
        """Detect common Python issues"""
        issues = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Bare except
            if re.match(r'^except\s*:', stripped):
                issues.append({
                    'line': i,
                    'severity': 'warning',
                    'message': 'Bare except clause - should catch specific exceptions',
                    'rule': 'bare-except'
                })
            
            # Print statements (should use logging)
            if re.search(r'\bprint\s*\(', stripped) and not stripped.startswith('#'):
                issues.append({
                    'line': i,
                    'severity': 'info',
                    'message': 'Consider using logging instead of print',
                    'rule': 'print-statement'
                })
            
            # Mutable default arguments
            if re.search(r'def\s+\w+\s*\([^)]*=\s*(\[|\{)', stripped):
                issues.append({
                    'line': i,
                    'severity': 'warning',
                    'message': 'Mutable default argument detected',
                    'rule': 'mutable-default'
                })
        
        return issues
    
    def _detect_javascript_issues(self, code: str) -> List[Dict[str, Any]]:
        """Detect common JavaScript issues"""
        issues = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Console.log in production
            if 'console.log' in stripped and not stripped.startswith('//'):
                issues.append({
                    'line': i,
                    'severity': 'info',
                    'message': 'console.log should be removed in production',
                    'rule': 'no-console'
                })
            
            # Var usage (should use let/const)
            if re.match(r'^var\s+', stripped):
                issues.append({
                    'line': i,
                    'severity': 'warning',
                    'message': 'Use let or const instead of var',
                    'rule': 'no-var'
                })
        
        return issues
    
    def get_complexity_rating(self, score: float) -> str:
        """Get human-readable complexity rating"""
        if score <= 5:
            return "Low (Good)"
        elif score <= 10:
            return "Medium"
        elif score <= 15:
            return "High"
        else:
            return "Very High (Needs Refactoring)"