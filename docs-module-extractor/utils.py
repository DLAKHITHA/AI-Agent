import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import redis
from config import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CacheManager:
    """Manages caching of crawled content and analysis results."""
    
    def __init__(self):
        self.cache = None
        if config.CACHE_ENABLED and config.CACHE_REDIS_URL:
            try:
                self.cache = redis.Redis.from_url(
                    config.CACHE_REDIS_URL, 
                    decode_responses=True
                )
                logger.info("Redis cache initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis cache: {e}")
                self.cache = None
    
    def get_key(self, url: str, prefix: str = "crawl") -> str:
        """Generate a cache key for a URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return f"{prefix}:{url_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.cache:
            return None
        try:
            value = self.cache.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        if not self.cache:
            return False
        try:
            ttl = ttl or config.CACHE_TTL
            self.cache.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self.cache:
            return False
        try:
            self.cache.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

def normalize_url(url: str, base_url: Optional[str] = None) -> str:
    """Normalize URL by removing fragments and query parameters."""
    try:
        parsed = urlparse(url)
        # Remove fragments and query params for canonicalization
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        normalized = normalized.rstrip('/')
        
        # Make relative URLs absolute
        if base_url and not parsed.netloc:
            normalized = urljoin(base_url, url)
            
        return normalized
    except Exception as e:
        logger.error(f"URL normalization error: {e}")
        return url

def is_valid_url(url: str) -> bool:
    """Validate URL format and accessibility."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except:
        return False

def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except:
        return ""

def clean_text(text: str) -> str:
    """Clean and normalize text content."""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,;:!?()-]', ' ', text)
    
    # Trim and normalize
    text = text.strip()
    
    return text

def calculate_content_hash(content: str) -> str:
    """Calculate hash of content for change detection."""
    return hashlib.md5(content.encode()).hexdigest()

def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences for better processing."""
    # Simple sentence splitting (consider using nltk for better results)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def extract_headings_from_html(html: str) -> Dict[str, List[str]]:
    """Extract heading hierarchy from HTML."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        
        headings = {
            'h1': [],
            'h2': [],
            'h3': [],
            'h4': [],
            'h5': [],
            'h6': []
        }
        
        for level in headings.keys():
            elements = soup.find_all(level)
            headings[level] = [
                clean_text(el.get_text()) 
                for el in elements 
                if clean_text(el.get_text())
            ]
        
        return headings
    except Exception as e:
        logger.error(f"Heading extraction error: {e}")
        return {}

def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Merge two dictionaries, combining lists and sets."""
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result:
            if isinstance(result[key], list) and isinstance(value, list):
                result[key].extend(value)
            elif isinstance(result[key], set) and isinstance(value, set):
                result[key].update(value)
            elif isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge_dicts(result[key], value)
            else:
                result[key] = value
        else:
            result[key] = value
    
    return result

def chunk_content(content: str, chunk_size: int = 1000) -> List[str]:
    """Split content into manageable chunks for processing."""
    words = content.split()
    chunks = []
    
    current_chunk = []
    current_size = 0
    
    for word in words:
        current_chunk.append(word)
        current_size += len(word) + 1
        
        if current_size >= chunk_size:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_size = 0
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks