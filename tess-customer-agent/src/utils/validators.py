"""
Validation Utilities for TESS
Input validation and sanitization
"""
import re
from typing import Optional, Dict, Any
from email_validator import validate_email, EmailNotValidError


def is_valid_email(email: str) -> bool:
    """
    Validate email address

    Args:
        email: Email address to validate

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def is_valid_phone(phone: str) -> bool:
    """
    Validate phone number (basic validation)

    Args:
        phone: Phone number to validate

    Returns:
        bool: True if valid, False otherwise
    """
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)

    # Check if it's a valid phone number (10-15 digits, optional + prefix)
    pattern = r'^\+?\d{10,15}$'
    return bool(re.match(pattern, cleaned))


def sanitize_string(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input string

    Args:
        text: Input text
        max_length: Maximum allowed length

    Returns:
        str: Sanitized text
    """
    # Remove null bytes
    text = text.replace('\x00', '')

    # Trim whitespace
    text = text.strip()

    # Limit length
    if len(text) > max_length:
        text = text[:max_length]

    return text


def validate_lead_data(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate lead data before submission

    Args:
        data: Lead data dictionary

    Returns:
        tuple: (is_valid, error_message)
    """
    # Check required fields
    if not data.get('full_name'):
        return False, "Full name is required"

    if not data.get('email'):
        return False, "Email is required"

    # Validate email
    if not is_valid_email(data['email']):
        return False, "Invalid email address"

    # Validate phone if provided
    if data.get('phone') and not is_valid_phone(data['phone']):
        return False, "Invalid phone number"

    # Validate name length
    if len(data['full_name']) < 2:
        return False, "Full name must be at least 2 characters"

    if len(data['full_name']) > 100:
        return False, "Full name must be less than 100 characters"

    return True, None


def generate_session_id() -> str:
    """
    Generate a unique session ID

    Returns:
        str: Session ID
    """
    import uuid
    return str(uuid.uuid4())


def is_valid_session_id(session_id: str) -> bool:
    """
    Validate session ID format

    Args:
        session_id: Session ID to validate

    Returns:
        bool: True if valid, False otherwise
    """
    # Check if empty
    if not session_id or not session_id.strip():
        return False

    # Check length
    if len(session_id) > 128:
        return False

    # Check if it's a valid UUID
    try:
        import uuid
        uuid.UUID(session_id)
        return True
    except (ValueError, AttributeError):
        # Also accept alphanumeric strings with underscores, hyphens, and dots
        return bool(re.match(r'^[a-zA-Z0-9_.-]+$', session_id))
