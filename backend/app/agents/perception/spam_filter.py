"""Spam detection module for email filtering"""
from typing import Dict, Any
import re
from app.utils.monitoring import StructuredLogger


def extract_sender_domain(sender: str) -> str:
    """
    Extract domain from sender email address
    
    Args:
        sender: Sender string in format "Name <email@domain.com>" or "email@domain.com"
        
    Returns:
        Domain string (e.g., "petsmart.com") or empty string if not found
    """
    if not sender:
        return ""
    
    # Extract email from "Name <email@domain.com>" format
    if "<" in sender and ">" in sender:
        match = re.search(r'<([^>]+)>', sender)
        if match:
            email = match.group(1)
        else:
            email = sender
    else:
        email = sender.strip()
    
    # Extract domain from email
    if "@" in email:
        domain = email.split("@")[1].lower()
        return domain
    
    return ""


def is_promotional_domain(domain: str) -> bool:
    """
    Check if domain matches known promotional domain patterns
    
    Args:
        domain: Domain string to check
        
    Returns:
        True if domain matches promotional patterns, False otherwise
    """
    if not domain:
        return False
    
    domain_lower = domain.lower()
    
    # Common promotional domain patterns (checking subdomain prefixes)
    promotional_patterns = [
        r'^mail\.',  # mail.petsmart.com, mail.company.com
        r'^email-',  # email-totalwine.com, email-company.com
        r'^email\.',  # email.company.com
        r'^noreply\.',  # noreply.company.com
        r'^no-reply\.',  # no-reply.company.com
        r'^marketing\.',  # marketing.company.com
        r'^newsletter\.',  # newsletter.company.com
        r'^promo\.',  # promo.company.com
        r'^promotions\.',  # promotions.company.com
        r'^offers\.',  # offers.company.com
        r'^deals\.',  # deals.company.com
        r'^notifications\.',  # notifications.company.com
        r'^updates\.',  # updates.company.com
        r'^alerts\.',  # alerts.company.com
        r'^info\d+\.',  # info15.citi.com, info1.company.com
        r'^info-',  # info-company.com
        r'^store-',  # store-news@amazon.com (checking subdomain)
        r'^store\.',  # store.company.com
        r'^shop\.',  # shop.company.com
        r'^sales\.',  # sales.company.com
        r'^news\.',  # news.company.com
        r'^e-?mail',  # email.company.com or e-mail.company.com
    ]
    
    for pattern in promotional_patterns:
        if re.search(pattern, domain_lower):
            return True
    
    return False


def has_promotional_content(subject: str, body: str) -> bool:
    """
    Check if email subject/body contains promotional content indicators
    
    Args:
        subject: Email subject line
        body: Email body text
        
    Returns:
        True if promotional content detected, False otherwise
    """
    if not subject and not body:
        return False
    
    subject_lower = (subject or "").lower()
    body_lower = (body or "").lower()
    combined_text = f"{subject_lower} {body_lower}"
    
    # Promotional keywords (expanded list)
    # Note: Single words like "marketing", "deal", "offer" are too broad and cause false positives
    # Use phrases instead for better accuracy
    promotional_keywords = [
        'unsubscribe',
        'opt-out',
        'opt out',
        'manage preferences',
        'view in browser',
        'special offer',
        'limited time',
        'limited-time',
        'limited time offer',
        'act now',
        'activate your',
        'activate now',
        'activate the',
        'click here',
        'shop now',
        'buy now',
        'sale',
        'discount',
        'coupon',
        'promo code',
        'promotional',
        'newsletter',
        'marketing email',  # More specific - avoid false positives
        'marketing campaign',
        'advertisement',
        'advert',
        'earn back',
        'statement credits',
        'rewards',
        'checkout',
        'snag your',
        'consider purchasing',
        'product review',
        'lifetime membership',
        'percent off',
        '% off',
        'discount code',
        'promo',
        'exclusive offer',
        'don\'t miss',
        'hurry',
        'expires',
        'ending soon',
        'last chance',
    ]
    
    # Check for promotional keywords
    for keyword in promotional_keywords:
        if keyword in combined_text:
            return True
    
    # Check for standalone promotional words only in specific contexts
    # These words alone are too broad, but in certain phrases they indicate spam
    standalone_promotional_words = {
        'deal': ['special deal', 'great deal', 'amazing deal', 'deal of', 'deal ends'],
        'deals': ['special deals', 'great deals', 'amazing deals', 'deals on'],
        'offer': ['special offer', 'limited offer', 'exclusive offer', 'offer ends', 'offer expires'],
        'offers': ['special offers', 'limited offers', 'exclusive offers'],
        'purchase': ['purchase now', 'purchase your', 'purchase the'],
        'buy': ['buy now', 'buy your', 'buy the', 'buy today'],
        'shop': ['shop now', 'shop today', 'shop our'],
        'earn': ['earn back', 'earn rewards', 'earn points', 'earn cash'],
    }
    
    for word, contexts in standalone_promotional_words.items():
        if word in combined_text:
            # Check if word appears in a promotional context
            for context in contexts:
                if context in combined_text:
                    return True
    
    # Check for unsubscribe links (common pattern)
    unsubscribe_patterns = [
        r'unsubscribe',
        r'opt.?out',
        r'manage.?preferences',
        r'preferences',
    ]
    
    for pattern in unsubscribe_patterns:
        if re.search(pattern, combined_text, re.IGNORECASE):
            return True
    
    return False


