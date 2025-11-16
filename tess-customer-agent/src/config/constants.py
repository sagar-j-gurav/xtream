"""
TESS Constants
Application-wide constants and configuration values
"""

# Agent Personality
AGENT_NAME = "TESS"
AGENT_FULL_NAME = "Technical Expert Support System"

# Message Roles
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_SYSTEM = "system"

# Topic Categories
TOPIC_PRODUCT_INQUIRY = "product_inquiry"
TOPIC_LEAD_MANAGEMENT = "lead_management"
TOPIC_GENERAL_SUPPORT = "general_support"
TOPIC_OFF_TOPIC = "off_topic"

# Tool Names
TOOL_CHROMADB = "search_knowledge_base"
TOOL_MCP_PREFIX = "frappe_"  # MCP tools will be auto-discovered with this prefix

# Response Templates
OFF_TOPIC_RESPONSE = (
    "I'm here to help with questions about our products and services. "
    "How can I assist you today?"
)

GREETING_TEMPLATES = [
    "Hi there! I'm TESS, here to help with any questions about our services. What can I do for you today?",
    "Hello! How can I assist you today?",
    "Welcome! I'm TESS, your technical support assistant. How may I help you?",
]

# ChromaDB Constants
EMBEDDING_DIMENSION = 1536  # for text-embedding-3-small
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100

# Lead Fields
LEAD_REQUIRED_FIELDS = ["full_name", "email"]
LEAD_OPTIONAL_FIELDS = ["phone", "company", "inquiry_type", "message"]

# Session Management
SESSION_ID_LENGTH = 32
ANONYMOUS_USER_PREFIX = "anon_"

# Retry Configuration
DEFAULT_RETRY_ATTEMPTS = 3
RETRY_MIN_WAIT = 2  # seconds
RETRY_MAX_WAIT = 10  # seconds

# API Configuration
API_V1_PREFIX = "/api/v1"
HEALTH_CHECK_PATH = "/api/v1/health"

# Logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
