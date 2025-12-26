import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    """Configuration settings for the documentation extractor."""
    
    # Crawler settings
    MAX_CRAWL_DEPTH: int = 3
    MAX_PAGES_PER_SITE: int = 50
    REQUEST_TIMEOUT: int = 30
    USER_AGENT: str = "Mozilla/5.0 (compatible; DocumentationExtractor/1.0)"
    
    # Parser settings
    MIN_CONTENT_LENGTH: int = 100
    CONTENT_TAGS: list = None
    IGNORE_SELECTORS: list = None
    
    # Analyzer settings
    MIN_MODULE_CONTENT_SIZE: int = 500
    SIMILARITY_THRESHOLD: float = 0.7
    MAX_SUBMODULES_PER_MODULE: int = 10
    
    # Cache settings
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 3600  # 1 hour
    CACHE_REDIS_URL: Optional[str] = None
    
    # LLM settings (optional)
    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4-turbo-preview"
    LLM_TEMPERATURE: float = 0.1
    
    def __post_init__(self):
        if self.CONTENT_TAGS is None:
            self.CONTENT_TAGS = ['article', 'main', 'section', 'div.content', 
                                'div.documentation', 'div.help-content']
        if self.IGNORE_SELECTORS is None:
            self.IGNORE_SELECTORS = ['nav', 'footer', 'header', 'aside', 
                                    '.sidebar', '.navigation', '.advertisement']

config = Config()

# Try to load environment variables
try:
    config.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    config.CACHE_REDIS_URL = os.getenv('REDIS_URL')
except:
    pass