def detect_spam(email_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect if email is spam/promotional using multiple detection methods
    
    Args:
        email_data: Email message dictionary with keys:
            - sender: Sender email address
            - subject: Email subject
            - body_text: Email body text
            - labels: List of Gmail labels
            
    Returns:
        Dictionary with:
            - is_spam: bool - Whether email is spam/promotional
            - spam_reason: str - Reason for spam detection
            - spam_score: float - Confidence score (0.0-1.0)
    """
    sender = email_data.get("sender", "")
    subject = email_data.get("subject", "")
    body_text = email_data.get("body_text", "")
    labels = email_data.get("labels", [])
    
    spam_score = 0.0
    spam_reasons = []
    
    # Check Gmail labels (highest confidence)
    if "SPAM" in labels:
        spam_score = 1.0
        spam_reasons.append("Gmail SPAM label")
    elif "CATEGORY_PROMOTIONS" in labels:
        spam_score = 0.9
        spam_reasons.append("Gmail CATEGORY_PROMOTIONS label")
    elif "CATEGORY_UPDATES" in labels:
        # Updates category is less spammy, but often promotional
        spam_score = 0.3
        spam_reasons.append("Gmail CATEGORY_UPDATES label")
    
    # Check sender domain patterns and email address patterns
    domain = extract_sender_domain(sender)
    
    # Check if domain matches promotional patterns
    if domain and is_promotional_domain(domain):
        domain_score = 0.8
        if spam_score < domain_score:
            spam_score = domain_score
        spam_reasons.append(f"Promotional domain pattern: {domain}")
    
    # Also check the full email address for promotional patterns
    # Extract full email address from sender string
    full_email = ""
    if "<" in sender and ">" in sender:
        match = re.search(r'<([^>]+)>', sender)
        if match:
            full_email = match.group(1).lower()
    else:
        full_email = sender.lower()
    
    # Check if email address contains promotional subdomain patterns
    if full_email and "@" in full_email:
        email_local = full_email.split("@")[0]
        # Check for promotional patterns in email address (e.g., store-news@amazon.com)
        email_promotional_patterns = [
            r'^store-',
            r'^news-',
            r'^email-',
            r'^info\d+',
            r'^marketing',
            r'^promo',
            r'^sales',
            r'^shop',
        ]
        for pattern in email_promotional_patterns:
            if re.search(pattern, email_local):
                email_score = 0.75
                if spam_score < email_score:
                    spam_score = email_score
                spam_reasons.append(f"Promotional email address pattern: {full_email}")
                break
    
    # Check promotional content
    if has_promotional_content(subject, body_text):
        content_score = 0.8  # Increased score for content detection
        if spam_score < content_score:
            spam_score = content_score
        spam_reasons.append("Promotional content detected")
    
    # Additional check: if subject contains common promotional phrases, boost score
    subject_lower = (subject or "").lower()
    strong_promotional_phrases = [
        ('activate your', 0.85),
        ('activate now', 0.85),
        ('activate the', 0.85),
        ('limited-time offer', 0.9),
        ('limited time offer', 0.9),
        ('consider purchasing', 0.8),
        ('snag your', 0.8),
        ('earn back', 0.8),
        ('statement credits', 0.8),
        ('percent off', 0.75),
        ('% off', 0.75),
        ('lifetime membership', 0.8),
        ('art in action', 0.7),  # Specific promotional event pattern
    ]
    
    # Check for "review the" but only if followed by a long product name (promotional)
    # Legitimate reviews usually have short subjects like "Review the proposal"
    if 'review the' in subject_lower:
        # If subject is very long (>60 chars) and contains product-like words, it's likely promotional
        if len(subject) > 60 and any(word in subject_lower for word in ['product', 'dry', 'food', 'protein', 'high', 'stages']):
            phrase_score = 0.8
            if spam_score < phrase_score:
                spam_score = phrase_score
            spam_reasons.append("Promotional product review email detected")
    
    # Check other strong promotional phrases
    for phrase, score in strong_promotional_phrases:
        if phrase in subject_lower:
            if spam_score < score:
                spam_score = score
            spam_reasons.append(f"Promotional phrase in subject: '{phrase}'")
            break  # Only add one reason per email
    
    # Determine if spam based on score threshold (lowered to catch more)
    is_spam = spam_score >= 0.4  # Lowered from 0.5 to be more aggressive
    
    # Combine reasons
    spam_reason = "; ".join(spam_reasons) if spam_reasons else None
    
    return {
        "is_spam": is_spam,
        "spam_reason": spam_reason,
        "spam_score": spam_score,
    }

