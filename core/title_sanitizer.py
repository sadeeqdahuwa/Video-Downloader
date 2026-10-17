"""
Title Sanitizer Module
======================
Cleans raw media titles from yt-dlp, specifically solving:
  - Facebook reaction/view count prefixes (e.g. '1.5K views · 326 reactions _ ')
  - HTML entity escaping (e.g. &#039; -> ', &amp; -> &)
  - Windows illegal filename characters
  - Maximizing title character length (up to 200 chars)
"""

import html
import re


# Pattern that matches Facebook-style metric prefixes:
#   "1.5K views · 326 reactions _ "
#   "12M views | "
#   "500 reactions, 12 comments - "
_FB_METRICS_PREFIX = re.compile(
    r'^(?:'
    r'(?:\d+(?:[.,]\d+)?[KMBkmb]?\s*'
    r'(?:views?|reactions?|comments?|shares?|likes?|plays?|followers?)'
    r'\s*[\s·•|_\-,;:]*\s*)+'
    r')+',
    re.IGNORECASE,
)

# Pattern for Facebook/Watch branding wrappers
_FB_BRAND_PREFIX = re.compile(
    r'^(?:(?:Facebook|Watch|Reels?|Meta)\s*[|•·_\-–—]\s*)+',
    re.IGNORECASE,
)
_FB_BRAND_SUFFIX = re.compile(
    r'\s*[|•·_\-–—]\s*(?:Facebook|Watch|Reels?|Meta)\s*$',
    re.IGNORECASE,
)

# Windows illegal filename characters
_ILLEGAL_CHARS = re.compile(r'[<>"|?*]')


def sanitize_title(raw_title: str, max_chars: int = 200) -> str:
    """
    Clean a raw media title into a safe, human-readable filename stem.

    Args:
        raw_title: The raw title string from yt-dlp metadata.
        max_chars: Maximum allowed characters for the title (default 200,
                   leaving room for path prefix + extension on Windows).

    Returns:
        A cleaned title string safe for use as a filename on Windows/Linux/macOS.
    """
    if not raw_title or not raw_title.strip():
        return "downloaded_video"

    title = raw_title

    # Step 1: Unescape HTML entities
    #   &#039;  ->  '
    #   &amp;   ->  &
    #   &quot;  ->  "
    #   &#x27;  ->  '
    title = html.unescape(title)

    # Step 2: Strip Facebook metric prefixes
    title = _FB_METRICS_PREFIX.sub('', title)

    # Step 3: Strip Facebook/Watch brand wrappers
    title = _FB_BRAND_PREFIX.sub('', title)
    title = _FB_BRAND_SUFFIX.sub('', title)

    # Step 4: Normalize whitespace and underscores
    title = re.sub(r'[_\s]+', ' ', title)

    # Step 5: Strip leading/trailing delimiters and whitespace
    title = title.strip(' _·•|-–—:,;')

    # Step 6: Replace trailing dots (Windows strips them) with unicode ellipsis
    title = re.sub(r'\.{2,}', '…', title)

    # Step 7: Replace illegal Windows filename characters
    title = title.replace(':', ' -')
    title = title.replace('/', '-')
    title = title.replace('\\', '-')
    title = _ILLEGAL_CHARS.sub('', title)

    # Step 8: Collapse any double spaces created by replacements
    title = re.sub(r'  +', ' ', title).strip()

    # Step 9: Enforce maximum length
    if len(title) > max_chars:
        title = title[:max_chars].rstrip(' -_.,')

    # Step 10: Final strip of trailing dots/spaces (Windows safety)
    title = title.strip('. ')

    return title if title else "downloaded_video"
