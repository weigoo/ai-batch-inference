"""
Centralized configuration management for AI Batch Inference System
Supports environment variable overrides for dev/staging/prod environments
"""

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    """Configuration dataclass with environment variable support"""
    
    # Redis Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
    #handle k8s autoservice discovery return port as tcp://<Cluster-IP>:<Port>
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379").rsplit(":", 1)[-1])
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_SSL: bool = os.getenv("REDIS_SSL", "False").lower() == "true"
    
    # Model Configuration
    MODEL_NAME: str = os.getenv(
        "MODEL_NAME",
        "distilbert-base-uncased-finetuned-sst-2-english"
    )
    MODEL_DEVICE: str = os.getenv("MODEL_DEVICE", "cpu")
    
    # Inference Configuration
    INFERENCE_TIMEOUT: int = int(os.getenv("INFERENCE_TIMEOUT", "300"))
    MAX_BATCH_SIZE: int = int(os.getenv("MAX_BATCH_SIZE", "1000"))
    MAX_TEXT_LENGTH: int = int(os.getenv("MAX_TEXT_LENGTH", "5000"))
    
    # Worker Configuration
    WORKER_POLLING_INTERVAL: int = int(os.getenv("WORKER_POLLING_INTERVAL", "2"))
    WORKER_MAX_RETRIES: int = int(os.getenv("WORKER_MAX_RETRIES", "3"))
    WORKER_RETRY_BACKOFF: float = float(os.getenv("WORKER_RETRY_BACKOFF", "2.0"))
    
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Storage Configuration (TTL in seconds, default 30 days)
    RESULT_TTL: int = int(os.getenv("RESULT_TTL", "2592000"))
    STATUS_TTL: int = int(os.getenv("STATUS_TTL", "2592000"))
    
    # Security Configuration
    ALLOWED_ORIGINS: list = field(default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "localhost").split(","))
    ENABLE_RATE_LIMITING: bool = os.getenv("ENABLE_RATE_LIMITING", "True").lower() == "true"
    RATE_LIMIT: str = os.getenv("RATE_LIMIT", "100/minute")
    

# Global config instance
config = Config()
