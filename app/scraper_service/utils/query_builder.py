"""
Search query builder — mirrors backend/src/services/search-query-builder.ts
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import quote_plus


@dataclass
class SourceQuery:
    source: str
    query: str
    url: str
    full_search_query: str
    semantic_keyword: Optional[str] = None
    is_semantic_expansion: bool = False


def slugify(text: str) -> str:
    return text.lower().replace(" ", "-")


def build_location_string(
    area: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    country: Optional[str] = None,
    location: Optional[str] = None,
) -> str:
    parts = [p for p in [area, city, state, country] if p]
    return ", ".join(parts) if parts else (location or "")


def build_maps_search_query(
    business_type: str,
    area: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    country: Optional[str] = None,
    location: Optional[str] = None,
) -> str:
    loc = build_location_string(area, city, state, country, location)
    if loc:
        return f"{business_type} in {loc}"
    return business_type


def build_source_queries(
    business_type: str,
    sources: List[str],
    area: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    country: Optional[str] = None,
) -> List[SourceQuery]:
    queries: List[SourceQuery] = []

    for source in sources:
        if source == "google-maps":
            search_query = build_maps_search_query(business_type, area, city, state, country)
            queries.append(
                SourceQuery(
                    source="google-maps",
                    query=search_query,
                    url=f"https://www.google.com/maps/search/{quote_plus(search_query)}",
                    full_search_query=search_query,
                )
            )

        elif source == "justdial":
            city_slug = slugify(city) if city else "india"
            area_slug = slugify(area) if area else ""
            biz_slug = slugify(business_type)
            query = (
                f"{business_type} in {area} {city}"
                if area
                else (f"{business_type} in {city}" if city else business_type)
            )
            url = (
                f"https://www.justdial.com/{city_slug}/{biz_slug}-in-{area_slug}"
                if area
                else f"https://www.justdial.com/{city_slug}/{biz_slug}"
            )
            queries.append(
                SourceQuery(
                    source="justdial",
                    query=query,
                    url=url,
                    full_search_query=query,
                )
            )

        elif source == "indiamart":
            query = (
                f"{business_type} {area} {city}"
                if area
                else (f"{business_type} {city}" if city else business_type)
            )
            queries.append(
                SourceQuery(
                    source="indiamart",
                    query=query,
                    url=f"https://dir.indiamart.com/search.mp?ss={quote_plus(query)}",
                    full_search_query=query,
                )
            )

        elif source == "clutch":
            query = f"{business_type} {city or ''} {state or ''}".strip()
            queries.append(
                SourceQuery(
                    source="clutch",
                    query=query,
                    url=f"https://clutch.co/search?q={quote_plus(query)}",
                    full_search_query=query,
                )
            )

        elif source == "website":
            query = (
                f"{business_type} in {city} official website"
                if city
                else f"{business_type} official website"
            )
            queries.append(
                SourceQuery(
                    source="website",
                    query=query,
                    url=f"https://www.google.com/search?q={quote_plus(query)}",
                    full_search_query=query,
                )
            )

    return queries
