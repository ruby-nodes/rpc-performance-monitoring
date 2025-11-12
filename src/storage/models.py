"""
Data models for the monitoring system.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time
import json


@dataclass
class NodeInfo:
    """Information about a blockchain node."""
    
    node_type: str  # 'geth' or 'reth'
    chain_id: int
    network_name: str
    client_version: str
    protocol_version: str
    ipc_path: str
    discovered_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'node_type': self.node_type,
            'chain_id': self.chain_id,
            'network_name': self.network_name,
            'client_version': self.client_version,
            'protocol_version': self.protocol_version,
            'ipc_path': self.ipc_path,
            'discovered_at': self.discovered_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeInfo':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class SyncStatus:
    """Node synchronization status."""
    
    is_syncing: bool
    current_block: int
    highest_block: int
    starting_block: Optional[int] = None
    synced_accounts: Optional[int] = None
    synced_account_bytes: Optional[int] = None
    synced_bytecodes: Optional[int] = None
    synced_bytecode_bytes: Optional[int] = None
    synced_storage: Optional[int] = None
    synced_storage_bytes: Optional[int] = None
    
    @property
    def blocks_behind(self) -> int:
        """Number of blocks behind the network."""
        return max(0, self.highest_block - self.current_block)
    
    @property
    def sync_progress(self) -> float:
        """Sync progress as percentage (0.0 - 1.0)."""
        if not self.is_syncing or self.highest_block <= 0:
            return 1.0 if not self.is_syncing else 0.0
        
        if self.starting_block is None:
            return self.current_block / self.highest_block
        
        total_blocks = self.highest_block - self.starting_block
        completed_blocks = self.current_block - self.starting_block
        
        if total_blocks <= 0:
            return 1.0
        
        return max(0.0, min(1.0, completed_blocks / total_blocks))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'is_syncing': self.is_syncing,
            'current_block': self.current_block,
            'highest_block': self.highest_block,
            'starting_block': self.starting_block,
            'synced_accounts': self.synced_accounts,
            'synced_account_bytes': self.synced_account_bytes,
            'synced_bytecodes': self.synced_bytecodes,
            'synced_bytecode_bytes': self.synced_bytecode_bytes,
            'synced_storage': self.synced_storage,
            'synced_storage_bytes': self.synced_storage_bytes,
            'blocks_behind': self.blocks_behind,
            'sync_progress': self.sync_progress
        }


@dataclass
class PeerInfo:
    """Information about a node peer."""
    
    id: str
    name: str
    caps: List[str]
    network: Dict[str, Any]
    protocols: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'caps': self.caps,
            'network': self.network,
            'protocols': self.protocols
        }


@dataclass
class DesyncEvent:
    """Detected desynchronization event."""
    
    event_id: str
    detected_at: float
    local_block: int
    network_block: int
    blocks_behind: int
    peer_count: int
    estimated_start_time: Optional[float] = None
    recovered_at: Optional[float] = None
    recovery_duration: Optional[float] = None
    severity: str = "medium"
    context_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[float]:
        """Duration of the desync event."""
        if self.recovered_at:
            return self.recovered_at - self.detected_at
        return None
    
    @property
    def is_active(self) -> bool:
        """Whether the desync is still active."""
        return self.recovered_at is None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'event_id': self.event_id,
            'detected_at': self.detected_at,
            'local_block': self.local_block,
            'network_block': self.network_block,
            'blocks_behind': self.blocks_behind,
            'peer_count': self.peer_count,
            'estimated_start_time': self.estimated_start_time,
            'recovered_at': self.recovered_at,
            'recovery_duration': self.recovery_duration,
            'severity': self.severity,
            'duration': self.duration,
            'is_active': self.is_active,
            'context_data': self.context_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DesyncEvent':
        """Create from dictionary."""
        # Remove computed properties
        data = data.copy()
        data.pop('duration', None)
        data.pop('is_active', None)
        
        return cls(**data)


@dataclass
class MetricAnomaly:
    """Detected metric anomaly."""
    
    metric_name: str
    detected_at: float
    anomaly_type: str
    severity: str
    description: str
    current_value: float
    expected_range: Dict[str, float]
    deviation_score: float
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'metric_name': self.metric_name,
            'detected_at': self.detected_at,
            'anomaly_type': self.anomaly_type,
            'severity': self.severity,
            'description': self.description,
            'current_value': self.current_value,
            'expected_range': self.expected_range,
            'deviation_score': self.deviation_score,
            'context': self.context
        }


@dataclass
class CorrelationResult:
    """Result of correlation analysis between metrics and events."""
    
    metric_name: str
    event_type: str
    correlation_strength: float
    confidence_level: float
    sample_size: int
    analysis_window: Dict[str, float]
    patterns_detected: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'metric_name': self.metric_name,
            'event_type': self.event_type,
            'correlation_strength': self.correlation_strength,
            'confidence_level': self.confidence_level,
            'sample_size': self.sample_size,
            'analysis_window': self.analysis_window,
            'patterns_detected': self.patterns_detected
        }


@dataclass
class MonitoringState:
    """Current state of the monitoring system."""
    
    started_at: float
    node_info: Optional[NodeInfo] = None
    current_sync_status: Optional[SyncStatus] = None
    last_metrics_collection: Optional[float] = None
    active_desyncs: List[DesyncEvent] = field(default_factory=list)
    recent_anomalies: List[MetricAnomaly] = field(default_factory=list)
    system_health: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'started_at': self.started_at,
            'uptime': time.time() - self.started_at,
            'node_info': self.node_info.to_dict() if self.node_info else None,
            'current_sync_status': self.current_sync_status.to_dict() if self.current_sync_status else None,
            'last_metrics_collection': self.last_metrics_collection,
            'active_desyncs': [d.to_dict() for d in self.active_desyncs],
            'recent_anomalies': [a.to_dict() for a in self.recent_anomalies],
            'system_health': self.system_health
        }


class MonitoringStats:
    """Statistics for monitoring performance."""
    
    def __init__(self):
        self.metrics_collected = 0
        self.desyncs_detected = 0
        self.anomalies_detected = 0
        self.ipc_calls_made = 0
        self.ipc_call_failures = 0
        self.prometheus_requests = 0
        self.prometheus_request_failures = 0
        self.database_writes = 0
        self.database_write_failures = 0
        self.start_time = time.time()
    
    @property
    def uptime(self) -> float:
        """System uptime in seconds."""
        return time.time() - self.start_time
    
    @property
    def metrics_per_minute(self) -> float:
        """Average metrics collected per minute."""
        uptime_minutes = self.uptime / 60
        return self.metrics_collected / max(1, uptime_minutes)
    
    @property
    def ipc_success_rate(self) -> float:
        """IPC call success rate (0.0 - 1.0)."""
        total_calls = self.ipc_calls_made
        if total_calls == 0:
            return 1.0
        return 1.0 - (self.ipc_call_failures / total_calls)
    
    @property
    def prometheus_success_rate(self) -> float:
        """Prometheus request success rate (0.0 - 1.0)."""
        total_requests = self.prometheus_requests
        if total_requests == 0:
            return 1.0
        return 1.0 - (self.prometheus_request_failures / total_requests)
    
    @property
    def database_success_rate(self) -> float:
        """Database write success rate (0.0 - 1.0)."""
        total_writes = self.database_writes
        if total_writes == 0:
            return 1.0
        return 1.0 - (self.database_write_failures / total_writes)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'uptime': self.uptime,
            'metrics_collected': self.metrics_collected,
            'desyncs_detected': self.desyncs_detected,
            'anomalies_detected': self.anomalies_detected,
            'ipc_calls': {
                'total': self.ipc_calls_made,
                'failures': self.ipc_call_failures,
                'success_rate': self.ipc_success_rate
            },
            'prometheus_requests': {
                'total': self.prometheus_requests,
                'failures': self.prometheus_request_failures,
                'success_rate': self.prometheus_success_rate
            },
            'database_writes': {
                'total': self.database_writes,
                'failures': self.database_write_failures,
                'success_rate': self.database_success_rate
            },
            'performance': {
                'metrics_per_minute': self.metrics_per_minute
            }
        }