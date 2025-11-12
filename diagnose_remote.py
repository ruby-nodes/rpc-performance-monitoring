#!/usr/bin/env python3
"""
Minimal test to diagnose the IPCClient issue on remote node
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def diagnose_issue():
    """Diagnose the IPCClient initialization issue."""
    
    print("🔍 Diagnosing IPCClient issue...")
    print("=" * 50)
    
    try:
        print("1. Testing core.ipc_client import...")
        from core.ipc_client import IPCClient as CoreIPCClient
        print("✅ Successfully imported from core.ipc_client")
        
        # Test new signature
        client = CoreIPCClient(ipc_path=None, timeout=30, http_rpc_url="http://localhost:8545")
        print("✅ Core IPCClient accepts new signature")
        
    except Exception as e:
        print(f"❌ Core import failed: {e}")
        return
    
    try:
        print("\n2. Testing sync_monitor import...")
        from monitoring.sync_monitor import SyncMonitor
        print("✅ Successfully imported SyncMonitor")
        
        print("\n3. Checking for fallback classes...")
        import monitoring.sync_monitor as sm_module
        
        # Check if there's a fallback IPCClient in the module
        fallback_attrs = []
        for attr in dir(sm_module):
            if 'IPCClient' in str(getattr(sm_module, attr, '')):
                fallback_attrs.append(attr)
        
        if fallback_attrs:
            print(f"⚠️  Found potential fallback IPCClient: {fallback_attrs}")
        else:
            print("✅ No fallback IPCClient found in module scope")
            
    except Exception as e:
        print(f"❌ SyncMonitor import failed: {e}")
        return
    
    try:
        print("\n4. Testing SyncMonitor initialization...")
        
        # Minimal config that should work
        config = {
            'node': {'rpc_url': 'http://localhost:8545'},
            'ipc': {'socket_path': None, 'connection_timeout_seconds': 30, 'http_rpc_url': 'http://localhost:8545'},
            'networks': {
                'bsc': {
                    'name': 'BSC Mainnet', 
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
        
        monitor = SyncMonitor(config)
        print("✅ SyncMonitor initialization succeeded!")
        
        # Check what IPCClient class is being used
        ipc_class = type(monitor.ipc_client).__name__
        ipc_module = type(monitor.ipc_client).__module__
        print(f"📋 IPCClient class: {ipc_class} from {ipc_module}")
        
        # Check if it has the new signature
        import inspect
        sig = inspect.signature(type(monitor.ipc_client).__init__)
        print(f"📋 IPCClient.__init__ signature: {sig}")
        
    except Exception as e:
        print(f"❌ SyncMonitor initialization failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_issue()