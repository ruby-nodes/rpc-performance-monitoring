#!/usr/bin/env python3
"""
Test script to isolate the IPCClient initialization issue
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_ipc_import():
    """Test importing and initializing IPCClient"""
    try:
        print("Testing IPCClient import and initialization...")
        
        # Test 1: Direct import
        from core.ipc_client import IPCClient
        print("✅ Successfully imported IPCClient from core.ipc_client")
        
        # Test 2: Initialize with new signature
        client = IPCClient(ipc_path=None, timeout=30, http_rpc_url="http://localhost:8545")
        print("✅ Successfully initialized IPCClient with keyword arguments")
        
        # Test 3: Import via sync_monitor
        from monitoring.sync_monitor import SyncMonitor
        print("✅ Successfully imported SyncMonitor")
        
        # Test 4: Check what IPCClient is available in sync_monitor scope
        from monitoring import sync_monitor
        if hasattr(sync_monitor, 'IPCClient'):
            print("⚠️  Found IPCClient in sync_monitor module scope - this might be a fallback class")
        else:
            print("✅ No IPCClient found in sync_monitor module scope")
            
        print("\n🔍 Testing component initialization...")
        
        # Test 5: Test with dummy config that matches the expected structure
        dummy_config = {
            'node': {'rpc_url': 'http://localhost:8545'},
            'ipc': {'socket_path': None, 'connection_timeout_seconds': 30, 'http_rpc_url': 'http://localhost:8545'},
            'networks': {
                'bsc': {
                    'name': 'BSC Mainnet',
                    'chain_id': 56,
                    'consensus_rpc_url': 'https://bsc-dataseed.bnbchain.org/'
                }
            },
            'monitoring': {
                'sync_check_interval_seconds': 30,
                'desync_threshold_blocks': 3,
                'desync_detection_window_seconds': 300,
                'network_timeout_seconds': 10
            }
        }
        
        sync_monitor = SyncMonitor(dummy_config)
        print("✅ Successfully initialized SyncMonitor with dummy config")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ipc_import()