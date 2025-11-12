"""
Universal IPC client for both geth and reth nodes with HTTP RPC fallback.
"""

import json
import socket
import asyncio
import logging
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class IPCResponse:
    """IPC response wrapper."""
    success: bool
    data: Any
    error: Optional[str] = None
    method: Optional[str] = None


class IPCClient:
    """Universal IPC client supporting both geth and reth with HTTP RPC fallback."""
    
    def __init__(self, ipc_path: str = None, timeout: int = 30, http_rpc_url: str = None):
        """
        Initialize IPC client.
        
        Args:
            ipc_path: Path to IPC socket (optional)
            timeout: Request timeout in seconds
            http_rpc_url: HTTP RPC URL fallback (optional)
        """
        self.ipc_path = ipc_path
        self.http_rpc_url = http_rpc_url or "http://localhost:8545"
        self.timeout = timeout
        self.logger = logging.getLogger('ipc_client')
        self._request_id = 0
        self._use_http = False
        
        # Auto-detect connection method
        if not ipc_path or not Path(ipc_path).exists():
            self.logger.info(f"IPC socket not available, using HTTP RPC: {self.http_rpc_url}")
            self._use_http = True
        
    async def call_method(self, method: str, params: List[Any] = None) -> IPCResponse:
        """
        Call JSON-RPC method via IPC or HTTP.
        
        Args:
            method: RPC method name
            params: Method parameters
            
        Returns:
            IPCResponse with result or error
        """
        if params is None:
            params = []
        
        self._request_id += 1
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._request_id
        }
        
        try:
            if self._use_http:
                return await self._call_http(request, method)
            else:
                return await self._call_ipc(request, method)
                
        except Exception as e:
            self.logger.error(f"Failed to call {method}: {e}")
            return IPCResponse(
                success=False,
                error=str(e),
                method=method
            )
    
    async def _call_http(self, request: dict, method: str) -> IPCResponse:
        """Call method via HTTP RPC."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.http_rpc_url,
                    json=request,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status != 200:
                        return IPCResponse(
                            success=False,
                            error=f"HTTP {response.status}: {await response.text()}",
                            method=method
                        )
                    
                    response_data = await response.json()
                    
                    if "error" in response_data:
                        return IPCResponse(
                            success=False,
                            error=response_data["error"].get("message", "Unknown RPC error"),
                            method=method
                        )
                    
                    return IPCResponse(
                        success=True,
                        data=response_data.get("result"),
                        method=method
                    )
                    
        except asyncio.TimeoutError:
            return IPCResponse(
                success=False,
                error=f"HTTP request timeout after {self.timeout}s",
                method=method
            )
        except Exception as e:
            return IPCResponse(
                success=False,
                error=f"HTTP request failed: {e}",
                method=method
            )
    
    async def _call_ipc(self, request: dict, method: str) -> IPCResponse:
        """Call method via IPC socket."""
        try:
            # Check if IPC socket exists
            if not Path(self.ipc_path).exists():
                return IPCResponse(
                    success=False,
                    error=f"IPC socket not found: {self.ipc_path}",
                    method=method
                )
            
            # Connect and send request
            reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(self.ipc_path),
                timeout=self.timeout
            )
            
            # Send request
            request_data = json.dumps(request) + '\n'
            writer.write(request_data.encode('utf-8'))
            await writer.drain()
            
            # Read response
            response_data = await asyncio.wait_for(
                reader.readline(),
                timeout=self.timeout
            )
            
            writer.close()
            await writer.wait_closed()
            
            # Parse response
            if not response_data:
                return IPCResponse(
                    success=False,
                    error="Empty response from node",
                    method=method
                )
            
            response = json.loads(response_data.decode('utf-8'))
            
            if 'error' in response:
                return IPCResponse(
                    success=False,
                    error=response['error']['message'],
                    method=method
                )
            
            return IPCResponse(
                success=True,
                data=response.get('result'),
                method=method
            )
            
        except asyncio.TimeoutError:
            return IPCResponse(
                success=False,
                error=f"Request timeout after {self.timeout}s",
                method=method
            )
        except json.JSONDecodeError as e:
            return IPCResponse(
                success=False,
                error=f"Invalid JSON response: {e}",
                method=method
            )
        except Exception as e:
            return IPCResponse(
                success=False,
                error=f"IPC communication error: {e}",
                method=method
            )
    
    async def get_block_number(self) -> IPCResponse:
        """Get current block number."""
        return await self.call_method("eth_blockNumber")
    
    async def get_syncing_status(self) -> IPCResponse:
        """Get sync status."""
        return await self.call_method("eth_syncing")
    
    async def get_peer_count(self) -> IPCResponse:
        """Get connected peer count."""
        return await self.call_method("net_peerCount")
    
    async def get_peers(self) -> IPCResponse:
        """Get detailed peer information."""
        return await self.call_method("admin_peers")
    
    async def get_node_info(self) -> IPCResponse:
        """Get node information."""
        return await self.call_method("admin_nodeInfo")
    
    async def get_client_version(self) -> IPCResponse:
        """Get client version."""
        return await self.call_method("web3_clientVersion")
    
    async def get_chain_id(self) -> IPCResponse:
        """Get chain ID."""
        return await self.call_method("eth_chainId")
    
    async def get_protocol_version(self) -> IPCResponse:
        """Get protocol version."""
        return await self.call_method("eth_protocolVersion")
    
    async def get_sync_status(self) -> Optional[object]:
        """Get synchronization status - returns SyncStatus object or None."""
        syncing_response = await self.get_syncing_status()
        if not syncing_response.success:
            return None
            
        block_response = await self.get_block_number()
        if not block_response.success:
            return None
            
        # Mock SyncStatus object since we don't have the import
        class SyncStatus:
            def __init__(self, is_syncing, current_block, highest_block):
                self.is_syncing = is_syncing
                # Convert hex strings to decimal integers
                self.current_block = self._hex_to_int(current_block)
                self.highest_block = self._hex_to_int(highest_block)
                
            def _hex_to_int(self, value):
                """Convert hex string to integer, handle various input types."""
                if isinstance(value, str) and value.startswith('0x'):
                    try:
                        return int(value, 16)
                    except ValueError:
                        return 0
                elif isinstance(value, int):
                    return value
                else:
                    return 0
        
        if syncing_response.data is False:
            # Not syncing, fully synced
            return SyncStatus(False, block_response.data, block_response.data)
        else:
            # Still syncing
            sync_data = syncing_response.data
            return SyncStatus(
                True,
                sync_data.get('currentBlock', 0),
                sync_data.get('highestBlock', 0)
            )
    
    async def get_latest_block(self) -> int:
        """Get latest block number."""
        response = await self.get_block_number()
        if response.success and response.data:
            try:
                return int(response.data, 16)  # Convert hex string to int
            except (ValueError, TypeError):
                return 0
        return 0
    
    async def is_connected(self) -> bool:
        """Check if IPC connection is working."""
        response = await self.call_method("net_version")
        return response.success
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.
        
        Returns:
            Health check results
        """
        health = {
            "connected": False,
            "block_number": None,
            "peer_count": None,
            "sync_status": None,
            "client_version": None,
            "response_times": {},
            "errors": []
        }
        
        # Test basic connectivity
        import time
        start_time = time.time()
        version_response = await self.get_client_version()
        health["response_times"]["client_version"] = time.time() - start_time
        
        if not version_response.success:
            health["errors"].append(f"Client version check failed: {version_response.error}")
            return health
        
        health["connected"] = True
        health["client_version"] = version_response.data
        
        # Get block number
        start_time = time.time()
        block_response = await self.get_block_number()
        health["response_times"]["block_number"] = time.time() - start_time
        
        if block_response.success:
            # Convert hex to int
            health["block_number"] = int(block_response.data, 16)
        else:
            health["errors"].append(f"Block number check failed: {block_response.error}")
        
        # Get peer count
        start_time = time.time()
        peer_response = await self.get_peer_count()
        health["response_times"]["peer_count"] = time.time() - start_time
        
        if peer_response.success:
            health["peer_count"] = int(peer_response.data, 16)
        else:
            health["errors"].append(f"Peer count check failed: {peer_response.error}")
        
        # Get sync status
        start_time = time.time()
        sync_response = await self.get_syncing_status()
        health["response_times"]["sync_status"] = time.time() - start_time
        
        if sync_response.success:
            health["sync_status"] = sync_response.data
        else:
            health["errors"].append(f"Sync status check failed: {sync_response.error}")
        
        return health