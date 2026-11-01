import httpx
import pytest
from conftest import fixture

pytestmark = pytest.mark.anyio

SLUG = "python-programming-basic-fvpht0064"
SEARCH = "/api/client/v2/explore/product/search"
POSTS = "/wp-json/wp/v2/posts"


async def test_search_new_kinds_upcoming_and_type_facet(client, api):
    api[SEARCH] = fixture("search.json")
    r = (
        await client.call_tool(
            "fr_search_courses", {"kind": "webinar", "upcoming": True, "sort": "trend_count", "limit": 3}
        )
    ).structured_content
    q = api.calls[0].url.params
    assert q["type"] == "webinar" and q["publish_status"] == "not_published" and q["sort"] == "trend_count"
    assert r["types"]["course"] > 0


async def test_unreleased_cards_have_no_placeholder_price(client, api):
    body = fixture("search.json")
    body["products"][0].update(status="publishing", price=1)
    api[SEARCH] = body
    c = (await client.call_tool("fr_search_courses", {})).structured_content["courses"][0]
    assert c["status"] == "publishing" and "price" not in c


async def test_instructors_without_query_and_by_category(client, api):
    api["/api/client/v2/explore/instructor/search"] = fixture("instructors.json")
    await client.call_tool("fr_instructors", {})
    assert "term" not in api.calls[0].url.params
    api[SEARCH] = fixture("search.json")
    api["/api/client/v1/product/category"] = fixture("categories.json")
    r = (await client.call_tool("fr_instructors", {"category": "python"})).structured_content
    top = r["instructors"][0]
    assert top["slug"] and top["courses_in_category"] > 0 and api.calls[-1].url.params["category_id"] == "70382"


async def test_instructor_rating_stats_bio_and_education(client, api):
    api["/api/client/v1/instructor/pejman-eqbali"] = fixture("instructor.json")
    api[SEARCH] = fixture("search.json")
    r = (await client.call_tool("fr_instructor", {"slug": "pejman-eqbali", "limit": 1})).structured_content
    assert api.calls[1].url.params["count"] == "100" and len(r["courses"]) == 1
    st = r["rating_stats"]
    assert 4 < st["average"] <= 5 and st["reviews"] > 0 and st["courses_rated"] >= 1
    assert r["bio"] and r["education"][0]["university"]


async def test_field_and_university_swapped_by_the_site_are_fixed(client, api):
    body = fixture("instructors.json")
    body["instructors"][0].update(grade="دانشگاه یزد", university="مهندسی مکانیک")
    api["/api/client/v2/explore/instructor/search"] = body
    i = (await client.call_tool("fr_instructors", {"query": "x"})).structured_content["instructors"][0]
    assert i["university"] == "دانشگاه یزد" and i["field"] == "مهندسی مکانیک"


async def test_course_new_fields(client, api):
    body = fixture("show.json")
    body["product"]["language"] = "fa"
    body["product"]["tags"] = [{"name": "Abstraction در پایتون"}]
    body["product"]["faqs"] = [{"question": "<p>آیا گواهی دارد؟</p>", "answer": "<p>بله</p>"}]
    api[f"/api/client/v1/product/{SLUG}/show"] = body
    r = (await client.call_tool("fr_course", {"slug": SLUG})).structured_content
    assert r["faqs"] == [{"question": "آیا گواهی دارد؟", "answer": "بله"}]
    assert r["tags"] and r["language"] == "fa" and r["bundle"] is None


async def test_learning_paths_list_without_query(client, api):
    api["/api/client/v1/landings"] = {"data": [{"title": "T", "slug": "programming", "count_product": 140}]}
    r = (await client.call_tool("fr_learning_paths", {})).structured_content
    assert r["paths"][0]["url"].endswith("/how-to-learn/programming") and r["paths"][0]["courses"] == 140


async def test_learning_path_courses_and_related(client, api):
    api["/api/client/v1/landings/python-programming"] = fixture("landing.json")
    api["/api/client/v2/landings/632531/products"] = fixture("landing_products.json")
    api["/api/client/v1/landings/python-programming/relatedLandings"] = fixture("landing_related.json")
    url = "https://faradars.org/how-to-learn/python-programming"
    r = (await client.call_tool("fr_learning_path", {"slug": url})).structured_content
    assert r["course_count"] == 137 and r["pages"] == 7 and len(r["courses"]) == 3
    assert r["courses"][0]["slug"] and r["related_paths"][0]["slug"]
    r2 = (await client.call_tool("fr_learning_path", {"slug": "python-programming", "page": 2})).structured_content
    assert r2["related_paths"] == [] and api.calls[-1].url.params["page"] == "2"
    assert (await client.call_tool("fr_learning_path", {"slug": "nope"})).is_error


async def test_related_courses_groups(client, api):
    api[f"/api/client/v1/product/{SLUG}/cards"] = fixture("cards.json")
    r = (await client.call_tool("fr_related_courses", {"slug": SLUG, "limit": 1})).structured_content
    assert set(r) == {"same_instructor", "recommended", "similar"} and all(len(v) == 1 for v in r.values())
    assert r["same_instructor"][0]["slug"] and r["similar"][0]["price"]


