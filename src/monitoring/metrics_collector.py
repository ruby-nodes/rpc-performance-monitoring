"""
Metrics collection and analysis system.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional

try:
    from core.prometheus_client import PrometheusClient, MetricSnapshot
    from storage.database import MetricsDatabase
    from storage.models import MetricAnomaly, MonitoringStats
    from utils.config import Config
except ImportError:
    # Fallback for development
    class PrometheusClient:
        def __init__(self, config): pass
        async def collect_metrics(self): return None
    
    class MetricSnapshot:
        def __init__(self, timestamp, samples): pass
        def to_dict(self): return {}
    
    class MetricsDatabase:
        def __init__(self, config): pass
        async def store_metrics(self, snapshot): pass
        async def store_anomaly(self, anomaly): pass
    
    class MetricAnomaly:
        def __init__(self, **kwargs): pass
    
    class MonitoringStats:
        def __init__(self): pass


class MetricsCollector:
    """Collects and analyzes Prometheus metrics."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize metrics collector.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger('metrics_collector')
        
        # Components
        self.prometheus_client = PrometheusClient(config)
        self.database = MetricsDatabase(config)
        
        # State
        self.is_collecting = False
        self.stats = MonitoringStats()
        
        # Configuration
        self.collection_interval = config['monitoring']['metrics_collection_interval_seconds']
        self.anomaly_detection_enabled = config['monitoring'].get('anomaly_detection_enabled', True)
        
        # Anomaly detection parameters
        self.baseline_window = config['monitoring'].get('anomaly_baseline_window_minutes', 60)
        self.anomaly_threshold_std = config['monitoring'].get('anomaly_threshold_standard_deviations', 2.5)
        
        # Metric baselines for anomaly detection
        self.metric_baselines: Dict[str, Dict[str, Any]] = {}
        self.recent_metrics: List[MetricSnapshot] = []
        
        # Callbacks
        self.anomaly_callbacks: List[callable] = []
    
    async def initialize(self):
        """Initialize the metrics collector."""
        try:
            # Database is already initialized in the main script
            self.logger.info("Metrics collector initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize metrics collector: {e}")
            raise
    
    def add_anomaly_callback(self, callback: callable):
        """Add callback for anomaly detection."""
        self.anomaly_callbacks.append(callback)
    
    async def start_collection(self):
        """Start metrics collection loop."""
        self.is_collecting = True
        self.logger.info("Starting metrics collection")
        
        try:
            while self.is_collecting:
                await self._collect_and_analyze()
                await asyncio.sleep(self.collection_interval)
                
        except Exception as e:
            self.logger.error(f"Metrics collection failed: {e}")
            raise
        finally:
            self.is_collecting = False
    
    async def stop_collection(self):
        """Stop metrics collection."""
        self.is_collecting = False
        self.logger.info("Stopping metrics collection")
    
    async def _collect_and_analyze(self):
        """Collect metrics and perform analysis."""
        try:
            # Collect metrics
            snapshot = await self.prometheus_client.collect_metrics()
            if not snapshot:
                self.stats.prometheus_request_failures += 1
                return
            
            self.stats.prometheus_requests += 1
            self.stats.metrics_collected += len(snapshot.samples)
            
            # Store metrics
            try:
                await self.database.store_metrics(snapshot)
                self.stats.database_writes += 1
            except Exception as e:
                self.logger.error(f"Failed to store metrics: {e}")
                self.stats.database_write_failures += 1
            
            # Add to recent metrics for analysis
            self.recent_metrics.append(snapshot)
            
            # Keep only recent metrics (last hour)
            cutoff_time = time.time() - 3600
            self.recent_metrics = [
                m for m in self.recent_metrics 
                if m.timestamp > cutoff_time
            ]
            
            # Perform anomaly detection
            if self.anomaly_detection_enabled:
                await self._detect_anomalies(snapshot)
            
            # Update baselines
            await self._update_baselines(snapshot)
            
        except Exception as e:
            self.logger.error(f"Collection and analysis failed: {e}")
    
    async def _detect_anomalies(self, snapshot: MetricSnapshot):
        """Detect anomalies in current metrics."""
        current_time = time.time()
        
        for sample in snapshot.samples:
            try:
                # Check if we have enough baseline data
                if sample.name not in self.metric_baselines:
                    continue
                
                baseline = self.metric_baselines[sample.name]
                if baseline['sample_count'] < 10:  # Need minimum samples
                    continue
                
                # Calculate deviation
                mean = baseline['mean']
                std = baseline['std']
                
                if std == 0:  # No variation in baseline
                    continue
                
                deviation = abs(sample.value - mean) / std
                
                # Check if anomaly
                if deviation > self.anomaly_threshold_std:
                    anomaly = await self._create_anomaly(sample, baseline, deviation, current_time)
                    
                    # Store anomaly
                    await self.database.store_anomaly(anomaly.to_dict())
                    self.stats.anomalies_detected += 1
                    
                    # Notify callbacks
                    for callback in self.anomaly_callbacks:
                        try:
                            await callback(anomaly)
                        except Exception as e:
                            self.logger.error(f"Anomaly callback failed: {e}")
                    
                    self.logger.warning(
                        f"ANOMALY DETECTED: {sample.name} = {sample.value:.2f} "
                        f"(expected: {mean:.2f}±{std:.2f}, deviation: {deviation:.2f}σ)"
                    )
            
            except Exception as e:
                self.logger.error(f"Anomaly detection failed for {sample.name}: {e}")
    
    async def _create_anomaly(self, sample, baseline, deviation, timestamp) -> MetricAnomaly:
        """Create anomaly object."""
        # Determine anomaly type
        anomaly_type = "spike" if sample.value > baseline['mean'] else "drop"
        
        # Determine severity
        if deviation > 5.0:
            severity = "critical"
        elif deviation > 3.5:
            severity = "high"
        elif deviation > 2.5:
            severity = "medium"
        else:
            severity = "low"
        
        # Create description
        direction = "above" if sample.value > baseline['mean'] else "below"
        description = (
            f"{sample.name} is {deviation:.1f} standard deviations {direction} "
            f"the expected range ({baseline['mean']:.2f}±{baseline['std']:.2f})"
        )
        
        return MetricAnomaly(
            metric_name=sample.name,
            detected_at=timestamp,
            anomaly_type=anomaly_type,
            severity=severity,
            description=description,
            current_value=sample.value,
            expected_range={
                'mean': baseline['mean'],
                'std': baseline['std'],
                'min': baseline['mean'] - baseline['std'],
                'max': baseline['mean'] + baseline['std']
            },
            deviation_score=deviation,
            context={
                'sample_count': baseline['sample_count'],
                'baseline_window_minutes': self.baseline_window,
                'labels': sample.labels
            }
        )
    
    async def _update_baselines(self, snapshot: MetricSnapshot):
        """Update metric baselines for anomaly detection."""
        cutoff_time = time.time() - (self.baseline_window * 60)
        
        # Group metrics by name
        metric_values: Dict[str, List[float]] = {}
        
        for historical_snapshot in self.recent_metrics:
            if historical_snapshot.timestamp < cutoff_time:
                continue
            
            for sample in historical_snapshot.samples:
                if sample.name not in metric_values:
                    metric_values[sample.name] = []
                metric_values[sample.name].append(sample.value)
        
        # Calculate baselines
        for metric_name, values in metric_values.items():
            if len(values) < 2:
                continue
            
            # Calculate statistics
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            std = variance ** 0.5
            
            self.metric_baselines[metric_name] = {
                'mean': mean,
                'std': std,
                'min': min(values),
                'max': max(values),
                'sample_count': len(values),
                'last_updated': time.time()
            }
    
    async def get_recent_anomalies(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent anomalies from database."""
        # This would query the database - simplified for now
        return []
    
    async def get_metrics_stats(self) -> Dict[str, Any]:
        """Get metrics collection statistics."""
        return {
            'collection_stats': self.stats.to_dict(),
            'baseline_metrics': len(self.metric_baselines),
            'recent_snapshots': len(self.recent_metrics),
            'anomaly_detection_enabled': self.anomaly_detection_enabled
        }
    
    def force_baseline_reset(self):
        """Force reset of all metric baselines."""
        self.metric_baselines.clear()
        self.logger.info("Metric baselines reset")


class CorrelationAnalyzer:
    """Analyzes correlations between metrics and events."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize correlation analyzer.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger('correlation_analyzer')
        self.database = MetricsDatabase(config)
        
        # Configuration
        self.analysis_window_hours = config['analysis'].get('correlation_window_hours', 24)
        self.min_correlation_strength = config['analysis'].get('min_correlation_strength', 0.5)
    
    async def analyze_desync_correlations(self, desync_event_id: str) -> List[Dict[str, Any]]:
        """
        Analyze correlations between metrics and a desync event.
        
        Args:
            desync_event_id: ID of the desync event to analyze
            
        Returns:
            List of correlation results
        """
        try:
            # This would perform statistical correlation analysis
            # between metrics patterns and desync timing
            self.logger.info(f"Analyzing correlations for desync {desync_event_id}")
            
            # Placeholder for correlation analysis
            correlations = []
            
            return correlations
            
        except Exception as e:
            self.logger.error(f"Correlation analysis failed: {e}")
            return []
    
    async def generate_pattern_report(self) -> Dict[str, Any]:
        """Generate a pattern analysis report."""
        try:
            # This would analyze historical data for patterns
            return {
                'analysis_timestamp': time.time(),
                'patterns_detected': [],
                'recommendations': []
            }
            
        except Exception as e:
            self.logger.error(f"Pattern report generation failed: {e}")
            return {}