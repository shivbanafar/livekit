"""
Text normalization and tokenization utilities.
"""

import re
from typing import List, Set, Optional


def normalize_text(text: str) -> str:
    """
    Normalize text: lowercase, strip punctuation, trim whitespace.
    
    Args:
        text: Raw transcription text
        
    Returns:
        Normalized text string
    """
    if not text:
        return ""
    # Convert to lowercase
    text = text.lower()
    # Remove extra whitespace
    text = " ".join(text.split())
    return text.strip()


def tokenize(text: str) -> List[str]:
    """
    Tokenize text by splitting on whitespace and punctuation.
    Removes empty tokens.
    
    Args:
        text: Input text to tokenize
        
    Returns:
        List of tokens
    """
    if not text:
        return []
    
    normalized = normalize_text(text)
    # Split on whitespace and common punctuation
    tokens = re.split(r'[\s\.,!?;:]+', normalized)
    # Filter out empty strings
    return [t for t in tokens if t]


def is_filler_only(tokens: List[str], ignored_words: Set[str], stopwords: Optional[Set[str]] = None) -> bool:
    """
    Check if tokens contain only filler words and stopwords.
    
    Args:
        tokens: List of tokenized words
        ignored_words: Set of filler words to ignore
        stopwords: Optional set of common stopwords (e.g., 'the', 'a', 'an')
        
    Returns:
        True if all meaningful tokens are fillers/stopwords
    """
    if not tokens:
        return True
    
    if stopwords is None:
        stopwords = set()
    
    # Check each token
    for token in tokens:
        # Skip if it's a filler word or stopword
        if token in ignored_words or token in stopwords:
            continue
        # If we find any meaningful token, it's not filler-only
        if len(token) > 0:
            return False
    
    return True


def contains_any_token(tokens: List[str], target_set: Set[str]) -> bool:
    """
    Check if any token in the list matches any string in target_set.
    Uses substring matching for phrase detection.
    
    Args:
        tokens: List of tokenized words
        target_set: Set of target strings to match
        
    Returns:
        True if any token or phrase matches
    """
    if not tokens or not target_set:
        return False
    
    # Create a normalized text string for phrase matching
    text = " ".join(tokens).lower()
    
    # Check each target string
    for target in target_set:
        target_lower = target.lower().strip()
        # Exact token match
        if target_lower in tokens:
            return True
        # Substring match for phrases (e.g., "not that" in "umm not that one")
        if target_lower in text:
            return True
    
    return False

