"""
Database storage for metrics and monitoring data.
"""

try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    import sqlite3
    import asyncio
    AIOSQLITE_AVAILABLE = False
    
    # Simple async wrapper for sqlite3 when aiosqlite is not available
    class aiosqlite:
        Row = sqlite3.Row
        
        @staticmethod
        async def connect(path):
            # Create a wrapper that makes sqlite3 look like aiosqlite
            class AsyncConnection:
                def __init__(self, conn):
                    self._conn = conn
                    self.row_factory = None
                    
                async def execute(self, query, parameters=()):
                    return self._conn.execute(query, parameters)
                    
                async def commit(self):
                    self._conn.commit()
                    
                async def rollback(self):
                    self._conn.rollback()
                    
                async def close(self):
                    self._conn.close()
                    
                def __setattr__(self, name, value):
                    if name == 'row_factory':
                        self._conn.row_factory = value
                    super().__setattr__(name, value)
            
            conn = sqlite3.connect(path)
            return AsyncConnection(conn)

import json
import logging
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

try:
    from core.prometheus_client import MetricSnapshot, MetricSample
except ImportError:
    # Fallback when core modules not available
    class MetricSnapshot:
        def __init__(self, timestamp, samples):
            self.timestamp = timestamp
            self.samples = samples
        
        def to_dict(self):
            return {'timestamp': self.timestamp, 'metrics': {}}
    
    class MetricSample:
        def __init__(self, name, value, timestamp, labels=None):
            self.name = name
            self.value = value
            self.timestamp = timestamp
            self.labels = labels or {}


