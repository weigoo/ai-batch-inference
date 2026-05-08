"""
Model loading and inference service
Handles DistilBERT sentiment analysis with caching and error handling
"""

import logging
from functools import lru_cache

from transformers import pipeline

from .config import config

logger = logging.getLogger(__name__)


class ModelError(Exception):
    """Custom exception for model-related errors"""
    pass


@lru_cache(maxsize=1)
def get_model():
    """
    Load and cache sentiment analysis model
    Uses lru_cache to ensure model is loaded only once
    
    Returns:
        Hugging Face pipeline object
        
    Raises:
        ModelError: If model loading fails
    """
    try:
        logger.info("Loading sentiment analysis model: %s", config.MODEL_NAME)
        
        classifier = pipeline(
            "sentiment-analysis",
            model=config.MODEL_NAME,
            device=-1 if config.MODEL_DEVICE == "cpu" else 0
        )
        
        logger.info("Model loaded successfully")
        return classifier
        
    except Exception as e:
        logger.error("Failed to load model: %s", e, exc_info=True)
        raise ModelError(f"Model initialization failed: {e}") from e


def run_inference(texts):
    """
    Run sentiment analysis inference on texts
    
    Args:
        texts: List of text strings to analyze
        
    Returns:
        List of sentiment predictions with labels and scores
        
    Raises:
        ValueError: If texts is empty
        ModelError: If inference fails
    """
    if not texts:
        raise ValueError("texts cannot be empty")
    
    if not isinstance(texts, list):
        raise ValueError("texts must be a list")
    
    # Validate text items
    for i, text in enumerate(texts):
        if not isinstance(text, str):
            raise ValueError(f"texts[{i}] must be a string, got {type(text)}")
        if not text:
            raise ValueError(f"texts[{i}] cannot be empty")
        if len(text) > config.MAX_TEXT_LENGTH:
            raise ValueError(
                f"texts[{i}] exceeds max length {config.MAX_TEXT_LENGTH}"
            )
    
    try:
        logger.info("Running inference on %d texts", len(texts))
        model = get_model()
        results = model(texts)
        logger.info("Inference completed successfully")
        return results
        
    except ModelError:
        raise
    except Exception as e:
        logger.exception("Inference failed: %s", e)
        raise ModelError(f"Inference failed: {e}") from e
