"""
Configuration management utilities.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config file. If None, uses default.
        
    Returns:
        Configuration dictionary
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid
    """
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), "../../config/config.yaml")
    
    config_path = Path(config_path).resolve()
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Validate required sections
        required_sections = ['node', 'monitoring', 'prometheus', 'correlation', 'storage', 'logging']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required config section: {section}")
        
        # Set default values and resolve paths
        config = _apply_defaults(config)
        config = _resolve_paths(config)
        
        return config
        
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML configuration: {e}")


def load_prometheus_metrics_config() -> Dict[str, Any]:
    """Load Prometheus metrics configuration."""
    metrics_config_path = os.path.join(
        os.path.dirname(__file__), "../../config/prometheus_metrics.yaml"
    )
    
    with open(metrics_config_path, 'r') as f:
        return yaml.safe_load(f)


def _apply_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply default values to configuration."""
    # Node defaults
    if 'auto_detect' not in config['node']:
        config['node']['auto_detect'] = True
    
    # Create data directory if it doesn't exist
    data_dir = Path(config['storage']['database_path']).parent
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create log directories
    log_dir = Path(config['logging']['logs_directory'])
    log_dir.mkdir(parents=True, exist_ok=True)
    
    for subdir in ['desyncs', 'analysis', 'metrics', 'system']:
        (log_dir / subdir).mkdir(parents=True, exist_ok=True)
    
    return config


def _resolve_paths(config: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve relative paths in configuration."""
    # Resolve database path
    if not os.path.isabs(config['storage']['database_path']):
        config['storage']['database_path'] = os.path.abspath(
            config['storage']['database_path']
        )
    
    # Resolve log directory path  
    if not os.path.isabs(config['logging']['logs_directory']):
        config['logging']['logs_directory'] = os.path.abspath(
            config['logging']['logs_directory']
        )
    
    return config


def get_network_config(config: Dict[str, Any], network_name: str) -> Dict[str, Any]:
    """
    Get configuration for specific network.
    
    Args:
        config: Main configuration dictionary
        network_name: Network name (bsc, base)
        
    Returns:
        Network-specific configuration
    """
    if network_name not in config['node']['networks']:
        raise ValueError(f"Unknown network: {network_name}")
    
    return config['node']['networks'][network_name]


def detect_network_from_ipc(ipc_path: str) -> str:
    """
    Detect network type from IPC path.
    
    Args:
        ipc_path: Path to IPC socket
        
    Returns:
        Network name (bsc, base)
    """
    ipc_path = ipc_path.lower()
    
    if 'bsc' in ipc_path or 'geth.ipc' in ipc_path:
        return 'bsc'
    elif 'reth.ipc' in ipc_path or 'tmp' in ipc_path:
        return 'base'
    else:
        # Default to BSC if can't determine
        return 'bsc'