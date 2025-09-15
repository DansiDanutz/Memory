#!/usr/bin/env python3
"""
JSON Logging Configuration Module
Provides structured JSON logging for the MemoApp Memory Bot
"""

import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_obj = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_obj['user_id'] = record.user_id
        if hasattr(record, 'tenant_id'):
            log_obj['tenant_id'] = record.tenant_id
        if hasattr(record, 'department_id'):
            log_obj['department_id'] = record.department_id
        if hasattr(record, 'action'):
            log_obj['action'] = record.action
        if hasattr(record, 'category'):
            log_obj['category'] = record.category
        if hasattr(record, 'memory_id'):
            log_obj['memory_id'] = record.memory_id
        if hasattr(record, 'request_id'):
            log_obj['request_id'] = record.request_id
        if hasattr(record, 'session_id'):
            log_obj['session_id'] = record.session_id
        
        # Add exception info if present
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        # Add any additional context
        if hasattr(record, 'context'):
            log_obj['context'] = record.context
            
        return json.dumps(log_obj, ensure_ascii=False)

def setup_json_logging(level=logging.INFO):
    """
    Configure JSON logging for the application
    
    Args:
        level: Logging level (default: INFO)
    """
    # Remove existing handlers
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    
    # Create console handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    
    # Configure root logger
    root.setLevel(level)
    root.addHandler(handler)
    
    # Configure specific loggers
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.error').setLevel(logging.INFO)
    
    return root

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with JSON formatting
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)

def log_with_context(logger: logging.Logger, level: str, message: str, **context):
    """
    Log a message with additional context
    
    Args:
        logger: Logger instance
        level: Log level (info, warning, error, etc.)
        message: Log message
        **context: Additional context to include in the log
    """
    extra = {}
    for key, value in context.items():
        extra[key] = value
    
    if level.lower() == 'info':
        logger.info(message, extra=extra)
    elif level.lower() == 'warning':
        logger.warning(message, extra=extra)
    elif level.lower() == 'error':
        logger.error(message, extra=extra)
    elif level.lower() == 'debug':
        logger.debug(message, extra=extra)
    elif level.lower() == 'critical':
        logger.critical(message, extra=extra)