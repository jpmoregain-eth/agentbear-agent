"""
HTTP API Server for Coding Bear
Exposes endpoints for external tools (like GoldmanSax) to call
"""

import os
import sys
import logging
from pathlib import Path
from flask import Flask, request, jsonify
from typing import Dict, Any

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))
from coding_agent import CodingBearAgent
from registry import (
    find_available_port,
    register_bear,
    unregister_bear,
    update_bear_status
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CodingBearAPI:
    """HTTP API wrapper for Coding Bear Agent"""
    
    def __init__(self, config_path: str = "bond_config.yaml", port: int = None):
        self.config_path = config_path
        self.agent = CodingBearAgent(config_path)
        self.port = port or find_available_port(start=5001)
        self.bear_id = f"coding-bear-{self.port}"
        self.app = Flask(__name__)
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            update_bear_status(self.bear_id)
            return jsonify({
                'status': 'healthy',
                'bear_id': self.bear_id,
                'port': self.port,
                'type': 'coding'
            })
        
        @self.app.route('/api/info', methods=['GET'])
        def info():
            """Get bear information"""
            return jsonify({
                'bear_id': self.bear_id,
                'type': 'coding',
                'port': self.port,
                'capabilities': [
                    'code_generate',
                    'code_review',
                    'debug',
                    'refactor',
                    'test_generate',
                    'explain',
                    'edit_file',
                    'implement_feature'
                ],
                'config_path': self.config_path
            })
        
        @self.app.route('/api/code/generate', methods=['POST'])
        def generate_code():
            """Generate code from description"""
            data = request.json or {}
            description = data.get('description', '')
            language = data.get('language', 'python')
            save_path = data.get('save_path')
            
            if not description:
                return jsonify({'error': 'description is required'}), 400
            
            try:
                code = self.agent.generate_code(description, language, save_path)
                return jsonify({
                    'success': True,
                    'code': code,
                    'language': language,
                    'saved_to': save_path
                })
            except Exception as e:
                logger.error(f"Generate code failed: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/code/review', methods=['POST'])
        def review_code():
            """Review code file"""
            data = request.json or {}
            file_path = data.get('file_path')
            code = data.get('code')
            
            if not file_path and not code:
                return jsonify({'error': 'file_path or code is required'}), 400
            
            try:
                review = self.agent.review_code(file_path, code)
                return jsonify({
                    'success': True,
                    'review': review,
                    'file_path': file_path
                })
            except Exception as e:
                logger.error(f"Review code failed: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/code/debug', methods=['POST'])
        def debug_error():
            """Debug an error"""
            data = request.json or {}
            error_message = data.get('error_message')
            code = data.get('code')
            context = data.get('context')
            
            if not error_message:
                return jsonify({'error': 'error_message is required'}), 400
            
            try:
                result = self.agent.debug_error(error_message, code, context)
                return jsonify({
                    'success': True,
                    'analysis': result
                })
            except Exception as e:
                logger.error(f"Debug failed: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/code/refactor', methods=['POST'])
        def refactor_code():
            """Refactor code"""
            data = request.json or {}
            file_path = data.get('file_path')
            goal = data.get('goal', 'improve')
            
            if not file_path:
                return jsonify({'error': 'file_path is required'}), 400
            
            try:
                refactored = self.agent.refactor_code(file_path, goal=goal)
                return jsonify({
                    'success': True,
                    'refactored_code': refactored,
                    'file_path': file_path
                })
            except Exception as e:
                logger.error(f"Refactor failed: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/code/edit', methods=['POST'])
        def edit_code():
            """Edit code file"""
            data = request.json or {}
            file_path = data.get('file_path')
            changes = data.get('changes')
            
            if not file_path or not changes:
                return jsonify({'error': 'file_path and changes are required'}), 400
            
            try:
                self.agent.edit_file(file_path, changes)
                return jsonify({
                    'success': True,
                    'file_path': file_path,
                    'message': 'File edited successfully'
                })
            except Exception as e:
                logger.error(f"Edit failed: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/code/test', methods=['POST'])
        def generate_tests():
            """Generate tests for code"""
            data = request.json or {}
            file_path = data.get('file_path')
            code = data.get('code')
            
            if not file_path and not code:
                return jsonify({'error': 'file_path or code is required'}), 400
            
            try:
                tests = self.agent.generate_tests(file_path, code)
                return jsonify({
                    'success': True,
                    'tests': tests
                })
            except Exception as e:
                logger.error(f"Test generation failed: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/code/implement', methods=['POST'])
        def implement_feature():
            """Implement feature in existing file"""
            data = request.json or {}
            file_path = data.get('file_path')
            feature = data.get('feature')
            
            if not file_path or not feature:
                return jsonify({'error': 'file_path and feature are required'}), 400
            
            try:
                updated = self.agent.implement_feature(file_path, feature)
                return jsonify({
                    'success': True,
                    'updated_code': updated,
                    'file_path': file_path
                })
            except Exception as e:
                logger.error(f"Implementation failed: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/file/read', methods=['POST'])
        def read_file():
            """Read file contents"""
            data = request.json or {}
            file_path = data.get('file_path')
            limit = data.get('limit', 100)
            
            if not file_path:
                return jsonify({'error': 'file_path is required'}), 400
            
            try:
                content = self.agent.read_file(file_path, limit)
                return jsonify({
                    'success': True,
                    'content': content,
                    'file_path': file_path
                })
            except Exception as e:
                logger.error(f"Read file failed: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/file/write', methods=['POST'])
        def write_file():
            """Write content to file"""
            data = request.json or {}
            file_path = data.get('file_path')
            content = data.get('content')
            
            if not file_path or content is None:
                return jsonify({'error': 'file_path and content are required'}), 400
            
            try:
                self.agent.write_file(file_path, content)
                return jsonify({
                    'success': True,
                    'file_path': file_path,
                    'bytes_written': len(content)
                })
            except Exception as e:
                logger.error(f"Write file failed: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/git/status', methods=['GET'])
        def git_status():
            """Get git status"""
            try:
                import subprocess
                result = subprocess.run(
                    ['git', 'status', '--short'],
                    capture_output=True,
                    text=True,
                    cwd=Path(self.config_path).parent
                )
                return jsonify({
                    'success': True,
                    'status': result.stdout,
                    'has_changes': bool(result.stdout.strip())
                })
            except Exception as e:
                logger.error(f"Git status failed: {e}")
                return jsonify({'error': str(e)}), 500
    
    def run(self):
        """Run the API server"""
        # Register in registry
        register_bear(
            bear_id=self.bear_id,
            bear_type='coding',
            port=self.port,
            name=f'Coding Bear {self.port}',
            capabilities=[
                'code_generate',
                'code_review',
                'debug',
                'refactor',
                'test_generate',
                'explain',
                'edit_file',
                'implement_feature',
                'git_operations'
            ],
            metadata={
                'config_path': str(Path(self.config_path).absolute()),
                'version': '0.1.0'
            }
        )
        
        logger.info(f"🐻 Coding Bear API starting on port {self.port}")
        logger.info(f"   Bear ID: {self.bear_id}")
        logger.info(f"   Health check: http://localhost:{self.port}/health")
        logger.info(f"   API docs: http://localhost:{self.port}/api/info")
        
        try:
            # Run Flask app
            self.app.run(
                host='0.0.0.0',
                port=self.port,
                debug=False,
                use_reloader=False
            )
        finally:
            # Unregister on shutdown
            unregister_bear(self.bear_id)
            logger.info(f"🐻 Coding Bear {self.bear_id} shut down")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Coding Bear API Server')
    parser.add_argument('--config', default='bond_config.yaml', help='Config file path')
    parser.add_argument('--port', type=int, help='Port to run on (auto if not specified)')
    
    args = parser.parse_args()
    
    api = CodingBearAPI(args.config, args.port)
    api.run()


if __name__ == '__main__':
    main()