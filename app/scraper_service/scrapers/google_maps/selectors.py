"""
Google Maps CSS/attribute selectors with comprehensive fallback lists.
Google Maps frequently changes DOM structure, so we maintain ordered fallback
lists for each field to maximize extraction reliability.
"""

FEED_CONTAINER = '[role="feed"]'

CARD_SELECTORS = [
    "div.Nv2PK",
    'div[role="article"]',
    'a[href*="maps/place/"]',
    'div[jsaction*="mouseover.card"]',
    'div[data-value="CgI"]',
]

DETAIL_COMPANY_NAME = [
    "h1", 
    "h1.DUwDvf", 
    'h1[itemprop="name"]',
    ".x3AX1-LfntMc-header-title-title",
    ".SPZz6b h1",
    "[data-attrid='title'] h1",
    ".qrShPb .fontHeadlineLarge",
]

DETAIL_CATEGORY = [
    "button.DKv0N",
    'button[jsaction*="category"]',
    'button[aria-label*="Category"]',
    'span[jsaction*="category"]',
    ".DkEaL",
    ".YhemCb",
    "[data-attrid='kc:/collection/knowledge_panels/local_business:type'] span",
    ".fontBodyMedium button[jsaction]",
    "button.fontBodyMedium",
]

DETAIL_PHONE = [
    'button[data-item-id*="phone"]',
    'a[data-item-id*="phone"]',
    'button[aria-label*="phone"]',
    'button[aria-label*="Phone"]',
    'button[aria-label*="Call"]',
    'a[href^="tel:"]',
    'button[data-item-id$="phone"]',
    '[data-attrid="kc:/collection/knowledge_panels/local_business:phone"] button',
    '.AeaXub a[href^="tel:"]',
    'button[jsaction*="phone"]',
    'span[dir="ltr"] a[href^="tel:"]',
]

DETAIL_ADDRESS = [
    'button[data-item-id*="address"]',
    'button[aria-label*="Address"]',
    'button[aria-label*="address"]',
    'button[data-item-id$="address"]',
    'div[data-item-id*="address"]',
    '[data-attrid*="kc:/location"] button',
    '.AeaXub button[jsaction*="address"]',
    'button[jsaction*="directions"]',
    '[data-value*="directions"] button',
    'div[role="button"][aria-label*="Address"]',
]

DETAIL_WEBSITE = [
    'a[data-item-id*="website"]',
    'a[data-item-id*="authority"]',
    'a[aria-label*="website"]',
    'a[aria-label*="Website"]',
    'a[aria-label*="Web page"]',
    'a[data-item-id$="website"]',
    'a[data-item-id$="authority"]',
    'a[href^="https://www.google.com/url"][href*="q="]',
    '.AeaXub a[href*="www.google.com/url"]',
    'a[ping*="website"]',
    'a[jsaction*="website"]',
]

DETAIL_PANEL_SCROLL = '[role="dialog"], div[role="main"], div.m6QErb'

DETAIL_RATING = [
    'span[role="img"][aria-label*="stars"]',
    'span[aria-label*="star"]',
    'div[aria-label*="stars"]',
    '[data-attrid*="kc:/collection/knowledge_panels/local_business:star_score"] span[aria-label]',
    '.fontDisplayLarge[aria-label*="stars"]',
    'span[jsaction*="rating"]',
    '.ceNzKf[aria-label*="star"]',
]

# Business status (Open/Closed)
DETAIL_BUSINESS_STATUS = [
    'span[aria-label*="Open"]',
    'span[aria-label*="Closed"]',
    'span[aria-label*="Closes"]',
    'span[aria-label*="Opens"]',
    '.OqCZI span',
    '.ZDu9vd span',
    '[data-attrid*="hours"] span',
    '.o0Svhf span',
    '.fontBodyMedium span[jsaction*="hours"]',
    'div[jsaction*="hours"] span',
]

