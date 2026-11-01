import httpx
import pytest
from conftest import fixture

pytestmark = pytest.mark.anyio

SLUG = "python-programming-basic-fvpht0064"
TOOLS = {
    "fr_search_courses",
    "fr_course",
    "fr_course_reviews",
    "fr_categories",
    "fr_instructors",
    "fr_instructor",
    "fr_learning_paths",
    "fr_articles",
    "fr_learning_path",
    "fr_related_courses",
    "fr_compare_courses",
    "fr_offers",
    "fr_faq",
    "fr_suggest",
    "fr_article",
    "fr_article_topics",
}
SEARCH = "/api/client/v2/explore/product/search"


async def test_all_tools_are_read_only_and_described(client):
    tools = (await client.list_tools()).tools
    assert {t.name for t in tools} == TOOLS
    for t in tools:
        assert t.annotations.read_only_hint is True, t.name
        assert t.title and t.description.splitlines()[0].endswith("."), t.name
        assert "title" not in str(t.input_schema.get("properties", {}).values()), t.name


async def test_search_maps_filters_and_trims_cards(client, api):
    api[SEARCH] = fixture("search.json")
    r = (
        await client.call_tool(
            "fr_search_courses", {"query": "پایتون", "free": True, "kind": "course", "certificate": True, "page": 2}
        )
    ).structured_content
    q = api.calls[0].url.params
    assert q["term"] == "پایتون" and q["cost"] == "free" and q["type"] == "course" and q["certificate"] == "with"
    assert q["page"] == "2" and q["publish_status"] == "published" and "category_id" not in q
    assert r["total"] == 216 and len(r["courses"]) == 3 and r["related_categories"][0]["slug"] == "free-courses"
    c = r["courses"][0]
    assert c["slug"] and c["price"] == 0 and "sale_price" not in c and set(c) >= {"title", "hours", "students"}


async def test_search_category_slug_and_instructor_slug_become_ids(client, api):
    api[SEARCH] = fixture("search.json")
    api["/api/client/v1/product/category"] = fixture("categories.json")
    api["/api/client/v1/instructor/pejman-eqbali"] = fixture("instructor.json")
    await client.call_tool("fr_search_courses", {"category": "python", "instructor": "pejman-eqbali"})
    q = next(c for c in api.calls if c.url.path == SEARCH).url.params
    assert q["category_id"] == "70382" and q["instructor_id"] == "363151"


async def test_search_unknown_category_is_an_error(client, api):
    api["/api/client/v1/product/category"] = fixture("categories.json")
    r = await client.call_tool("fr_search_courses", {"category": "nope"})
    assert r.is_error and "fr_categories" in r.content[0].text


async def test_course_detail_sale_and_syllabus(client, api):
    api[f"/api/client/v1/product/{SLUG}/show"] = fixture("show.json")
    r = (await client.call_tool("fr_course", {"slug": f"https://faradars.org/courses/{SLUG}?x=1"})).structured_content
    assert r["price"] == 1390000 and r["sale"]["price"] == 119000 and r["sale"]["discount"] == 1271000
    assert r["hours"] == 21.6 and r["url"] == f"https://faradars.org/courses/{SLUG}"
    assert r["instructors"][0]["slug"] == "pejman-eqbali" and r["prerequisites"][0]["free"] is True
    assert r["syllabus"][1]["lessons"] == 4 and "items" not in r["syllabus"][1]
    assert "<" not in r["description"] and "&zwnj;" not in r["description"]
    full = (await client.call_tool("fr_course", {"slug": SLUG, "lessons": True})).structured_content
    assert full["syllabus"][1]["items"][0] == {"title": "نصب پایتون", "minutes": 8, "free": True}


async def test_course_missing_and_bad_slug(client, api):
    r = await client.call_tool("fr_course", {"slug": "no-such-course"})
    assert r.is_error and "fr_search_courses" in r.content[0].text
    r = await client.call_tool("fr_course", {"slug": "bad slug!"})
    assert r.is_error


