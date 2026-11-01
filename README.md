<!-- mcp-name: io.github.sepehr071/faradars-mcp -->

<div align="center">

# faradars-mcp: Faradars (فرادرس) course search MCP server for AI agents

**faradars-mcp is an unofficial, read-only MCP server that gives AI agents the public course catalog of Faradars (فرادرس), the large Persian online learning platform.**<br>
Its 16 tools search courses and videos, read prices, discounts and syllabi, compare courses, list student reviews, browse categories and instructors,<br>
walk learning paths, list offers and coupons, and search and read the Faradars Magazine (مجله فرادرس). No API key or Faradars account is needed.

[![PyPI](https://img.shields.io/pypi/v/faradars-mcp?color=2563eb)](https://pypi.org/project/faradars-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/faradars-mcp)](https://pypi.org/project/faradars-mcp/)
[![License: MIT](https://img.shields.io/badge/license-MIT-16a34a)](https://github.com/sepehr071/faradars-mcp/blob/main/LICENSE)

[For AI agents](#for-ai-agents) · [Quick start](#quick-start) · [What it can do](#what-it-can-do) · [Tools](#tools) · [فارسی](#فارسی)

</div>

---

## For AI agents

- **What:** unofficial MCP server (model context protocol) for faradars.org: course and video search with filters, course details (price, current sale, duration, rating, students, instructors, objectives, syllabus), student reviews, category tree, instructor profiles, learning paths, related courses and comparison, discount campaigns and subscription plans, help answers, and Faradars Magazine article search and full text.
- **Install:** `uvx faradars-mcp` or `claude mcp add faradars -- uvx faradars-mcp`. Transport: stdio. Needs [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python 3.10+).
- **Auth:** none. Optional `FARADARS_MCP_PROXY` (HTTP proxy URL, or a comma-separated list); system proxy settings are ignored.
- **Access:** read-only. It cannot log in, buy, enrol or comment, so no confirmation is needed before calling any tool.
- **Tools:** 16, all prefixed `fr_`. Typical sequences: `fr_search_courses` -> `fr_course` -> `fr_course_reviews`; `fr_course` -> `fr_related_courses` -> `fr_compare_courses`; `fr_instructors` -> `fr_instructor`; `fr_learning_paths` -> `fr_learning_path`; `fr_articles` -> `fr_article`.
- **Use when:** the user asks which Faradars courses exist on a topic, how much a course costs, whether it has a discount or certificate, what its syllabus is, who teaches it, which courses are free, or wants a tutorial from the Faradars Magazine.
- **Do not use when:** the user wants to watch lessons, buy, or see their own account (not supported).
- **Output:** compact JSON. Prices are Toman, durations hours, text is Persian as on the site.
- **Machine-readable:** [`server.json`](https://github.com/sepehr071/faradars-mcp/blob/main/server.json).

## What it can do

- **Search courses and videos** by text, category, free or paid, length, certificate or instructor, sorted by sales, views, relevance or date
- **Read a course**: price, active sale and its end time, hours, lesson count, rating, student count, objectives, prerequisites, description and the full syllabus
- **Read student reviews**, 10 at a time
- **Browse** the category tree, instructors and learning paths (مسیر یادگیری)
- **Search the magazine** (blog.faradars.org) for tutorials and comparisons

Example prompts:

- "Find the best-selling Python courses on Faradars and show me the syllabus of the first one."
- "Which free Excel courses does Faradars have?"
- "What else does the instructor of this course teach?"
- <span dir="rtl">بهترین دوره‌های آموزش پایتون در فرادرس کدام‌اند و قیمتشان چند است؟</span>
- <span dir="rtl">دوره‌های رایگان اکسل با گواهینامه را پیدا کن.</span>

## Quick start

You need [uv](https://docs.astral.sh/uv/getting-started/installation/). No API key or account.

<details open>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add faradars -- uvx faradars-mcp
```
</details>

<details>
<summary><b>Claude Desktop, Cursor, Windsurf, Gemini CLI</b></summary>

Add to the client's MCP config:

```json
{
  "mcpServers": {
    "faradars": { "command": "uvx", "args": ["faradars-mcp"] }
  }
}
```
</details>

<details>
<summary><b>VS Code (Copilot agent mode)</b></summary>

```json
{
  "servers": {
    "faradars": { "type": "stdio", "command": "uvx", "args": ["faradars-mcp"] }
  }
}
```
</details>

<details>
<summary><b>Anything else</b></summary>

It is a standard stdio MCP server: run `uvx faradars-mcp`, or `pip install faradars-mcp` and run `faradars-mcp`.
</details>

## Tools

| Tool | What it does |
|---|---|
| `fr_search_courses` | Search courses, videos, exams, podcasts and webinars by text, category, price, length, certificate, instructor or trend |
| `fr_course` | Get one course: price and sale, duration, rating, students, instructors, prerequisites, objectives, syllabus, included extras |
| `fr_course_reviews` | Get student reviews (stars and comment) of a course, newest first |
| `fr_related_courses` | Get a course's related courses: same instructor, recommended next steps, similar topics |
| `fr_compare_courses` | Compare 2-4 courses side by side (price, sale, length, rating, students, certificate) |
| `fr_categories` | List course categories as a tree of slugs and names |
| `fr_suggest` | Get the site's search-box suggestions for the start of a phrase |
| `fr_instructors` | Find instructors by name, or the top instructors of a category |
| `fr_instructor` | Get an instructor's profile, rating statistics and courses |
| `fr_learning_paths` | List or search curated learning paths (course collections) |
| `fr_learning_path` | Get one learning path: its ordered courses, totals and related paths |
| `fr_offers` | List current discount campaigns, public coupon codes and subscription plans |
| `fr_faq` | Get Faradars' general help answers (buying, access, certificates, support) |
| `fr_articles` | Search Faradars Magazine articles by text, category or tag, or list the newest |
| `fr_article` | Read one Magazine article: key points, outline, text, views and rating |
| `fr_article_topics` | List Magazine categories or tags with article counts |

All 16 tools are annotated `readOnlyHint: true`.

## How it works

```text
  AI agent  ──MCP over stdio──▶  faradars-mcp  ──HTTPS──▶  faradars.org/api/client      courses, categories, instructors
                                                  └──────▶  blog.faradars.org/wp-json    magazine
```

Requests look like Faradars' own web app (Chrome TLS fingerprint and headers), at most two at a time, with a 5 minute
cache. Set `FARADARS_MCP_PROXY=http://host:port` to route through a proxy.

## Notes

- Unofficial. Not affiliated with or endorsed by Faradars. It reads the same public data the website shows to anyone.
- Course content (videos) is not exposed; only catalog data.
- Prices change with Faradars sales (`sale_price` is time-limited).

## Development

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
uv run python -m pytest -q          # offline
uv run python -m pytest -m live -q  # real faradars.org
```

## فارسی

**faradars-mcp** یک سرور MCP غیررسمی و فقط‌خواندنی برای فرادرس است. با آن، دستیار هوش مصنوعی می‌تواند دوره‌ها را جست‌وجو کند، قیمت و تخفیف و سرفصل‌ها را بخواند، نظر دانشجویان را ببیند، مدرس‌ها و مسیرهای یادگیری را پیدا کند و در مجله فرادرس بگردد. نیازی به کلید API یا حساب کاربری نیست.

نصب: `claude mcp add faradars -- uvx faradars-mcp`

## License

MIT. Built by [Sepehr Radmard](https://github.com/sepehr071) (سپهر رادمرد).
