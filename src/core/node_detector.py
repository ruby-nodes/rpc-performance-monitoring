"""
Node detection and information gathering.
"""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional

from core.ipc_client import IPCClient
from utils.config import get_network_config, detect_network_from_ipc


@dataclass
class NodeInfo:
    """Node information container."""
    client_type: str  # geth, reth
    version: str
    network: str  # bsc, base
    chain_id: int
    ipc_path: str
    rpc_fallback: str


class NodeDetector:
    """Detects and identifies Ethereum node type and configuration."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize node detector.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.node_config = config['node']
        self.logger = logging.getLogger('node_detector')
        
    async def detect_node(self) -> NodeInfo:
        """
        Detect node type and gather information.
        
        Returns:
            NodeInfo with detected node information
            
        Raises:
            RuntimeError: If node detection fails
        """
        if self.node_config['auto_detect']:
            return await self._auto_detect_node()
        else:
            return await self._manual_node_config()
    
    async def _auto_detect_node(self) -> NodeInfo:
        """Auto-detect node from common IPC paths."""
                # Try common IPC paths
        common_paths = [
            "/var/lib/bsc/geth.ipc",  # BSC geth
            "/tmp/reth.ipc",          # Base reth
            "/tmp/geth.ipc",          # Standard geth
            "~/.ethereum/geth.ipc"    # Home directory geth
        ]
        
        http_rpc_url = self.config.get('node', {}).get('rpc_url', 'http://localhost:8545')
        
        for ipc_path in common_paths:
            if Path(ipc_path).exists():
                self.logger.info(f"Found IPC socket at: {ipc_path}")
                
                try:
                    node_info = await self._probe_node(ipc_path, http_rpc_url)
                    self.logger.info(f"Successfully detected node: {node_info.client_type} v{node_info.version}")
                    return node_info
                except Exception as e:
                    self.logger.debug(f"Failed to probe {ipc_path}: {e}")
                    continue
        
        # If no IPC socket found, try HTTP RPC
        self.logger.info(f"No IPC socket found, trying HTTP RPC: {http_rpc_url}")
        try:
            node_info = await self._probe_node(None, http_rpc_url)
            self.logger.info(f"Successfully connected via HTTP: {node_info.client_type} v{node_info.version}")
            return node_info
        except Exception as e:
            self.logger.debug(f"Failed to connect via HTTP: {e}")
        
        raise RuntimeError("No accessible node found. Please check IPC socket availability or HTTP RPC endpoint.")
        
        # Add manually configured path if specified
        if self.node_config.get('ipc_path'):
            common_paths.insert(0, self.node_config['ipc_path'])
        
        for ipc_path in common_paths:
            if Path(ipc_path).exists():
                self.logger.info(f"Found IPC socket at: {ipc_path}")
                
                try:
                    node_info = await self._probe_node(ipc_path)
                    self.logger.info(f"Successfully detected node: {node_info.client_type} v{node_info.version}")
                    return node_info
                except Exception as e:
                    self.logger.debug(f"Failed to probe {ipc_path}: {e}")
                    continue
        
        raise RuntimeError("No accessible node found. Please check IPC socket availability.")
    
    async def _manual_node_config(self) -> NodeInfo:
        """Use manual node configuration."""
        ipc_path = self.node_config.get('ipc_path')
        http_rpc_url = self.node_config.get('rpc_url') or self.config.get('node', {}).get('rpc_url', 'http://localhost:8545')
        
        if not ipc_path:
            self.logger.info("No IPC path configured, using HTTP RPC")
            return await self._probe_node(None, http_rpc_url)
        
        if not Path(ipc_path).exists():
            self.logger.warning(f"IPC socket not found at: {ipc_path}, trying HTTP RPC")
            return await self._probe_node(None, http_rpc_url)
        
        return await self._probe_node(ipc_path, http_rpc_url)
    
    async def _probe_node(self, ipc_path: str, http_rpc_url: str = None) -> NodeInfo:
        """
        Probe node via IPC to determine type and network.
        
        Args:
            ipc_path: Path to IPC socket
            http_rpc_url: HTTP RPC URL fallback
            
        Returns:
            NodeInfo with node details
        """
        ipc_client = IPCClient(ipc_path=ipc_path, http_rpc_url=http_rpc_url)
        
        # Get client version
        version_response = await ipc_client.get_client_version()
        if not version_response.success:
            raise RuntimeError(f"Failed to get client version: {version_response.error}")
        
        client_version = version_response.data
        
        # Parse client type and version
        client_type, version = self._parse_client_version(client_version)
        
        # Get chain ID to determine network
        chain_id_response = await ipc_client.call_method("eth_chainId")
        if not chain_id_response.success:
            raise RuntimeError(f"Failed to get chain ID: {chain_id_response.error}")
        
        chain_id = int(chain_id_response.data, 16)
        
        # Determine network from chain ID
        network = self._determine_network(chain_id, ipc_path)
        
        # Get network configuration
        network_config = get_network_config(self.config, network)
        
        return NodeInfo(
            client_type=client_type,
            version=version,
            network=network,
            chain_id=chain_id,
            ipc_path=ipc_path,
            rpc_fallback=network_config['rpc_fallback']
        )
    
    def _parse_client_version(self, version_string: str) -> tuple[str, str]:
        """
        Parse client type and version from version string.
        
        Args:
            version_string: Client version string
            
        Returns:
            Tuple of (client_type, version)
        """
        version_lower = version_string.lower()
        
        if 'geth' in version_lower:
            # Format: Geth/v1.13.4-stable/linux-amd64/go1.21.3
            if '/' in version_string:
                parts = version_string.split('/')
                if len(parts) >= 2:
                    version = parts[1].replace('v', '')
                else:
                    version = "unknown"
            else:
                version = "unknown"
            return "geth", version
        
        elif 'reth' in version_lower:
            # Format: reth/v0.1.0-alpha.10/x86_64-unknown-linux-gnu
            if '/' in version_string:
                parts = version_string.split('/')
                if len(parts) >= 2:
                    version = parts[1].replace('v', '')
                else:
                    version = "unknown"
            else:
                version = "unknown"
            return "reth", version
        
        elif 'erigon' in version_lower:
            return "erigon", "unknown"
        
        elif 'besu' in version_lower:
            return "besu", "unknown"
        
        else:
            # Try to extract version from unknown client
            return "unknown", "unknown"
    
    def _determine_network(self, chain_id: int, ipc_path: str) -> str:
        """
        Determine network from chain ID and IPC path.
        
        Args:
            chain_id: Blockchain chain ID
            ipc_path: IPC socket path
            
        Returns:
            Network name
        """
        # Known chain IDs
        chain_id_to_network = {
            1: 'ethereum',      # Ethereum mainnet
            56: 'bsc',          # BSC mainnet
            8453: 'base',       # Base mainnet
            97: 'bsc_testnet',  # BSC testnet
            84531: 'base_goerli'  # Base Goerli testnet
        }
        
        if chain_id in chain_id_to_network:
            network = chain_id_to_network[chain_id]
            
            # Verify against supported networks
            if network in self.config['node']['networks']:
                return network
        
        # Fallback: detect from IPC path
        network_from_path = detect_network_from_ipc(ipc_path)
        if network_from_path in self.config['node']['networks']:
            self.logger.warning(f"Unknown chain ID {chain_id}, using path-based detection: {network_from_path}")
            return network_from_path
        
        # Default fallback
        self.logger.warning(f"Unknown chain ID {chain_id}, defaulting to BSC")
        return 'bsc'