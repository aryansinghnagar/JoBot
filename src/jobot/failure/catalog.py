import logging
import time
from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class FailureMode(str, Enum):
    # Category 1: Network & Protocol
    NETWORK_TIMEOUT = "FM_NET_001"
    DNS_RESOLUTION_FAILURE = "FM_NET_002"
    HTTP_500_SERVER_ERROR = "FM_NET_003"
    RATE_LIMIT_EXCEEDED = "FM_NET_004"

    # Category 2: Authentication & Session
    SESSION_EXPIRED = "FM_AUTH_001"
    MFA_CHALLENGE_REQUIRED = "FM_AUTH_002"
    CREDENTIALS_INVALID = "FM_AUTH_003"

    # Category 3: Anti-Bot & Stealth
    CAPTCHA_TRIGGERED = "FM_BOT_001"
    ACCOUNT_RESTRICTED = "FM_BOT_002"
    IP_BLOCKED = "FM_BOT_003"

    # Category 4: DOM & Form Drift
    SELECTOR_NOT_FOUND = "FM_DOM_001"
    FORM_STRUCTURE_CHANGED = "FM_DOM_002"
    UNEXPECTED_REQUIRED_FIELD = "FM_DOM_003"

    # Category 5: Grounding & AI
    GROUNDING_CHECK_FAILED = "FM_AI_001"
    LLM_TIMEOUT = "FM_AI_002"
    PROMPT_INJECTION_DETECTED = "FM_AI_003"