# Working hours
DETAIL_WORKING_HOURS = [
    'table[aria-label*="Hours"]',
    'div[aria-label*="Hours"]', 
    '.t39EBf',
    '.eK4R0e',
    '[data-value*="OpeningHours"]',
    '[data-attrid*="hours"] table',
    '.OqCZI table',
    'div[role="table"]',
    'table.WgFkxc',
    '.fontBodyMedium table',
]

# Plus Code
DETAIL_PLUS_CODE = [
    'button[data-item-id*="oloc"]',
    'button[aria-label*="Plus code"]',
    'button[aria-label*="plus code"]',
    'div[data-value*="plus_code"]',
    '[data-attrid*="plus_code"] button',
    'button[jsaction*="oloc"]',
    'span[data-value*="oloc"]',
]

# Owner claimed / verification badge
DETAIL_OWNER_CLAIMED = [
    'span[aria-label*="Claimed"]',
    'span[aria-label*="Verified"]',
    '.RZ66Rb span',
    'button[aria-label*="Claim this business"]',
    '[data-attrid*="claimed"] span',
    '.fontBodySmall[aria-label*="Verified"]',
    'div[jsaction*="claim"]',
]

# Total photos count
DETAIL_TOTAL_PHOTOS = [
    'button[aria-label*="photos"]',
    'button[aria-label*="Photos"]',
    'button[data-item-id*="photos"]',
    '.Gpq6kf .fontTitleSmall',
    '[data-attrid*="photos"] button',
    'button[jsaction*="photos"]',
    'div[role="button"][aria-label*="photo"]',
    '.RWPxGd button[aria-label*="photo"]',
]

# Service options (delivery, takeout, etc.)
DETAIL_SERVICE_OPTIONS = [
    'div[aria-label*="Service options"]',
    'div[aria-label*="Highlights"]',
    '.AeaXub',
    '.RWPxGd',
    '[data-attrid*="service"] div',
    '.fontBodyMedium[aria-label*="Service"]',
    'div[jsaction*="service"]',
    '.ceNzKf[aria-label*="option"]',
]

# Common text patterns for fallback extraction
RATING_PATTERNS = [
    r'(\d+\.?\d*)\s*stars?',
    r'(\d+\.?\d*)/5',
    r'Rating:\s*(\d+\.?\d*)',
    r'(\d+\.?\d*)\s*★',
]

PHONE_PATTERNS = [
    r'\+?[\d\s\-\(\)\.]{10,}',
    r'tel:[\+\d\-\(\)\.]+',
    r'Call\s+([\d\s\-\(\)\.]+)',
    r'Phone:\s*([\d\s\-\(\)\.]+)',
]

REVIEWS_PATTERNS = [
    r'([\d,]+)\s*reviews?',
    r'([\d,]+)\s*ratings?',
    r'(\d+)\s*Google\s*reviews?',
]

BUSINESS_STATUS_PATTERNS = [
    r'\b(Open|Closed|Opens|Closes)\b.*?\b(\d{1,2}:\d{2}|\d{1,2}\s*[AP]M)',
    r'(Temporarily closed)',
    r'(Permanently closed)',
    r'(Open 24 hours)',
]

PLUS_CODE_PATTERN = r'([A-Z0-9]{4}\+[A-Z0-9]{2,4}[\w]*)'

END_OF_LIST_SELECTORS = [".HlvXi", ".PbZDve", ".lCKMBd"]

END_OF_LIST_TEXTS = [
    r"reached the end|end of the list|no more results|that.?s all|you.?ve reached the end",
    r"fin de la liste|plus de r[eé]sultats",
    r"ende der liste|keine weiteren ergebnisse",
    r"fine dell.?elenco|non ci sono altri risultati",
    r"fim da lista|n[aã]o h[aá] mais resultados",
    r"конец списка|больше нет результатов",
    r"نهاية القائمة|لا مزيد من النتائج",
    r"列表结束|没有更多结果",
]

# Google blocking detection patterns
GOOGLE_BLOCKING_PATTERNS = [
    r"unusual traffic",
    r"not a robot",
    r"captcha",
    r"verify you're human",
    r"blocked.*request",
    r"too many requests",
    r"automated queries",
]
