# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Similar request detection utilities.
See instructions/architecture for development guidelines.
"""

import difflib
from app.models import FeatureRequest, Comment
from app.config import get_config_value

def calculate_levenshtein_similarity(str1: str, str2: str) -> float:
    """
    Calculate Levenshtein similarity between two strings.
    
    Args:
        str1: First string
        str2: Second string
    
    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not str1 or not str2:
        return 0.0
    
    return difflib.SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def calculate_jaccard_similarity(str1: str, str2: str) -> float:
    """
    Calculate Jaccard similarity between two strings.
    
    Args:
        str1: First string
        str2: Second string
    
    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not str1 or not str2:
        return 0.0
    
    set1 = set(str1.lower().split())
    set2 = set(str2.lower().split())
    
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    return intersection / union if union > 0 else 0.0

def keyword_match_score(request1: FeatureRequest, request2: FeatureRequest) -> float:
    """
    Calculate keyword matching score between two requests.
    
    Args:
        request1: First feature request
        request2: Second feature request
    
    Returns:
        Similarity score between 0.0 and 1.0
    """
    # Get keywords from titles and first comments
    keywords1 = set((request1.title + ' ' + get_first_comment_text(request1)).lower().split())
    keywords2 = set((request2.title + ' ' + get_first_comment_text(request2)).lower().split())
    
    # Remove common stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can'}
    keywords1 = keywords1 - stop_words
    keywords2 = keywords2 - stop_words
    
    if not keywords1 or not keywords2:
        return 0.0
    
    intersection = len(keywords1.intersection(keywords2))
    union = len(keywords1.union(keywords2))
    
    return intersection / union if union > 0 else 0.0

def get_first_comment_text(feature_request: FeatureRequest) -> str:
    """Get text from first comment of a feature request."""
    first_comment = Comment.query.filter_by(
        feature_request_id=feature_request.id,
        is_deleted=False
    ).order_by(Comment.date.asc()).first()
    
    return first_comment.comment if first_comment else ''

def find_similar_requests(title: str, description: str, app_id: int) -> list:
    """
    Find similar feature requests for the same app.
    
    Args:
        title: Title of the new request
        description: Description of the new request
        app_id: App ID
    
    Returns:
        List of (FeatureRequest, similarity_score) tuples, sorted by score descending
    """
    # Get all requests for the same app
    existing_requests = FeatureRequest.query.filter_by(app_id=app_id).all()
    
    if not existing_requests:
        return []
    
    threshold = get_config_value('similar_request_threshold', 0.6)
    max_results = get_config_value('similar_request_max_results', 5)
    
    similarities = []
    
    # Create a temporary FeatureRequest-like object for comparison
    # We'll use a simple dict-based approach since we only need title and description
    for req in existing_requests:
        # Calculate different similarity scores
        title_levenshtein = calculate_levenshtein_similarity(title, req.title)
        title_jaccard = calculate_jaccard_similarity(title, req.title)
        
        # For keyword matching, we need to compare the new request with existing one
        # Get keywords from new request
        new_keywords = set((title + ' ' + description).lower().split())
        # Get keywords from existing request
        req_description = get_first_comment_text(req)
        req_keywords = set((req.title + ' ' + req_description).lower().split())
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can'}
        new_keywords = new_keywords - stop_words
        req_keywords = req_keywords - stop_words
        
        if new_keywords and req_keywords:
            intersection = len(new_keywords.intersection(req_keywords))
            union = len(new_keywords.union(req_keywords))
            keyword_score = intersection / union if union > 0 else 0.0
        else:
            keyword_score = 0.0
        
        desc_levenshtein = calculate_levenshtein_similarity(description, req_description)
        
        # Weighted average
        combined_score = (
            title_levenshtein * 0.4 +
            title_jaccard * 0.2 +
            keyword_score * 0.2 +
            desc_levenshtein * 0.2
        )
        
        if combined_score >= threshold:
            similarities.append((req, combined_score))
    
    # Sort by score descending
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    # Return top results
    return similarities[:max_results]