async def test_reviews_resolve_course_id(client, api):
    api[f"/api/client/v1/product/{SLUG}/show"] = fixture("show.json")
    api["/api/client/v1/product/9229982/comments"] = fixture("comments.json")
    r = (await client.call_tool("fr_course_reviews", {"slug": SLUG, "limit": 3})).structured_content
    assert r["total"] == 835 and r["more"] is True and len(r["reviews"]) == 3
    assert r["reviews"][0]["stars"] == 5 and r["reviews"][0]["date"] == "2026-10-27"
    assert api.calls[-1].url.params["limit"] == "3"


async def test_categories_top_level_and_subtree(client, api):
    api["/api/client/v1/product/category"] = fixture("categories.json")
    top = (await client.call_tool("fr_categories", {})).structured_content["categories"]
    assert top[1]["slug"] == "programming" and "programming-languages" in top[1]["children"]
    sub = (await client.call_tool("fr_categories", {"parent": "programming-languages"})).structured_content
    assert {c["slug"] for c in sub["children"]} >= {"python", "javascript"}
    assert (await client.call_tool("fr_categories", {"parent": "zzz"})).is_error


async def test_instructors_search(client, api):
    api["/api/client/v2/explore/instructor/search"] = fixture("instructors.json")
    r = (await client.call_tool("fr_instructors", {"query": "اقبالی"})).structured_content
    assert r["instructors"][0]["slug"] == "pejman-eqbali" and r["instructors"][0]["courses"] == 54
    assert api.calls[0].url.params["term"] == "اقبالی"


async def test_instructor_profile_with_courses(client, api):
    api["/api/client/v1/instructor/pejman-eqbali"] = fixture("instructor.json")
    api[SEARCH] = fixture("search.json")
    r = (await client.call_tool("fr_instructor", {"slug": "pejman-eqbali", "free": False})).structured_content
    q = api.calls[1].url.params
    assert q["instructor_id"] == "363151" and q["cost"] == "not_free"
    assert r["name"] and r["students"] and r["course_count"] and len(r["courses"]) == 3


async def test_learning_paths(client, api):
    api["/api/client/v2/explore/landing/search"] = fixture("landings.json")
    r = (await client.call_tool("fr_learning_paths", {"query": "پایتون"})).structured_content
    p = r["paths"][0]
    assert (
        p["url"].startswith("https://faradars.org/how-to-learn/")
        and p["courses"] == 137
        and len(p["first_courses"]) == 3
    )


async def test_articles_use_wp_totals_and_strip_html(client, api):
    def posts(request):
        return httpx.Response(200, json=fixture("posts.json"), headers={"X-WP-Total": "1747", "X-WP-TotalPages": "874"})

    api["/wp-json/wp/v2/posts"] = posts
    r = (await client.call_tool("fr_articles", {"query": "python", "limit": 2})).structured_content
    assert r["total"] == 1747 and r["pages"] == 874 and len(r["articles"]) == 2
    a = r["articles"][0]
    assert a["url"].startswith("https://blog.faradars.org/") and "<" not in a["excerpt"] and a["date"] == "2026-10-31"
    assert api.calls[0].url.params["search"] == "python"


async def test_articles_past_the_last_page_is_empty(client, api):
    api["/wp-json/wp/v2/posts"] = lambda request: httpx.Response(400, json={"code": "rest_post_invalid_page_number"})
    r = (await client.call_tool("fr_articles", {"page": 500})).structured_content
    assert r["articles"] == []


async def test_requests_look_like_the_site_frontend(api):
    from faradars_mcp import http

    api["/api/client/v1/megaMenu"] = {}
    api["/wp-json/wp/v2/posts"] = []
    await http.fetch(f"{http.API}/v1/megaMenu")
    await http.fetch(f"{http.BLOG}/posts")
    own, blog = (c.headers for c in api.calls)
    assert own["accept"] == "application/json" and own["accept-language"] == "fa" and own["nextjs"] == "true"
    assert own["platform"] == "web" and own["authorization"] == "" and own["current-url"] == own["referer"]
    assert "origin" not in own and own["sec-fetch-site"] == "same-origin"
    assert blog["origin"] == "https://faradars.org" and blog["sec-fetch-site"] == "same-site"
