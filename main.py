#!/usr/bin/env python3
"""
Ethereum Node Monitor - Main Entry Point

Monitors Ethereum-based blockchain fullnodes (geth and reth) to detect and analyze desync issues.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

try:
    from utils.config import load_config
    from utils.logger import setup_logging
    from core.node_detector import NodeDetector
    from monitoring.sync_monitor import SyncMonitor
    from monitoring.metrics_collector import MetricsCollector
    from loggers.desync_logger import DesyncLogger
    from storage.database import MetricsDatabase
except ImportError as e:
    print(f"Failed to import modules: {e}")
    print("Please ensure the project is properly set up and dependencies are installed.")
    print("Install dependencies with: pip install -r requirements.txt")
    sys.exit(1)


class NodeMonitor:
    """Main node monitoring application."""
    
    def __init__(self):
        self.config = None
        self.logger = None
        self.is_running = False
        
        # Core components
        self.node_detector = None
        self.sync_monitor = None
        self.metrics_collector = None
        self.desync_logger = None
        self.database = None
        
        # Monitoring tasks
        self.monitoring_tasks = []
    
    async def initialize(self):
        """Initialize the monitoring system."""
        try:
            # Load configuration
            print("Loading configuration...")
            self.config = load_config()
            print("Configuration loaded successfully")
            
            # Setup logging
            print("Setting up logging...")
            setup_logging()  # Use default config path
            self.logger = logging.getLogger('node_monitor')
            
            self.logger.info("Initializing Ethereum Node Monitor...")
            
            # Initialize database
            print("Initializing database...")
            self.database = MetricsDatabase(self.config)
            await self.database.initialize()
            print("Database initialized successfully")
            
            # Initialize components
            self.node_detector = NodeDetector(self.config)
            self.sync_monitor = SyncMonitor(self.config)
            self.metrics_collector = MetricsCollector(self.config)
            self.desync_logger = DesyncLogger(self.config)
            
            # Initialize sync monitor
            await self.sync_monitor.initialize()
            await self.metrics_collector.initialize()
            
            # Setup callbacks
            self._setup_event_callbacks()
            
            self.logger.info("Node monitor initialized successfully")
            
        except Exception as e:
            if hasattr(self, 'logger') and self.logger:
                self.logger.error(f"Failed to initialize node monitor: {e}")
            else:
                print(f"Failed to initialize node monitor: {e}")
            sys.exit(1)
    
    def _setup_event_callbacks(self):
        """Setup event callbacks between components."""
        # Desync detection callbacks
        self.sync_monitor.add_desync_callback(self._on_desync_detected)
        self.sync_monitor.add_recovery_callback(self._on_desync_recovered)
        
        # Anomaly detection callbacks
        self.metrics_collector.add_anomaly_callback(self._on_anomaly_detected)
    
    async def _on_desync_detected(self, desync_event):
        """Handle desync detection."""
        self.logger.warning(f"DESYNC DETECTED: {desync_event.event_id}")
        
        # Log detailed desync information
        node_info = self.sync_monitor.monitoring_state.node_info
        await self.desync_logger.log_desync_event(desync_event, node_info)
        
        # Generate AI analysis prompt
        ai_prompt = await self.desync_logger.generate_ai_analysis_prompt(desync_event.event_id)
        self.logger.info(f"AI analysis prompt generated for {desync_event.event_id}")
    
    async def _on_desync_recovered(self, desync_event):
        """Handle desync recovery."""
        self.logger.info(f"DESYNC RECOVERED: {desync_event.event_id}")
        
        # Update logged event with recovery information
        node_info = self.sync_monitor.monitoring_state.node_info
        await self.desync_logger.log_desync_event(desync_event, node_info)
    
    async def _on_anomaly_detected(self, anomaly):
        """Handle anomaly detection."""
        self.logger.warning(f"METRIC ANOMALY: {anomaly.metric_name} - {anomaly.description}")
        
        # Log anomaly
        await self.desync_logger.log_anomaly(anomaly)
    
    async def start_monitoring(self):
        """Start the monitoring process."""
        self.is_running = True
        self.logger.info("Starting blockchain node monitoring...")
        
        try:
            # Start monitoring tasks
            self.monitoring_tasks = [
                asyncio.create_task(self.sync_monitor.start_monitoring()),
                asyncio.create_task(self.metrics_collector.start_collection()),
                asyncio.create_task(self._status_reporter())
            ]
            
            # Wait for all tasks to complete (or cancellation)
            await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
            
        except asyncio.CancelledError:
            self.logger.info("Monitoring cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Monitoring failed: {e}")
            raise
    
    async def _status_reporter(self):
        """Periodic status reporting."""
        while self.is_running:
            try:
                # Log status every 5 minutes
                await asyncio.sleep(300)
                
                if not self.is_running:
                    break
                
                # Get monitoring status
                sync_status = await self.sync_monitor.get_monitoring_status()
                metrics_stats = await self.metrics_collector.get_metrics_stats()
                
                self.logger.info(f"Status: Active desyncs: {len(sync_status.get('active_desyncs', []))}, "
                               f"Metrics collected: {metrics_stats.get('collection_stats', {}).get('metrics_collected', 0)}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Status reporting failed: {e}")
    
    async def shutdown(self):
        """Shutdown the monitoring system."""
        self.is_running = False
        self.logger.info("Shutting down node monitor...")
        
        # Cancel monitoring tasks
        for task in self.monitoring_tasks:
            if not task.done():
                task.cancel()
        
        # Shutdown components
        if self.sync_monitor:
            await self.sync_monitor.stop_monitoring()
        
        if self.metrics_collector:
            await self.metrics_collector.stop_collection()
        
        if self.database:
            await self.database.close()
        
        self.logger.info("Node monitor shutdown complete")


async def main():
    """Main entry point."""
    monitor = NodeMonitor()
    
    # Initialize monitoring
    await monitor.initialize()
    
    # Create a shutdown event
    shutdown_event = asyncio.Event()
    
    def signal_handler(sig, frame):
        """Handle shutdown signals."""
        monitor.logger.info(f"Received signal {sig}, shutting down...")
        shutdown_event.set()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start monitoring in background task
        monitoring_task = asyncio.create_task(monitor.start_monitoring())
        
        # Wait for shutdown signal
        await shutdown_event.wait()
        
        # Cancel monitoring task
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
        
        # Shutdown monitor
        await monitor.shutdown()
        
    except Exception as e:
        monitor.logger.error(f"Error during monitoring: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Application failed: {e}")
        sys.exit(1)
