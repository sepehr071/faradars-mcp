import pytest

pytestmark = [pytest.mark.live, pytest.mark.anyio]


async def test_live_search_and_course(client):
    r = (
        await client.call_tool("fr_search_courses", {"query": "پایتون", "sort": "relevance", "limit": 5})
    ).structured_content
    assert r["total"] > 100 and len(r["courses"]) == 5
    c = (await client.call_tool("fr_course", {"slug": r["courses"][0]["slug"]})).structured_content
    assert c["title"] and c["syllabus"] and c["hours"] > 0


async def test_live_free_filter(client):
    r = (await client.call_tool("fr_search_courses", {"free": True, "limit": 5})).structured_content
    assert r["total"] > 1000 and all(c["price"] == 0 for c in r["courses"])


async def test_live_reviews(client):
    r = (
        await client.call_tool("fr_course_reviews", {"slug": "python-programming-basic-fvpht0064", "limit": 3})
    ).structured_content
    assert r["total"] > 100 and len(r["reviews"]) == 3


async def test_live_categories_and_category_filter(client):
    sub = (await client.call_tool("fr_categories", {"parent": "programming-languages"})).structured_content
    assert any(c["slug"] == "python" for c in sub["children"])
    r = (await client.call_tool("fr_search_courses", {"category": "python", "limit": 3})).structured_content
    assert r["total"] > 100


async def test_live_instructor(client):
    found = (await client.call_tool("fr_instructors", {"query": "اقبالی"})).structured_content
    assert any(i["slug"] == "pejman-eqbali" for i in found["instructors"])
    r = (await client.call_tool("fr_instructor", {"slug": "pejman-eqbali", "limit": 3})).structured_content
    assert r["courses_total"] > 20 and len(r["courses"]) == 3


async def test_live_learning_paths(client):
    r = (await client.call_tool("fr_learning_paths", {"query": "پایتون"})).structured_content
    assert r["paths"] and r["paths"][0]["url"].startswith("https://faradars.org/")


async def test_live_articles(client):
    r = (await client.call_tool("fr_articles", {"query": "python", "limit": 3})).structured_content
    assert len(r["articles"]) == 3 and r["articles"][0]["url"].startswith("https://blog.faradars.org/")


async def test_live_learning_path_and_related(client):
    r = (await client.call_tool("fr_learning_path", {"slug": "python-programming"})).structured_content
    assert r["course_count"] > 50 and r["pages"] >= 2 and len(r["courses"]) == 20 and r["related_paths"]
    rel = (
        await client.call_tool("fr_related_courses", {"slug": "python-programming-basic-fvpht0064"})
    ).structured_content
    assert rel["same_instructor"] and rel["similar"]
    assert (await client.call_tool("fr_learning_paths", {})).structured_content["paths"]


async def test_live_compare_offers_faq_suggest(client):
    slugs = ["python-programming-basic-fvpht0064", "crash-course-of-python-fvpht007"]
    r = (await client.call_tool("fr_compare_courses", {"slugs": slugs})).structured_content
    assert r["best"]["cheapest"] == "crash-course-of-python-fvpht007" and len(r["courses"]) == 2
    o = (await client.call_tool("fr_offers", {})).structured_content
    assert o["subscription_plans"] and all(c["link"].startswith("https://") for c in o["campaigns"])
    f = (await client.call_tool("fr_faq", {"query": "گواهینامه"})).structured_content
    assert f["topics"]
    s = (await client.call_tool("fr_suggest", {"term": "پای"})).structured_content
    assert "پایتون" in s["suggestions"]


async def test_live_instructor_stats_and_category_top(client):
    r = (await client.call_tool("fr_instructor", {"slug": "pejman-eqbali", "limit": 2})).structured_content
    assert 4 < r["rating_stats"]["average"] <= 5 and r["education"]
    top = (await client.call_tool("fr_instructors", {"category": "python"})).structured_content
    assert top["instructors"][0]["courses_in_category"] > 5


async def test_live_search_kinds(client):
    r = (await client.call_tool("fr_search_courses", {"kind": "webinar", "limit": 2})).structured_content
    assert r["total"] > 10 and all(c["type"] == "webinar" for c in r["courses"])
    up = (await client.call_tool("fr_search_courses", {"upcoming": True, "limit": 2})).structured_content
    assert up["total"] > 10 and all("price" not in c for c in up["courses"])


async def test_live_article_and_topics(client):
    a = (
        await client.call_tool("fr_article", {"slug": "python-programming-language", "max_chars": 800})
    ).structured_content
    assert a["views"] > 1000 and a["outline"] and len(a["text"]) == 800 and a["next_offset"] == 800
    topics = (await client.call_tool("fr_article_topics", {"limit": 5})).structured_content
    assert topics["topics"][0]["articles"] > 100
    r = (await client.call_tool("fr_articles", {"category": "python", "limit": 3})).structured_content
    assert r["total"] > 100 and r["pages"] > 10 and len(r["articles"]) == 3
    assert (
        await client.call_tool("fr_article", {"slug": r["articles"][0]["slug"], "max_chars": 500})
    ).structured_content["text"]
