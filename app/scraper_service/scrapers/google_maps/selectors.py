"""
Google Maps CSS/attribute selectors.
Mirrors backend/src/sources/google-maps/selectors.ts
"""

FEED_CONTAINER = '[role="feed"]'

CARD_SELECTORS = [
    "div.Nv2PK",
    'div[role="article"]',
    'a[href*="maps/place/"]',
]

DETAIL_COMPANY_NAME = ["h1", "h1.DUwDvf", 'h1[itemprop="name"]']

DETAIL_CATEGORY = [
    "button.DKv0N",
    'button[jsaction*="category"]',
    'button[aria-label*="Category"]',
    'span[jsaction*="category"]',
    ".DkEaL",
]

DETAIL_PHONE = [
    'button[data-item-id*="phone"]',
    'a[data-item-id*="phone"]',
    'button[aria-label*="phone"]',
    'button[aria-label*="Phone"]',
    'button[aria-label*="Call"]',
    'a[href^="tel:"]',
    'button[data-item-id$="phone"]',
]

DETAIL_ADDRESS = [
    'button[data-item-id*="address"]',
    'button[aria-label*="Address"]',
    'button[aria-label*="address"]',
    'button[data-item-id$="address"]',
    'div[data-item-id*="address"]',
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
]

DETAIL_PANEL_SCROLL = '[role="dialog"], div[role="main"], div.m6QErb'

DETAIL_RATING = [
    'span[role="img"][aria-label*="stars"]',
    'span[aria-label*="star"]',
    'div[aria-label*="stars"]',
]

# Business status (Open/Closed)
DETAIL_BUSINESS_STATUS = [
    'span[aria-label*="Open"]',
    'span[aria-label*="Closed"]',
    'span[aria-label*="Closes"]',
    'span[aria-label*="Opens"]',
    '.OqCZI span',
    '.ZDu9vd span',
]

# Working hours
DETAIL_WORKING_HOURS = [
    'table[aria-label*="Hours"]',
    'div[aria-label*="Hours"]', 
    '.t39EBf',
    '.eK4R0e',
    '[data-value*="OpeningHours"]',
]

# Plus Code
DETAIL_PLUS_CODE = [
    'button[data-item-id*="oloc"]',
    'button[aria-label*="Plus code"]',
    'button[aria-label*="plus code"]',
    'div[data-value*="plus_code"]',
]

# Owner claimed / verification badge
DETAIL_OWNER_CLAIMED = [
    'span[aria-label*="Claimed"]',
    'span[aria-label*="Verified"]',
    '.RZ66Rb span',
    'button[aria-label*="Claim this business"]',
]

# Total photos count
DETAIL_TOTAL_PHOTOS = [
    'button[aria-label*="photos"]',
    'button[aria-label*="Photos"]',
    'button[data-item-id*="photos"]',
    '.Gpq6kf .fontTitleSmall',
]

# Service options (delivery, takeout, etc.)
DETAIL_SERVICE_OPTIONS = [
    'div[aria-label*="Service options"]',
    'div[aria-label*="Highlights"]',
    '.AeaXub',
    '.RWPxGd',
]

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
