#!/usr/bin/env python3
"""
Live status dashboard for the monitoring application
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

async def monitor_status():
    """Show live status of the monitoring system."""
    
    print("📊 Ethereum Node Monitor - Live Status Dashboard")
    print("=" * 60)
    print("Press Ctrl+C to exit")
    print()
    
    try:
        from utils.config import load_config
        from core.ipc_client import IPCClient
        
        # Load config
        config = load_config()
        
        # Get connection details
        ipc_path = (
            config.get('networks', {}).get('bsc', {}).get('ipc_path') or
            config.get('node', {}).get('ipc_path')
        )
        http_rpc_url = config.get('node', {}).get('rpc_url', 'http://localhost:8545')
        
        # Create IPC client
        client = IPCClient(ipc_path=ipc_path, http_rpc_url=http_rpc_url)
        
        iteration = 0
        while True:
            iteration += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            print(f"\r🕐 {timestamp} | Check #{iteration}", end="")
            
            try:
                # Test connection
                version_response = await client.get_client_version()
                
                if version_response.success:
                    print(f" | ✅ Connected: {version_response.data[:50]}...")
                    
                    # Get sync status
                    sync_status = await client.get_sync_status()
                    if sync_status:
                        syncing_status = "🔄 Syncing" if sync_status.is_syncing else "✅ Synced"
                        print(f" | {syncing_status} | Block: {sync_status.current_block:,}")
                    else:
                        print(" | ❓ No sync status")
                else:
                    print(f" | ❌ Connection failed: {version_response.error[:30]}...")
                    
            except Exception as e:
                print(f" | 💥 Error: {str(e)[:30]}...")
            
            await asyncio.sleep(5)  # Update every 5 seconds
            
    except KeyboardInterrupt:
        print(f"\n\n👋 Status monitoring stopped.")
    except Exception as e:
        print(f"\n❌ Status monitor error: {e}")

if __name__ == "__main__":
    asyncio.run(monitor_status())