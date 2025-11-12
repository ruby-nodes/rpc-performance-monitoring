"""
AI-optimized desync logging system.
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

try:
    from storage.models import DesyncEvent, MetricAnomaly, NodeInfo
    from storage.database import MetricsDatabase
except ImportError:
    # Fallback for development
    class DesyncEvent:
        def to_dict(self): return {}
    
    class MetricAnomaly:
        def to_dict(self): return {}
    
    class NodeInfo:
        def to_dict(self): return {}
    
    class MetricsDatabase:
        def __init__(self, config): pass


class DesyncLogger:
    """AI-optimized logging for desync events and analysis."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize desync logger.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger('desync_logger')
        self.database = MetricsDatabase(config)
        
        # Log file paths
        self.logs_dir = Path(config['logging']['logs_directory'])
        self.desync_log_path = self.logs_dir / 'desyncs' / 'desync_events.jsonl'
        self.analysis_log_path = self.logs_dir / 'analysis' / 'ai_analysis.jsonl'
        
        # Configuration
        self.context_window_minutes = config['logging'].get('context_window_minutes', 10)
        self.ai_optimization = config['logging'].get('ai_optimization_enabled', True)
        
        # Ensure log directories exist
        self.desync_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.analysis_log_path.parent.mkdir(parents=True, exist_ok=True)
    
    async def log_desync_event(self, desync_event: DesyncEvent, node_info: Optional[NodeInfo] = None):
        """
        Log a comprehensive desync event with AI-optimized format.
        
        Args:
            desync_event: The desync event to log
            node_info: Optional node information
        """
        try:
            # Create comprehensive log entry
            log_entry = await self._create_desync_log_entry(desync_event, node_info)
            
            # Write to desync log
            await self._write_log_entry(self.desync_log_path, log_entry)
            
            # If AI optimization is enabled, create analysis entry
            if self.ai_optimization:
                analysis_entry = await self._create_analysis_entry(desync_event, log_entry)
                await self._write_log_entry(self.analysis_log_path, analysis_entry)
            
            self.logger.info(f"Logged desync event: {desync_event.event_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to log desync event: {e}")
    
    async def _create_desync_log_entry(self, desync_event: DesyncEvent, node_info: Optional[NodeInfo]) -> Dict[str, Any]:
        """Create comprehensive desync log entry."""
        # Get context metrics
        context_metrics = await self._get_context_metrics(desync_event.detected_at)
        
        # Get peer information
        peer_context = await self._get_peer_context(desync_event.detected_at)
        
        # Calculate timing analysis
        timing_analysis = self._calculate_timing_analysis(desync_event)
        
        return {
            'log_metadata': {
                'log_type': 'desync_event',
                'log_version': '1.0',
                'timestamp': time.time(),
                'ai_optimized': self.ai_optimization
            },
            'event_summary': {
                'event_id': desync_event.event_id,
                'detected_at': desync_event.detected_at,
                'recovered_at': desync_event.recovered_at,
                'duration_seconds': desync_event.duration,
                'severity': desync_event.severity,
                'status': 'resolved' if desync_event.recovered_at else 'active'
            },
            'blockchain_state': {
                'local_block_height': desync_event.local_block,
                'network_block_height': desync_event.network_block,
                'blocks_behind': desync_event.blocks_behind,
                'estimated_sync_time': self._estimate_sync_time(desync_event.blocks_behind),
                'block_production_rate': self._calculate_block_rate()
            },
            'node_information': node_info.to_dict() if node_info else {},
            'network_context': {
                'peer_count': desync_event.peer_count,
                'peer_analysis': peer_context,
                'network_conditions': await self._analyze_network_conditions()
            },
            'metrics_context': {
                'context_window_minutes': self.context_window_minutes,
                'pre_event_metrics': context_metrics.get('pre_event', []),
                'during_event_metrics': context_metrics.get('during_event', []),
                'post_event_metrics': context_metrics.get('post_event', [])
            },
            'timing_analysis': timing_analysis,
            'system_health': {
                'memory_usage_patterns': await self._get_memory_patterns(),
                'cpu_usage_patterns': await self._get_cpu_patterns(),
                'disk_io_patterns': await self._get_disk_patterns(),
                'network_io_patterns': await self._get_network_patterns()
            },
            'correlation_hints': await self._generate_correlation_hints(desync_event),
            'raw_event_data': desync_event.to_dict()
        }
    
    async def _create_analysis_entry(self, desync_event: DesyncEvent, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Create AI analysis entry with structured prompts."""
        return {
            'analysis_metadata': {
                'analysis_type': 'desync_investigation',
                'event_id': desync_event.event_id,
                'timestamp': time.time(),
                'analysis_version': '1.0'
            },
            'ai_prompt_context': {
                'investigation_focus': self._generate_investigation_focus(desync_event),
                'key_questions': self._generate_key_questions(desync_event, log_entry),
                'data_summary': self._generate_data_summary(log_entry),
                'pattern_hints': self._generate_pattern_hints(log_entry)
            },
            'structured_data': {
                'event_timeline': self._create_event_timeline(desync_event, log_entry),
                'metric_anomalies': await self._identify_metric_anomalies(desync_event),
                'comparative_analysis': await self._get_comparative_data(desync_event),
                'environmental_factors': self._extract_environmental_factors(log_entry)
            },
            'analysis_suggestions': {
                'immediate_checks': self._suggest_immediate_checks(desync_event),
                'investigation_paths': self._suggest_investigation_paths(log_entry),
                'monitoring_improvements': self._suggest_monitoring_improvements(desync_event),
                'prevention_strategies': self._suggest_prevention_strategies(log_entry)
            },
            'full_context': log_entry
        }
    
    def _generate_investigation_focus(self, desync_event: DesyncEvent) -> str:
        """Generate focused investigation prompt."""
        severity_context = {
            'critical': 'This is a critical desync event requiring immediate investigation.',
            'high': 'This is a significant desync event that needs thorough analysis.',
            'medium': 'This is a moderate desync event that should be analyzed for patterns.',
            'low': 'This is a minor desync event that may indicate emerging issues.'
        }
        
        duration_context = ""
        if desync_event.duration:
            if desync_event.duration > 300:  # 5 minutes
                duration_context = "The extended duration suggests systemic issues."
            elif desync_event.duration > 60:  # 1 minute
                duration_context = "The moderate duration indicates potential performance problems."
            else:
                duration_context = "The brief duration suggests a temporary synchronization issue."
        
        return (
            f"{severity_context.get(desync_event.severity, '')} "
            f"The node fell {desync_event.blocks_behind} blocks behind the network. "
            f"{duration_context} "
            f"Focus your analysis on identifying the root cause and prevention strategies."
        )
    
    def _generate_key_questions(self, desync_event: DesyncEvent, log_entry: Dict[str, Any]) -> List[str]:
        """Generate key questions for AI analysis."""
        questions = [
            "What was the primary cause of this desynchronization event?",
            "Were there any warning signs in the metrics before the desync occurred?",
            "How do the peer connection patterns correlate with the desync timing?",
            "What resource utilization patterns preceded and accompanied this event?",
            "Are there any network-level issues that could have contributed?",
            "How does this event compare to historical desync patterns?",
            "What preventive measures could reduce the likelihood of similar events?"
        ]
        
        # Add severity-specific questions
        if desync_event.severity in ['critical', 'high']:
            questions.extend([
                "What immediate actions should be taken to prevent recurrence?",
                "Are there any infrastructure-level changes needed?"
            ])
        
        # Add duration-specific questions
        if desync_event.duration and desync_event.duration > 300:
            questions.extend([
                "Why did the recovery take so long?",
                "What factors prevented faster resynchronization?"
            ])
        
        return questions
    
    def _generate_data_summary(self, log_entry: Dict[str, Any]) -> str:
        """Generate a concise data summary for AI context."""
        event_summary = log_entry['event_summary']
        blockchain_state = log_entry['blockchain_state']
        network_context = log_entry['network_context']
        
        summary = (
            f"Desync Event Summary: "
            f"Severity: {event_summary['severity']}, "
            f"Blocks behind: {blockchain_state['blocks_behind']}, "
            f"Duration: {event_summary.get('duration_seconds', 'ongoing')} seconds, "
            f"Peer count: {network_context['peer_count']}"
        )
        
        if blockchain_state.get('estimated_sync_time'):
            summary += f", Estimated sync time: {blockchain_state['estimated_sync_time']} seconds"
        
        return summary
    
    def _generate_pattern_hints(self, log_entry: Dict[str, Any]) -> List[str]:
        """Generate pattern recognition hints for AI."""
        hints = []
        
        # Timing patterns
        event_hour = time.strftime('%H', time.localtime(log_entry['event_summary']['detected_at']))
        hints.append(f"Event occurred at hour {event_hour} - check for time-based patterns")
        
        # Severity patterns
        severity = log_entry['event_summary']['severity']
        hints.append(f"Event severity is {severity} - compare with other {severity} events")
        
        # Peer count patterns
        peer_count = log_entry['network_context']['peer_count']
        if peer_count < 10:
            hints.append("Low peer count detected - investigate network connectivity")
        elif peer_count > 50:
            hints.append("High peer count - check for network congestion patterns")
        
        return hints
    
    async def _get_context_metrics(self, event_timestamp: float) -> Dict[str, List[Dict]]:
        """Get metrics context around the event."""
        try:
            context_seconds = self.context_window_minutes * 60
            
            # Get metrics before, during, and after the event
            pre_event = await self.database.get_recent_metrics(context_seconds)
            # This is simplified - would need more sophisticated querying
            
            return {
                'pre_event': [m.to_dict() for m in pre_event[-5:]],  # Last 5 samples
                'during_event': [],  # Would get metrics during event
                'post_event': []     # Would get metrics after event
            }
        except:
            return {'pre_event': [], 'during_event': [], 'post_event': []}
    
    async def _get_peer_context(self, event_timestamp: float) -> Dict[str, Any]:
        """Get peer connection context."""
        return {
            'peer_connection_stability': 'unknown',
            'peer_geographic_distribution': 'unknown',
            'peer_version_distribution': 'unknown',
            'connection_quality_metrics': {}
        }
    
    def _calculate_timing_analysis(self, desync_event: DesyncEvent) -> Dict[str, Any]:
        """Calculate timing analysis for the event."""
        analysis = {
            'event_start_precision': 'estimated',
            'detection_delay_seconds': None,
            'recovery_characteristics': {}
        }
        
        if desync_event.recovered_at:
            analysis['recovery_characteristics'] = {
                'recovery_type': 'automatic',
                'recovery_speed': 'normal',  # Would calculate based on blocks caught up
                'recovery_duration': desync_event.duration
            }
        
        return analysis
    
    def _estimate_sync_time(self, blocks_behind: int) -> Optional[int]:
        """Estimate time to sync based on blocks behind."""
        # Simplified estimation - would use historical data
        avg_block_time = 3  # seconds (BSC = 3s, Base = 2s)
        return blocks_behind * avg_block_time
    
    def _calculate_block_rate(self) -> float:
        """Calculate current block production rate."""
        # Would analyze recent block times
        return 3.0  # placeholder
    
    async def _analyze_network_conditions(self) -> Dict[str, Any]:
        """Analyze network conditions at time of event."""
        return {
            'network_congestion_level': 'unknown',
            'validator_performance': 'unknown',
            'consensus_health': 'unknown'
        }
    
    async def _get_memory_patterns(self) -> Dict[str, Any]:
        """Get memory usage patterns."""
        return {'pattern': 'unknown', 'trend': 'stable'}
    
    async def _get_cpu_patterns(self) -> Dict[str, Any]:
        """Get CPU usage patterns."""
        return {'pattern': 'unknown', 'trend': 'stable'}
    
    async def _get_disk_patterns(self) -> Dict[str, Any]:
        """Get disk I/O patterns."""
        return {'pattern': 'unknown', 'trend': 'stable'}
    
    async def _get_network_patterns(self) -> Dict[str, Any]:
        """Get network I/O patterns."""
        return {'pattern': 'unknown', 'trend': 'stable'}
    
    async def _generate_correlation_hints(self, desync_event: DesyncEvent) -> List[str]:
        """Generate correlation analysis hints."""
        return [
            "Check correlation with peer count fluctuations",
            "Analyze memory usage spikes before event",
            "Examine network latency patterns",
            "Review disk I/O bottlenecks"
        ]
    
    def _create_event_timeline(self, desync_event: DesyncEvent, log_entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create detailed event timeline."""
        timeline = [
            {
                'timestamp': desync_event.detected_at,
                'event': 'desync_detected',
                'details': f"Node {desync_event.blocks_behind} blocks behind"
            }
        ]
        
        if desync_event.recovered_at:
            timeline.append({
                'timestamp': desync_event.recovered_at,
                'event': 'desync_recovered',
                'details': f"Recovery completed in {desync_event.duration:.1f} seconds"
            })
        
        return timeline
    
    async def _identify_metric_anomalies(self, desync_event: DesyncEvent) -> List[Dict[str, Any]]:
        """Identify metric anomalies around the event time."""
        # Would analyze metrics for anomalies
        return []
    
    async def _get_comparative_data(self, desync_event: DesyncEvent) -> Dict[str, Any]:
        """Get comparative analysis with similar events."""
        return {
            'similar_events_count': 0,
            'average_recovery_time': None,
            'common_patterns': []
        }
    
    def _extract_environmental_factors(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Extract environmental factors."""
        return {
            'system_load': log_entry.get('system_health', {}),
            'network_conditions': log_entry.get('network_context', {}),
            'blockchain_state': log_entry.get('blockchain_state', {})
        }
    
    def _suggest_immediate_checks(self, desync_event: DesyncEvent) -> List[str]:
        """Suggest immediate checks."""
        suggestions = [
            "Verify peer connectivity and count",
            "Check system resource utilization",
            "Review recent block processing times",
            "Examine network latency to consensus nodes"
        ]
        
        if desync_event.severity in ['critical', 'high']:
            suggestions.extend([
                "Consider restarting the node if recovery is slow",
                "Check for any infrastructure alerts or issues"
            ])
        
        return suggestions
    
    def _suggest_investigation_paths(self, log_entry: Dict[str, Any]) -> List[str]:
        """Suggest investigation paths."""
        return [
            "Analyze historical desync patterns for trends",
            "Compare with other nodes on the same network",
            "Review infrastructure monitoring for correlations",
            "Examine consensus node performance metrics"
        ]
    
    def _suggest_monitoring_improvements(self, desync_event: DesyncEvent) -> List[str]:
        """Suggest monitoring improvements."""
        suggestions = [
            "Add earlier warning thresholds for block lag",
            "Implement peer quality monitoring",
            "Add network latency tracking to consensus nodes",
            "Monitor system resource trends more granularly"
        ]
        
        return suggestions
    
    def _suggest_prevention_strategies(self, log_entry: Dict[str, Any]) -> List[str]:
        """Suggest prevention strategies."""
        return [
            "Optimize peer connection management",
            "Implement proactive resource scaling",
            "Add redundant consensus node connections",
            "Schedule maintenance during low-activity periods"
        ]
    
    async def _write_log_entry(self, log_path: Path, entry: Dict[str, Any]):
        """Write log entry to file."""
        try:
            with open(log_path, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to write log entry to {log_path}: {e}")
    
    async def log_anomaly(self, anomaly: MetricAnomaly):
        """Log a metric anomaly."""
        try:
            anomaly_entry = {
                'log_metadata': {
                    'log_type': 'metric_anomaly',
                    'timestamp': time.time()
                },
                'anomaly_data': anomaly.to_dict(),
                'context': {
                    'detection_method': 'statistical_analysis',
                    'baseline_window': 'rolling_average'
                }
            }
            
            anomaly_log_path = self.logs_dir / 'analysis' / 'anomalies.jsonl'
            await self._write_log_entry(anomaly_log_path, anomaly_entry)
            
        except Exception as e:
            self.logger.error(f"Failed to log anomaly: {e}")
    
    async def generate_ai_analysis_prompt(self, event_id: str) -> str:
        """Generate a comprehensive AI analysis prompt for a specific event."""
        try:
            # Read the analysis entry for the event
            analysis_entries = []
            if self.analysis_log_path.exists():
                with open(self.analysis_log_path, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            if entry.get('analysis_metadata', {}).get('event_id') == event_id:
                                analysis_entries.append(entry)
                        except:
                            continue
            
            if not analysis_entries:
                return f"No analysis data found for event {event_id}"
            
            latest_entry = analysis_entries[-1]  # Get most recent
            
            # Generate comprehensive prompt
            prompt = f"""
BLOCKCHAIN NODE DESYNC ANALYSIS REQUEST

{latest_entry['ai_prompt_context']['investigation_focus']}

KEY QUESTIONS TO ADDRESS:
{chr(10).join('- ' + q for q in latest_entry['ai_prompt_context']['key_questions'])}

DATA SUMMARY:
{latest_entry['ai_prompt_context']['data_summary']}

PATTERN RECOGNITION HINTS:
{chr(10).join('- ' + h for h in latest_entry['ai_prompt_context']['pattern_hints'])}

EVENT TIMELINE:
{chr(10).join(f"- {item['timestamp']}: {item['event']} - {item['details']}" for item in latest_entry['structured_data']['event_timeline'])}

SUGGESTED INVESTIGATION PATHS:
{chr(10).join('- ' + s for s in latest_entry['analysis_suggestions']['investigation_paths'])}

IMMEDIATE RECOMMENDED CHECKS:
{chr(10).join('- ' + c for c in latest_entry['analysis_suggestions']['immediate_checks'])}

Please provide a comprehensive analysis of this desync event, including:
1. Root cause analysis
2. Contributing factors identification
3. Impact assessment
4. Prevention recommendations
5. Monitoring improvements

Full technical context is available in the attached data structure.
"""
            
            return prompt
            
        except Exception as e:
            self.logger.error(f"Failed to generate AI prompt: {e}")
            return f"Error generating analysis prompt for event {event_id}: {e}"