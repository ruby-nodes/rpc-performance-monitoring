"""
Logging setup and utilities.
"""

import os
import json
import logging
import logging.config
import yaml
from pathlib import Path
from typing import Dict, Any


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process', 'getMessage',
                          'message']:
                log_entry[key] = value
        
        return json.dumps(log_entry)


def setup_logging(config_path: str = None) -> None:
    """
    Setup logging configuration from YAML file.
    
    Args:
        config_path: Path to logging configuration file
    """
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(__file__), "../../config/logging.yaml"
        )
    
    config_path = Path(config_path).resolve()
    
    if not config_path.exists():
        # Fallback to basic logging if config file doesn't exist
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        logging.warning(f"Logging config not found at {config_path}, using basic config")
        return
    
    try:
        with open(config_path, 'r') as f:
            log_config = yaml.safe_load(f)
        
        # Ensure log directories exist
        _create_log_directories(log_config)
        
        # Configure logging
        logging.config.dictConfig(log_config)
        
        # Test logging setup
        logger = logging.getLogger(__name__)
        logger.info("Logging system initialized successfully")
        
    except Exception as e:
        # Fallback to basic logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        logging.error(f"Failed to setup logging configuration: {e}")


def _create_log_directories(log_config: Dict[str, Any]) -> None:
    """Create log directories from logging configuration."""
    handlers = log_config.get('handlers', {})
    
    for handler_name, handler_config in handlers.items():
        if 'filename' in handler_config:
            log_file = Path(handler_config['filename'])
            log_file.parent.mkdir(parents=True, exist_ok=True)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)