"""
Prometheus metrics client for collecting node metrics.
"""

import aiohttp
import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from urllib.parse import urljoin

try:
    from utils.config import load_prometheus_metrics_config
except ImportError:
    # Fallback for when utils are not yet available
    def load_prometheus_metrics_config():
        return {}


@dataclass
class MetricSample:
    """Single metric sample."""
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}


@dataclass
class MetricSnapshot:
    """Snapshot of multiple metrics at a point in time."""
    timestamp: float
    samples: List[MetricSample]
    
    def get_metric(self, name: str) -> Optional[MetricSample]:
        """Get metric by name."""
        for sample in self.samples:
            if sample.name == name:
                return sample
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'timestamp': self.timestamp,
            'metrics': {
                sample.name: {
                    'value': sample.value,
                    'labels': sample.labels
                }
                for sample in self.samples
            }
        }


class PrometheusClient:
    """Client for collecting Prometheus metrics from Ethereum nodes."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Prometheus client.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.prometheus_config = config['prometheus']
        self.base_url = config['node']['prometheus_url']
        self.timeout = self.prometheus_config['timeout']
        self.logger = logging.getLogger('prometheus_client')
        
        # Load metrics configuration
        try:
            self.metrics_config = load_prometheus_metrics_config()
        except Exception as e:
            self.logger.warning(f"Failed to load metrics config: {e}")
            self.metrics_config = {}
        
        # Build list of metrics to collect
        self.target_metrics = self._build_target_metrics()
        
        self.session = None
        
    async def start(self):
        """Start the Prometheus client."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        
        # Test connection
        if await self.test_connection():
            self.logger.info(f"Connected to Prometheus at {self.base_url}")
        else:
            self.logger.warning(f"Cannot connect to Prometheus at {self.base_url}")
    
    async def stop(self):
        """Stop the Prometheus client."""
        if self.session:
            await self.session.close()
    
    async def test_connection(self) -> bool:
        """Test connection to Prometheus endpoint."""
        try:
            url = urljoin(self.base_url, '/metrics')
            async with self.session.get(url) as response:
                return response.status == 200
        except Exception as e:
            self.logger.error(f"Prometheus connection test failed: {e}")
            return False
    
    async def collect_metrics(self) -> Optional[MetricSnapshot]:
        """
        Collect current metrics snapshot.
        
        Returns:
            MetricSnapshot with current values, or None if failed
        """
        try:
            url = urljoin(self.base_url, '/metrics')
            timestamp = time.time()
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    self.logger.error(f"Prometheus returned status {response.status}")
                    return None
                
                text = await response.text()
                samples = self._parse_metrics(text, timestamp)
                
                return MetricSnapshot(timestamp=timestamp, samples=samples)
                
        except Exception as e:
            self.logger.error(f"Failed to collect metrics: {e}")
            return None
    
    async def collect_specific_metrics(self, metric_names: List[str]) -> Optional[MetricSnapshot]:
        """
        Collect only specific metrics.
        
        Args:
            metric_names: List of metric names to collect
            
        Returns:
            MetricSnapshot with requested metrics
        """
        snapshot = await self.collect_metrics()
        if not snapshot:
            return None
        
        # Filter to requested metrics
        filtered_samples = [
            sample for sample in snapshot.samples
            if sample.name in metric_names
        ]
        
        return MetricSnapshot(
            timestamp=snapshot.timestamp,
            samples=filtered_samples
        )
    
    async def get_metric_value(self, metric_name: str) -> Optional[float]:
        """
        Get current value of a specific metric.
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            Current metric value or None if not found
        """
        snapshot = await self.collect_specific_metrics([metric_name])
        if snapshot:
            sample = snapshot.get_metric(metric_name)
            if sample:
                return sample.value
        return None
    
    def _build_target_metrics(self) -> List[str]:
        """Build list of metrics to collect based on configuration."""
        target_metrics = []
        
        # Add all configured metrics
        for category_name, metrics in self.metrics_config.items():
            if category_name in ['critical_metrics', 'chain_metrics', 'performance_metrics',
                               'peer_metrics', 'resource_metrics', 'storage_metrics']:
                if isinstance(metrics, list):
                    for metric in metrics:
                        if isinstance(metric, dict) and 'name' in metric:
                            target_metrics.append(metric['name'])
        
        return target_metrics
    
    def _parse_metrics(self, metrics_text: str, timestamp: float) -> List[MetricSample]:
        """
        Parse Prometheus metrics text format.
        
        Args:
            metrics_text: Raw metrics text from Prometheus
            timestamp: Collection timestamp
            
        Returns:
            List of MetricSample objects
        """
        samples = []
        
        for line in metrics_text.split('\n'):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            try:
                # Parse metric line
                if '{' in line:
                    # Metric with labels: metric_name{label1="value1",label2="value2"} value
                    metric_part, value_str = line.rsplit(' ', 1)
                    metric_name, labels_str = metric_part.split('{', 1)
                    labels_str = labels_str.rstrip('}')
                    
                    # Parse labels
                    labels = {}
                    if labels_str:
                        for label_pair in labels_str.split(','):
                            if '=' in label_pair:
                                key, value = label_pair.split('=', 1)
                                key = key.strip()
                                value = value.strip().strip('"')
                                labels[key] = value
                else:
                    # Simple metric: metric_name value
                    metric_name, value_str = line.rsplit(' ', 1)
                    labels = {}
                
                # Only collect target metrics or if no targets specified, collect common ones
                if not self.target_metrics or metric_name in self.target_metrics or self._is_common_metric(metric_name):
                    try:
                        value = float(value_str)
                        samples.append(MetricSample(
                            name=metric_name,
                            value=value,
                            timestamp=timestamp,
                            labels=labels
                        ))
                    except ValueError:
                        # Skip invalid numeric values
                        continue
                    
            except (ValueError, IndexError):
                # Skip invalid lines
                continue
        
        return samples
    
    def _is_common_metric(self, metric_name: str) -> bool:
        """Check if metric is a commonly useful metric to collect."""
        common_patterns = [
            'p2p_peers',
            'chain_head',
            'chain_block',
            'system_memory',
            'system_cpu',
            'db_chaindata'
        ]
        
        return any(pattern in metric_name for pattern in common_patterns)
    
    def get_metric_config(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific metric.
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            Metric configuration or None if not found
        """
        for category_name, metrics in self.metrics_config.items():
            if isinstance(metrics, list):
                for metric in metrics:
                    if isinstance(metric, dict) and metric.get('name') == metric_name:
                        return metric
        return None