async def test_compare_courses_picks_best(client, api):
    cheap = fixture("show.json")
    cheap["product"].update(slug="cheap-one", price=0, fara_festival={}, sold_count=5, rating={"rate": 4.0, "total": 9})
    api[f"/api/client/v1/product/{SLUG}/show"] = fixture("show.json")
    api["/api/client/v1/product/cheap-one/show"] = cheap
    r = (await client.call_tool("fr_compare_courses", {"slugs": [SLUG, "cheap-one"]})).structured_content
    assert [c["slug"] for c in r["courses"]] == [SLUG, "cheap-one"]
    assert r["best"]["cheapest"] == "cheap-one" and r["best"]["most_students"] == SLUG
    assert r["best"]["best_rated"] == SLUG  # cheap-one has under 50 reviews
    assert (await client.call_tool("fr_compare_courses", {"slugs": [SLUG]})).is_error


async def test_offers_campaigns_and_visible_plans(client, api):
    api["/api/client/v1/special-offers"] = fixture("offers.json")
    api["/api/client/v1/subscription/plans"] = fixture("plans.json")
    r = (await client.call_tool("fr_offers", {})).structured_content
    assert r["campaigns"][0]["ends"] == "2026-11-25" and "coupon" not in r["campaigns"][0]
    assert any(c.get("coupon") for c in r["campaigns"])
    assert [p["slug"] for p in r["subscription_plans"]] == ["one-year", "six-months"]
    assert r["subscription_plans"][0]["price"] < r["subscription_plans"][0]["price_before_discount"]


async def test_faq_filter_and_text(client, api):
    api["/api/client/v1/faq"] = fixture("faq.json")
    everything = (await client.call_tool("fr_faq", {})).structured_content["topics"]
    assert "viewing_certificate" in everything and "<" not in everything["viewing_certificate"][0]["answer"]
    assert (await client.call_tool("fr_faq", {"query": "zzzz-nothing"})).structured_content["topics"] == {}


async def test_suggest(client, api):
    api["/api/client/v1/utils/suggest/keywords"] = fixture("suggest.json")
    r = (await client.call_tool("fr_suggest", {"term": "پای", "limit": 3})).structured_content
    assert r["suggestions"][1] == "پایتون" and api.calls[0].url.params["count"] == "3"


async def test_articles_filters_and_chaining_fields(client, api):
    api["/wp-json/wp/v2/categories"] = [{"id": 322583}]
    api["/wp-json/wp/v2/tags"] = [{"id": 7}]
    api[POSTS] = lambda request: httpx.Response(
        200, json=fixture("posts.json"), headers={"X-WP-Total": "30", "X-WP-TotalPages": "15"}
    )
    r = (
        await client.call_tool(
            "fr_articles", {"query": "x", "category": "python", "tag": "django", "sort": "relevance", "limit": 2}
        )
    ).structured_content
    q = api.calls[-1].url.params
    assert q["categories"] == "322583" and q["tags"] == "7" and q["orderby"] == "relevance" and q["order"] == "desc"
    assert r["more"] is True and r["articles"][0]["slug"]
    api["/wp-json/wp/v2/categories"] = []
    assert (await client.call_tool("fr_articles", {"category": "nope"})).is_error


async def test_articles_totals_recovered_when_cdn_drops_headers(client, api):
    def posts(request):
        if request.url.params.get("per_page") == "1":
            return httpx.Response(200, json=[{"id": 1}], headers={"X-WP-Total": "45"})
        return httpx.Response(200, json=fixture("posts.json"))  # no WP headers, as on a CDN cache hit

    api[POSTS] = posts
    r = (await client.call_tool("fr_articles", {"limit": 10})).structured_content
    assert r["total"] == 45 and r["pages"] == 5 and r["more"] is True


async def test_article_text_outline_and_paging(client, api):
    api[POSTS] = fixture("post.json")
    r = (
        await client.call_tool("fr_article", {"slug": "https://blog.faradars.org/python-programming-language/"})
    ).structured_content
    assert api.calls[0].url.params["slug"] == "python-programming-language"
    assert r["title"] and r["key_points"] and r["outline"] and r["views"] > 0 and r["rating"]["stars"] > 4
    assert "x()" not in r["text"] and "\n- الف\n- ب" in r["text"] and "## پایان" in r["text"]
    first = (await client.call_tool("fr_article", {"slug": "abc-def", "max_chars": 500})).structured_content
    assert len(first["text"]) == 500 and first["next_offset"] == 500
    more = (
        await client.call_tool("fr_article", {"slug": "abc-def", "max_chars": 500, "offset": 500})
    ).structured_content
    assert more["text"] and more["text"] != first["text"]
    api[POSTS] = []
    assert (await client.call_tool("fr_article", {"slug": "missing-post"})).is_error


async def test_article_persian_slug_is_sent_plain(client, api):
    api[POSTS] = fixture("post.json")
    await client.call_tool("fr_article", {"slug": "fastapi-چیست"})
    assert api.calls[0].url.params["slug"] == "fastapi-چیست"


async def test_article_topics(client, api):
    api["/wp-json/wp/v2/categories"] = fixture("blog_categories.json")
    r = (await client.call_tool("fr_article_topics", {"limit": 3})).structured_content
    assert r["topics"][0]["slug"] == "programming" and len(r["topics"]) == 3 and r["total"] >= 3
    api["/wp-json/wp/v2/tags"] = [{"id": 1, "name": "Django", "slug": "django", "count": 13, "parent": 0}]
    t = (await client.call_tool("fr_article_topics", {"kind": "tag", "query": "django"})).structured_content
    assert t["topics"][0] == {"slug": "django", "name": "Django", "articles": 13}
