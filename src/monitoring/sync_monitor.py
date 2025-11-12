"""
Synchronization monitoring system.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable

try:
    from core.ipc_client import IPCClient
    from core.prometheus_client import PrometheusClient
    from storage.database import MetricsDatabase
    from storage.models import SyncStatus, DesyncEvent, NodeInfo, MonitoringState
    from utils.config import Config
except ImportError:
    # Fallback for development
    class IPCClient:
        def __init__(self, config): pass
        async def get_sync_status(self): return None
        async def get_peer_count(self): return 0
        async def get_latest_block(self): return 0
    
    class PrometheusClient:
        def __init__(self, config): pass
        async def collect_metrics(self): return None
    
    class MetricsDatabase:
        def __init__(self, config): pass
        async def initialize(self): pass
        async def store_desync_event(self, id, data): pass
    
    class SyncStatus:
        def __init__(self, **kwargs): pass
    
    class DesyncEvent:
        def __init__(self, **kwargs): pass
    
    class NodeInfo:
        def __init__(self, **kwargs): pass
    
    class MonitoringState:
        def __init__(self, **kwargs): pass


class SyncMonitor:
    """Main synchronization monitoring component."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize sync monitor.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger('sync_monitor')
        
        # Components
        self.ipc_client = IPCClient(config)
        self.prometheus_client = PrometheusClient(config)
        self.database = MetricsDatabase(config)
        
        # State
        self.monitoring_state = MonitoringState(started_at=time.time())
        self.is_running = False
        self.current_desync: Optional[DesyncEvent] = None
        
        # Configuration
        self.check_interval = config['monitoring']['sync_check_interval_seconds']
        self.desync_threshold = config['monitoring']['desync_threshold_blocks']
        self.desync_detection_window = config['monitoring']['desync_detection_window_seconds']
        self.network_timeout = config['monitoring']['network_timeout_seconds']
        
        # Callbacks
        self.desync_callbacks: list[Callable] = []
        self.recovery_callbacks: list[Callable] = []
        
        # RPC endpoint for consensus comparison
        network_config = self._get_network_config()
        self.consensus_rpc_url = network_config.get('consensus_rpc_url')
    
    def _get_network_config(self) -> Dict[str, Any]:
        """Get network configuration based on detected node."""
        # Default to BSC for now - will be updated when node is detected
        return self.config['networks']['bsc']
    
    async def initialize(self):
        """Initialize the monitoring system."""
        try:
            # Initialize database
            await self.database.initialize()
            
            # Detect node type and update configuration
            node_info = await self._detect_node()
            if node_info:
                self.monitoring_state.node_info = node_info
                self._update_network_config(node_info)
            
            self.logger.info("Sync monitor initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize sync monitor: {e}")
            raise
    
    async def _detect_node(self) -> Optional[NodeInfo]:
        """Detect node type and configuration."""
        try:
            # Try to connect and get node info
            version_response = await self.ipc_client.get_client_version()
            if not version_response or not version_response.success:
                return None
            
            client_version = version_response.data
            
            # Determine node type
            node_type = 'geth' if 'geth' in client_version.lower() else 'reth'
            
            # Get additional info
            chain_response = await self.ipc_client.get_chain_id()
            protocol_response = await self.ipc_client.get_protocol_version()
            
            chain_id = chain_response.data if chain_response and chain_response.success else 0
            protocol_version = protocol_response.data if protocol_response and protocol_response.success else ""
            
            # Determine network
            network_name = 'bsc' if chain_id == 56 else 'base' if chain_id == 8453 else 'unknown'
            
            return NodeInfo(
                node_type=node_type,
                chain_id=chain_id,
                network_name=network_name,
                client_version=client_version,
                protocol_version=protocol_version,
                ipc_path=self.config['ipc']['socket_path']
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to detect node: {e}")
            return None
    
    def _update_network_config(self, node_info: NodeInfo):
        """Update network configuration based on detected node."""
        if node_info.network_name in self.config['networks']:
            network_config = self.config['networks'][node_info.network_name]
            self.consensus_rpc_url = network_config.get('consensus_rpc_url')
            
            self.logger.info(f"Updated configuration for {node_info.network_name} network")
    
    def add_desync_callback(self, callback: Callable[[DesyncEvent], None]):
        """Add callback for desync detection."""
        self.desync_callbacks.append(callback)
    
    def add_recovery_callback(self, callback: Callable[[DesyncEvent], None]):
        """Add callback for desync recovery."""
        self.recovery_callbacks.append(callback)
    
    async def start_monitoring(self):
        """Start the monitoring loop."""
        self.is_running = True
        self.logger.info("Starting sync monitoring")
        
        try:
            while self.is_running:
                await self._check_sync_status()
                await asyncio.sleep(self.check_interval)
                
        except Exception as e:
            self.logger.error(f"Monitoring loop failed: {e}")
            raise
        finally:
            self.is_running = False
    
    async def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.is_running = False
        self.logger.info("Stopping sync monitoring")
        
        # Close database connection
        await self.database.close()
    
    async def _check_sync_status(self):
        """Check current synchronization status."""
        try:
            # Get local node status
            sync_status = await self.ipc_client.get_sync_status()
            if not sync_status:
                self.logger.warning("Could not get sync status from local node")
                return
            
            self.monitoring_state.current_sync_status = sync_status
            
            # Check for desync
            await self._check_for_desync(sync_status)
            
            # Update last check time
            self.monitoring_state.last_metrics_collection = time.time()
            
        except Exception as e:
            self.logger.error(f"Failed to check sync status: {e}")
    
    async def _check_for_desync(self, sync_status: SyncStatus):
        """
        Check if node is desynced.
        
        Args:
            sync_status: Current sync status
        """
        try:
            # Get consensus block height
            consensus_block = await self._get_consensus_block_height()
            if consensus_block is None:
                return
            
            blocks_behind = consensus_block - sync_status.current_block
            
            # Check desync threshold
            if blocks_behind >= self.desync_threshold:
                if not self.current_desync:
                    # New desync detected
                    await self._handle_desync_detection(sync_status, consensus_block, blocks_behind)
                else:
                    # Update existing desync
                    self.current_desync.blocks_behind = blocks_behind
                    self.current_desync.network_block = consensus_block
                    self.current_desync.local_block = sync_status.current_block
            else:
                if self.current_desync:
                    # Recovery detected
                    await self._handle_desync_recovery(sync_status, consensus_block)
            
        except Exception as e:
            self.logger.error(f"Failed to check for desync: {e}")
    
    async def _get_consensus_block_height(self) -> Optional[int]:
        """Get consensus block height from network RPC."""
        try:
            if not self.consensus_rpc_url:
                return None
            
            import aiohttp
            import json
            
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": 1
            }
            
            timeout = aiohttp.ClientTimeout(total=self.network_timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.consensus_rpc_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'result' in data:
                            return int(data['result'], 16)
            
            return None
            
        except ImportError:
            self.logger.warning("aiohttp not available for consensus RPC calls")
            return None
        except Exception as e:
            self.logger.warning(f"Failed to get consensus block height: {e}")
            return None
    
    async def _handle_desync_detection(self, sync_status: SyncStatus, consensus_block: int, blocks_behind: int):
        """Handle new desync detection."""
        event_id = f"desync_{int(time.time())}"
        peer_count = await self.ipc_client.get_peer_count()
        
        self.current_desync = DesyncEvent(
            event_id=event_id,
            detected_at=time.time(),
            local_block=sync_status.current_block,
            network_block=consensus_block,
            blocks_behind=blocks_behind,
            peer_count=peer_count,
            severity=self._calculate_desync_severity(blocks_behind)
        )
        
        # Add to active desyncs
        self.monitoring_state.active_desyncs.append(self.current_desync)
        
        # Create detailed event data for logging
        event_data = await self._create_detailed_event_data(self.current_desync)
        
        # Store in database
        await self.database.store_desync_event(event_id, event_data)
        
        # Notify callbacks
        for callback in self.desync_callbacks:
            try:
                await callback(self.current_desync)
            except Exception as e:
                self.logger.error(f"Desync callback failed: {e}")
        
        self.logger.warning(
            f"DESYNC DETECTED: {blocks_behind} blocks behind consensus "
            f"(local: {sync_status.current_block}, network: {consensus_block})"
        )
    
    async def _handle_desync_recovery(self, sync_status: SyncStatus, consensus_block: int):
        """Handle desync recovery."""
        if not self.current_desync:
            return
        
        recovery_time = time.time()
        self.current_desync.recovered_at = recovery_time
        self.current_desync.recovery_duration = recovery_time - self.current_desync.detected_at
        
        # Update event data
        event_data = await self._create_detailed_event_data(self.current_desync)
        await self.database.store_desync_event(self.current_desync.event_id, event_data)
        
        # Notify callbacks
        for callback in self.recovery_callbacks:
            try:
                await callback(self.current_desync)
            except Exception as e:
                self.logger.error(f"Recovery callback failed: {e}")
        
        self.logger.info(
            f"DESYNC RECOVERED: Event {self.current_desync.event_id} "
            f"lasted {self.current_desync.recovery_duration:.1f} seconds"
        )
        
        # Remove from active desyncs
        if self.current_desync in self.monitoring_state.active_desyncs:
            self.monitoring_state.active_desyncs.remove(self.current_desync)
        
        self.current_desync = None
    
    def _calculate_desync_severity(self, blocks_behind: int) -> str:
        """Calculate desync severity based on blocks behind."""
        if blocks_behind >= 1000:
            return "critical"
        elif blocks_behind >= 100:
            return "high"
        elif blocks_behind >= 10:
            return "medium"
        else:
            return "low"
    
    async def _create_detailed_event_data(self, desync_event: DesyncEvent) -> Dict[str, Any]:
        """Create detailed event data for logging and analysis."""
        # Get additional context
        peer_count = await self.ipc_client.get_peer_count()
        
        # Get recent metrics for context
        try:
            recent_metrics = await self.database.get_recent_metrics(600)  # 10 minutes
        except:
            recent_metrics = []
        
        return {
            'event_metadata': {
                'event_id': desync_event.event_id,
                'timestamp': desync_event.detected_at,
                'detection_source': 'sync_monitor',
                'node_info': self.monitoring_state.node_info.to_dict() if self.monitoring_state.node_info else {}
            },
            'desync_details': {
                'local_block_height': desync_event.local_block,
                'consensus_block_height': desync_event.network_block,
                'blocks_behind': desync_event.blocks_behind,
                'severity': desync_event.severity,
                'estimated_desync_start': desync_event.estimated_start_time,
                'recovery_time': desync_event.recovered_at,
                'duration_seconds': desync_event.recovery_duration
            },
            'peer_analysis': {
                'peer_statistics': {
                    'total_peers': peer_count,
                    'collection_timestamp': time.time()
                }
            },
            'metrics_context': {
                'metrics_window_seconds': 600,
                'metrics_collected': len(recent_metrics),
                'context_data': [m.to_dict() for m in recent_metrics[-10:]]  # Last 10 samples
            },
            'system_context': {
                'monitoring_uptime': time.time() - self.monitoring_state.started_at,
                'configuration': {
                    'desync_threshold': self.desync_threshold,
                    'check_interval': self.check_interval
                }
            }
        }
    
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        return self.monitoring_state.to_dict()