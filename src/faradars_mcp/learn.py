"""Faradars learning tools: learning paths, related courses, comparison, offers and subscription, FAQ, suggestions."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Annotated, Any

from pydantic import Field

from .courses import Page, Slug, _course, _hours, _names, _pager, _show, _slug, _text
from .http import API, SITE, ApiError, fetch
from .registry import tool


@tool("Learning path")
async def fr_learning_path(
    slug: Annotated[
        str,
        Field(description="Path slug from fr_learning_paths.", min_length=2, max_length=200),
    ],
    page: Page = 1,
) -> dict[str, Any]:
    """Get one Faradars learning path (مسیر یادگیری): its ordered course list, totals and related paths.

    Courses are in site order (starters first), 20 per page. Then call fr_course.
    """
    s = _slug(slug)
    try:
        head = (await fetch(f"{API}/v1/landings/{s}")).get("data") or {}
    except ApiError as e:
        if e.status == 404:
            raise ApiError(f"No learning path '{s}'. Get slugs from fr_learning_paths.", 404) from e
        raise
    body = await fetch(f"{API}/v2/landings/{head.get('id')}/products", {"page": page})
    related = []
    if page == 1:
        rel = await fetch(f"{API}/v1/landings/{s}/relatedLandings")
        related = [
            {"slug": x.get("slug"), "title": x.get("title"), "courses": x.get("count_product")}
            for x in rel.get("data") or []
        ]
    return {
        "title": head.get("title"),
        "slug": head.get("slug") or s,
        "url": f"{SITE}/how-to-learn/{head.get('slug') or s}",
        "course_count": head.get("count_product"),
        "students": head.get("count_student"),
        "hours": head.get("total_time_hour"),
        "instructors": head.get("totalInstructor"),
        "intro": _text(head.get("content"), 600),
        **_pager(body.get("pagination") or {}),
        "courses": [_course(p) for p in body.get("products") or []],
        "related_paths": related,
    }


@tool("Related courses")
async def fr_related_courses(
    slug: Slug,
    limit: Annotated[int, Field(description="Per group.", ge=1, le=6)] = 6,
) -> dict[str, Any]:
    """Get courses related to one Faradars course: more by the same instructor, recommended next steps, similar topics.

    Cards match fr_search_courses.
    """
    body = await fetch(f"{API}/v1/product/{_slug(slug)}/cards")
    data = body.get("data") or {}
    return {
        key: [_course(p) for p in (data.get(src) or [])[:limit]]
        for key, src in (
            ("same_instructor", "instructor_products"),
            ("recommended", "recommended_products"),
            ("similar", "relatedProducts"),
        )
    }


def _facts(p: dict[str, Any]) -> dict[str, Any]:
    f = p.get("fara_festival") or {}
    sale = f.get("price_after_discount") if f.get("discount") else None
    rating = p.get("rating") or {}
    return {
        "title": p.get("title_short") or p.get("title"),
        "slug": p.get("slug"),
        "price": p.get("price"),
        "sale_price": sale,
        "hours": _hours((p.get("duration") or {}).get("in_minutes")),
        "lessons": p.get("lessons_count"),
        "students": p.get("sold_count"),
        "rating": rating.get("rate"),
        "rating_count": rating.get("total"),
        "certificate": p.get("hasCertificate"),
        "exam_questions": p.get("examCount"),
        "practice_items": p.get("practiceCount"),
        "language": p.get("language"),
        "published": (p.get("published_at") or "")[:10],
        "instructors": _names(p.get("instructors")),
        "prerequisites": [x.get("title") for x in p.get("product_prerequisites") or []],
    }


@tool("Compare courses")
async def fr_compare_courses(
    slugs: Annotated[
        list[str],
        Field(description="2-4 course slugs or URLs.", min_length=2, max_length=4),
    ],
) -> dict[str, Any]:
    """Compare 2-4 Faradars courses side by side: price, sale, length, lessons, students, rating, certificate, exams.

    `best` names the cheapest, longest, most popular and best rated course (rating needs 50+ reviews). Prices are Toman.
    """
    rows = [_facts(p) for p in await asyncio.gather(*(_show(s) for s in slugs))]

    def best(key, pool=rows, reverse=False):
        pool = [r for r in pool if r.get(key) is not None]
        return (max if reverse else min)(pool, key=lambda r: r[key])["slug"] if pool else None

    for r in rows:
        r["pay"] = r["sale_price"] if r["sale_price"] is not None else r["price"]
    return {
        "courses": rows,
        "best": {
            "cheapest": best("pay"),
            "longest": best("hours", reverse=True),
            "most_students": best("students", reverse=True),
            "best_rated": best("rating", [r for r in rows if (r["rating_count"] or 0) >= 50], reverse=True),
        },
    }


def _day(ms: Any) -> str | None:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d") if isinstance(ms, int | float) else None


@tool("Offers and subscription")
async def fr_offers() -> dict[str, Any]:
    """List the current Faradars discount campaigns, public coupon codes and subscription plans.

    Subscription plans give unlimited access to all courses for a period. Prices are Toman. A course's live sale
    is in fr_course.
    """
    offers, plans = await asyncio.gather(fetch(f"{API}/v1/special-offers"), fetch(f"{API}/v1/subscription/plans"))
    return {
        "campaigns": [
            {
                "title": o.get("title"),
                "details": _text(o.get("description"), 250),
                "coupon": None if o.get("coupon") in (None, "", "-") else o.get("coupon"),
                "ends": _day(o.get("date_expired")),
                "ends_fa": o.get("date_expired_convert"),
                "link": o.get("link"),
            }
            for o in (offers.get("data") or {}).get("offers") or []
        ],
        "subscription_plans": [
            {
                "name": x.get("title"),
                "slug": x.get("slug"),
                "price": x.get("price"),
                "price_before_discount": x.get("price_before_discount")
                if x.get("price_before_discount") != x.get("price")
                else None,
                "discount_percent": x.get("discount_percent"),
                "days": x.get("duration_days"),
            }
            for x in plans.get("data") or []
            if x.get("is_active") and not x.get("is_hidden")
        ],
    }


@tool("Faradars FAQ")
async def fr_faq(
    query: Annotated[
        str | None,
        Field(description="Word to look for, e.g. گواهینامه.", max_length=60),
    ] = None,
) -> dict[str, Any]:
    """Get Faradars' general help answers: buying and subscription, access validity, certificates, support, refunds.

    Use for policy questions. With `query` only matching questions are returned.
    """
    data = (await fetch(f"{API}/v1/faq")).get("data") or {}
    q = (query or "").casefold()
    topics = {}
    for topic, items in data.items():
        rows = [
            {"question": _text(x.get("question")), "answer": _text(x.get("answer"), 700)}
            for x in items or []
            if q in _text(x.get("question")).casefold() or q in _text(x.get("answer")).casefold()
        ]
        if rows:
            topics[topic] = rows
    return {"topics": topics}


@tool("Search suggestions")
async def fr_suggest(
    term: Annotated[str, Field(description="Start of a phrase, e.g. پای.", min_length=1, max_length=60)],
    limit: Annotated[int, Field(description="Suggestions.", ge=1, le=10)] = 5,
) -> dict[str, Any]:
    """Get Faradars search-box suggestions for the start of a phrase (autocomplete).

    Use to find the site's own wording before fr_search_courses.
    """
    body = await fetch(f"{API}/v1/utils/suggest/keywords", {"term": term, "count": limit})
    return {"suggestions": [k.get("title") for k in (body.get("data") or {}).get("keywords") or []]}
