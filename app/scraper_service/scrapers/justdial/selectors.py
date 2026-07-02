"""JustDial CSS selectors — mirrors backend/src/sources/justdial/selectors.ts"""

# Result container selectors (tried in order)
RESULT_BOX_SELECTORS = [
    'div[class*="resultbox"]',
    'li[data-result-index]',
    ".jca-widget",
    ".cntanr",
    ".store-block",
    'div[class*="result"]',
    'section[class*="result"]',
]

NAME_SELECTORS = [
    ".font22",
    'span[class*="font22"]',
    '[class*="store_name"]',
    ".lng_cont_name",
    "h2",
    "h3",
    '[class*="name"]',
]

PHONE_SELECTORS = [
    'a[href^="tel:"]',
    ".callNowAnchor",
    'a[class*="call"]',
    '[class*="callNow"]',
    ".contact-info",
    '[class*="phone"]',
    '[class*="mob"]',
]

ADDRESS_SELECTORS = [
    ".cont_fload",
    '[class*="address"]',
    ".mre-dir",
    '[class*="add"]',
    ".cns_address",
]

RATING_SELECTORS = [
    '[class*="rating"]',
    ".green-box",
    ".star",
    '[class*="green"]',
]

SCROLL_CONTAINER_SELECTORS = [
    ".result-list",
    '[class*="result_list"]',
    ".search-result",
    ".card-list",
    "main",
    '[role="main"]',
    ".list_part",
    ".jbd",
    ".jbt",
]

# Menu item patterns to skip (food items, not businesses)
MENU_ITEM_PATTERNS = [
    "manchurian", "tandoori", "paneer", "butter chicken", "mutton",
    "curry", "biryani", "roti", "naan", "paratha", "rice", "dal",
    "soup", "salad", "dessert", "ice cream", "shake", "juice",
    "starter", "main course", "sizzler", "pizza", "pasta", "burger",
    "sandwich", "roll", "noodles", "fried rice", "spring roll",
    "chilli", "masala", "kebab", "tikka", "kofta", "korma",
    "lassi", "chai", "coffee", "cold drink", "soft drink",
]