class MetricsDatabase:
    """SQLite database for storing metrics and monitoring data."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize metrics database.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.db_path = config['storage']['database_path']
        self.retention_hours = config['storage']['timeseries_retention_hours']
        self.logger = logging.getLogger('metrics_database')
        
        # Ensure database directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db = None
    
    async def initialize(self):
        """Initialize database and create tables."""
        self.db = await aiosqlite.connect(self.db_path)
        self.db.row_factory = aiosqlite.Row
        
        await self._create_tables()
        await self._create_indexes()
        
        # Schedule cleanup
        await self._cleanup_old_data()
        
        self.logger.info(f"Database initialized: {self.db_path}")
    
    async def close(self):
        """Close database connection."""
        if self.db:
            await self.db.close()
    
    async def _create_tables(self):
        """Create database tables."""
        # Metrics snapshots table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS metrics_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                snapshot_data TEXT NOT NULL
            )
        """)
        
        # Individual metrics table for easy querying
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                labels TEXT
            )
        """)
        
        # Desync events table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS desync_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                detected_at REAL NOT NULL,
                recovered_at REAL,
                local_block INTEGER NOT NULL,
                network_block INTEGER NOT NULL,
                blocks_behind INTEGER NOT NULL,
                estimated_start_time REAL,
                peer_count INTEGER,
                event_data TEXT NOT NULL
            )
        """)
        
        # Anomalies table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                detected_at REAL NOT NULL,
                metric_name TEXT NOT NULL,
                anomaly_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                anomaly_data TEXT NOT NULL
            )
        """)
        
        await self.db.commit()
    
    async def _create_indexes(self):
        """Create database indexes for performance."""
        # Metrics indexes
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_metrics_timestamp 
            ON metrics(timestamp)
        """)
        
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_metrics_name_timestamp 
            ON metrics(metric_name, timestamp)
        """)
        
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp 
            ON metrics_snapshots(timestamp)
        """)
        
        # Desync events indexes
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_desync_detected_at 
            ON desync_events(detected_at)
        """)
        
        # Anomalies indexes
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_anomalies_detected_at 
            ON anomalies(detected_at)
        """)
        
        await self.db.commit()
    
    async def store_metrics(self, snapshot: MetricSnapshot):
        """
        Store metrics snapshot in database.
        
        Args:
            snapshot: MetricSnapshot to store
        """
        try:
            # Store complete snapshot
            await self.db.execute(
                "INSERT INTO metrics_snapshots (timestamp, snapshot_data) VALUES (?, ?)",
                (snapshot.timestamp, json.dumps(snapshot.to_dict()))
            )
            
            # Store individual metrics for easy querying
            for sample in snapshot.samples:
                await self.db.execute(
                    "INSERT INTO metrics (timestamp, metric_name, metric_value, labels) VALUES (?, ?, ?, ?)",
                    (
                        snapshot.timestamp,
                        sample.name,
                        sample.value,
                        json.dumps(sample.labels) if sample.labels else None
                    )
                )
            
            await self.db.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to store metrics: {e}")
            if self.db:
                await self.db.rollback()
    
    async def get_recent_metrics(self, seconds: int) -> List[MetricSnapshot]:
        """
        Get recent metrics snapshots.
        
        Args:
            seconds: Number of seconds to look back
            
        Returns:
            List of MetricSnapshot objects
        """
        cutoff_time = time.time() - seconds
        
        cursor = await self.db.execute(
            "SELECT timestamp, snapshot_data FROM metrics_snapshots WHERE timestamp > ? ORDER BY timestamp",
            (cutoff_time,)
        )
        
        snapshots = []
        async for row in cursor:
            try:
                data = json.loads(row['snapshot_data'])
                samples = []
                
                for metric_name, metric_data in data['metrics'].items():
                    sample = MetricSample(
                        name=metric_name,
                        value=metric_data['value'],
                        timestamp=data['timestamp'],
                        labels=metric_data.get('labels', {})
                    )
                    samples.append(sample)
                
                snapshot = MetricSnapshot(
                    timestamp=data['timestamp'],
                    samples=samples
                )
                snapshots.append(snapshot)
                
            except Exception as e:
                self.logger.warning(f"Failed to parse stored snapshot: {e}")
                continue
        
        return snapshots
    
    async def get_metric_history(self, metric_name: str, seconds: int) -> List[Dict[str, Any]]:
        """
        Get history for a specific metric.
        
        Args:
            metric_name: Name of the metric
            seconds: Number of seconds to look back
            
        Returns:
            List of metric data points
        """
        cutoff_time = time.time() - seconds
        
        cursor = await self.db.execute(
            "SELECT timestamp, metric_value, labels FROM metrics WHERE metric_name = ? AND timestamp > ? ORDER BY timestamp",
            (metric_name, cutoff_time)
        )
        
        history = []
        async for row in cursor:
            labels = json.loads(row['labels']) if row['labels'] else {}
            history.append({
                'timestamp': row['timestamp'],
                'value': row['metric_value'],
                'labels': labels
            })
        
        return history
    
    async def store_desync_event(self, event_id: str, event_data: Dict[str, Any]):
        """
        Store desync event in database.
        
        Args:
            event_id: Unique event identifier
            event_data: Complete event data
        """
        try:
            await self.db.execute("""
                INSERT OR REPLACE INTO desync_events 
                (event_id, detected_at, recovered_at, local_block, network_block, 
                 blocks_behind, estimated_start_time, peer_count, event_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                event_data['event_metadata']['timestamp'],
                event_data.get('recovery_time'),
                event_data['desync_details']['local_block_height'],
                event_data['desync_details']['consensus_block_height'],
                event_data['desync_details']['blocks_behind'],
                event_data['desync_details'].get('estimated_desync_start'),
                event_data['peer_analysis']['peer_statistics']['total_peers'],
                json.dumps(event_data)
            ))
            
            await self.db.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to store desync event: {e}")
            if self.db:
                await self.db.rollback()
    
    async def store_anomaly(self, anomaly_data: Dict[str, Any]):
        """
        Store detected anomaly in database.
        
        Args:
            anomaly_data: Anomaly information
        """
        try:
            await self.db.execute("""
                INSERT INTO anomalies 
                (detected_at, metric_name, anomaly_type, severity, description, anomaly_data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                anomaly_data['detected_at'],
                anomaly_data['metric_name'],
                anomaly_data['anomaly_type'],
                anomaly_data['severity'],
                anomaly_data['description'],
                json.dumps(anomaly_data)
            ))
            
            await self.db.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to store anomaly: {e}")
            if self.db:
                await self.db.rollback()
    
    async def get_recent_desyncs(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get recent desync events.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of desync events
        """
        cutoff_time = time.time() - (days * 24 * 3600)
        
        cursor = await self.db.execute(
            "SELECT * FROM desync_events WHERE detected_at > ? ORDER BY detected_at DESC",
            (cutoff_time,)
        )
        
        events = []
        async for row in cursor:
            event_data = json.loads(row['event_data'])
            events.append({
                'event_id': row['event_id'],
                'detected_at': row['detected_at'],
                'recovered_at': row['recovered_at'],
                'blocks_behind': row['blocks_behind'],
                'duration': row['recovered_at'] - row['detected_at'] if row['recovered_at'] else None,
                'event_data': event_data
            })
        
        return events
    
    async def _cleanup_old_data(self):
        """Clean up old data based on retention policies."""
        try:
            cutoff_time = time.time() - (self.retention_hours * 3600)
            
            # Clean old metrics
            await self.db.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff_time,))
            await self.db.execute("DELETE FROM metrics_snapshots WHERE timestamp < ?", (cutoff_time,))
            
            # Clean old anomalies (keep longer than metrics)
            anomaly_cutoff = time.time() - (7 * 24 * 3600)  # 7 days
            await self.db.execute("DELETE FROM anomalies WHERE detected_at < ?", (anomaly_cutoff,))
            
            await self.db.commit()
            
            self.logger.info("Database cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Database cleanup failed: {e}")
            if self.db:
                await self.db.rollback()