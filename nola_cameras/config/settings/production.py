"""
Production settings for New Orleans Camera Mapping project.
"""

import os

from .base import *  # noqa: F401, F403

DEBUG = False

# Detect whether we're serving over HTTPS.
# CADDY_SITE=http://x.x.x.x means bare-IP HTTP; anything else is a domain → HTTPS.
_caddy_site = os.environ.get("CADDY_SITE", "")
_using_https = not _caddy_site.startswith("http://")

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# HSTS only makes sense over HTTPS
SECURE_HSTS_SECONDS = 31536000 if _using_https else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = _using_https
SECURE_HSTS_PRELOAD = _using_https

# Secure-flag cookies require HTTPS; disable for bare-IP HTTP deployments
SESSION_COOKIE_SECURE = _using_https
CSRF_COOKIE_SECURE = _using_https

# Proxy settings (for Caddy)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
