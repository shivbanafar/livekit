"""
HTTP server for dynamically updating ignored words and command words at runtime.
"""

import asyncio
import json
from typing import Optional
from aiohttp import web, web_request
from aiohttp.web_response import Response

from ..interruption_filter import InterruptionFilter


class DynamicUpdateServer:
    """
    HTTP server that provides endpoints for runtime configuration updates.
    """
    
    def __init__(
        self,
        filter_instance: InterruptionFilter,
        port: int = 9090,
        token: Optional[str] = None
    ):
        """
        Initialize the dynamic update server.
        
        Args:
            filter_instance: InterruptionFilter instance to update
            port: Port to listen on
            token: Optional authentication token
        """
        self.filter = filter_instance
        self.port = port
        self.token = token
        self.app = web.Application()
        self._setup_routes()
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
    
    def _setup_routes(self):
        """Set up HTTP routes."""
        self.app.router.add_get('/ignored-words', self.get_ignored_words)
        self.app.router.add_post('/ignored-words', self.update_ignored_words)
        self.app.router.add_get('/command-words', self.get_command_words)
        self.app.router.add_post('/command-words', self.update_command_words)
        self.app.router.add_get('/health', self.health_check)
    
    def _check_auth(self, request: web_request.Request) -> bool:
        """Check if request is authenticated."""
        if not self.token:
            return True  # No auth required
        
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            provided_token = auth_header[7:]
            return provided_token == self.token
        
        # Also check query parameter
        provided_token = request.query.get('token')
        return provided_token == self.token
    
    async def get_ignored_words(self, request: web_request.Request) -> Response:
        """Get current ignored words list."""
        if not self._check_auth(request):
            return web.json_response({'error': 'Unauthorized'}, status=401)
        
        async with self.filter._lock:
            words = list(self.filter._ignored_words)
        
        return web.json_response({'ignored_words': words})
    
    async def update_ignored_words(self, request: web_request.Request) -> Response:
        """Update ignored words list."""
        if not self._check_auth(request):
            return web.json_response({'error': 'Unauthorized'}, status=401)
        
        try:
            data = await request.json()
            words = data.get('ignored_words', [])
            
            if not isinstance(words, list):
                return web.json_response(
                    {'error': 'ignored_words must be a list'}, 
                    status=400
                )
            
            await self.filter.update_ignored_words(words)
            
            async with self.filter._lock:
                current_words = list(self.filter._ignored_words)
            
            return web.json_response({
                'success': True,
                'ignored_words': current_words
            })
        except json.JSONDecodeError:
            return web.json_response({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_command_words(self, request: web_request.Request) -> Response:
        """Get current command words list."""
        if not self._check_auth(request):
            return web.json_response({'error': 'Unauthorized'}, status=401)
        
        async with self.filter._lock:
            words = list(self.filter._command_words)
        
        return web.json_response({'command_words': words})
    
    async def update_command_words(self, request: web_request.Request) -> Response:
        """Update command words list."""
        if not self._check_auth(request):
            return web.json_response({'error': 'Unauthorized'}, status=401)
        
        try:
            data = await request.json()
            words = data.get('command_words', [])
            
            if not isinstance(words, list):
                return web.json_response(
                    {'error': 'command_words must be a list'}, 
                    status=400
                )
            
            await self.filter.update_command_words(words)
            
            async with self.filter._lock:
                current_words = list(self.filter._command_words)
            
            return web.json_response({
                'success': True,
                'command_words': current_words
            })
        except json.JSONDecodeError:
            return web.json_response({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def health_check(self, request: web_request.Request) -> Response:
        """Health check endpoint."""
        return web.json_response({'status': 'ok'})
    
    async def start(self):
        """Start the HTTP server."""
        self._runner = web.AppRunner(self.app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, '0.0.0.0', self.port)
        await self._site.start()
        print(f"Dynamic update server started on port {self.port}")
    
    async def stop(self):
        """Stop the HTTP server."""
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()

