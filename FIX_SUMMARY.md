## Fix for IPCClient Initialization Error

### Error
```
IPCClient.__init__() got an unexpected keyword argument 'ipc_path'
```

### Root Cause
The fallback IPCClient class in `src/monitoring/sync_monitor.py` had the old signature that expected a single `config` parameter, but the code was updated to pass keyword arguments.

### Solution Applied
Updated the fallback IPCClient class signature in `src/monitoring/sync_monitor.py` from:
```python
def __init__(self, config): pass
```

To:
```python
def __init__(self, ipc_path=None, timeout=30, http_rpc_url=None): pass
```

### Files Modified
1. `src/core/ipc_client.py` - Added HTTP RPC fallback support with graceful aiohttp handling
2. `src/monitoring/sync_monitor.py` - Updated fallback IPCClient class signature

### To Apply Fix on Remote Node

1. **Pull latest changes:**
   ```bash
   git pull origin main
   ```

2. **Clear Python cache (if needed):**
   ```bash
   find . -name "*.pyc" -delete
   find . -name "__pycache__" -type d -exec rm -rf {} +
   ```

3. **Verify the fix:**
   ```bash
   source .venv/bin/activate
   python3 diagnose_remote.py
   ```

4. **Test the main application:**
   ```bash
   source .venv/bin/activate
   timeout 10s python3 main.py
   ```

### Expected Behavior After Fix
- ✅ No more IPCClient initialization errors
- ✅ Automatic fallback to HTTP RPC when IPC socket not available 
- ✅ Proper error messages if neither IPC nor HTTP RPC is available
- ✅ Graceful shutdown with Ctrl+C

### Verification
The diagnostic script should show:
```
✅ Core IPCClient accepts new signature
✅ SyncMonitor initialization succeeded!
📋 IPCClient.__init__ signature: (self, ipc_path=None, timeout=30, http_rpc_url=None)
```