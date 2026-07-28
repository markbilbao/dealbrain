"""Review & Rating Intelligence — Sprint 11.

Status: implemented (in-memory + mock collectors only)
Date: 2026-07-29

Scope
-----
Collect marketplace rating / review snapshots and compare them across
Shopee, Lazada, TikTok Shop, and Amazon. This sprint does **not** scrape
live marketplaces, call LLMs, detect fake reviews, send notifications, or
modify protected intelligence modules.

Architecture
------------
```
Presentation (demo.html)
  ↓
API (/api/v1/reviews)
  ↓
ReviewService
  ↓
Domain (ReviewSnapshot, MarketplaceReviewComparison)
  ↓
ReviewRepository (in-memory)
  ↓
Mock Marketplace Collectors
  (Shopee · Lazada · TikTok Shop · Amazon)
```

Domain
------
``ReviewSnapshot`` fields:

- ``snapshot_id``
- ``product_id``
- ``marketplace``
- ``average_rating``
- ``review_count``
- ``five_star_count`` / ``four_star_count`` / ``three_star_count`` /
  ``two_star_count`` / ``one_star_count``
- ``seller_rating`` / ``seller_followers`` / ``seller_products``
- ``collected_at``

Repository
----------
``ReviewRepository`` (in-memory implementation only):

- ``save_snapshot()``
- ``latest_snapshot()``
- ``history()``
- ``marketplace_summary()``

Services
--------
``ReviewService``:

- ``collect_reviews(product_id)``
- ``latest_reviews(product_id)``
- ``review_history(product_id)``
- ``compare_marketplaces(product_id)``
- ``overall_rating(product_id)`` — weighted by review count
- ``total_review_count(product_id)``

API endpoints
-------------
Base path: ``/api/v1/reviews``

- ``POST /reviews/collect``
- ``GET /reviews/{product_id}``
- ``GET /reviews/history/{product_id}``
- ``GET /reviews/compare/{product_id}``

Sample JSON
-----------

Collect::

    POST /api/v1/reviews/collect
    {
      "product_id": "00000000-0000-4000-8000-000000000017",
      "product_label": "iPhone 17 Pro Max"
    }

Compare response::

    {
      "product": "iPhone 17 Pro Max",
      "product_id": "00000000-0000-4000-8000-000000000017",
      "overall_rating": 4.65,
      "total_review_count": 43364,
      "marketplaces": [
        {
          "marketplace": "Amazon",
          "rating": 4.5,
          "reviews": 15680,
          "seller_rating": 4.6
        },
        {
          "marketplace": "Lazada",
          "rating": 4.7,
          "reviews": 9821,
          "seller_rating": 4.8
        },
        {
          "marketplace": "Shopee",
          "rating": 4.8,
          "reviews": 12431,
          "seller_rating": 4.9
        },
        {
          "marketplace": "TikTok Shop",
          "rating": 4.6,
          "reviews": 5432,
          "seller_rating": 4.7
        }
      ]
    }

Mock collector examples
-----------------------
Shopee — rating 4.8 · reviews 12,431 · seller 4.9 · followers 18,000

Lazada — rating 4.7 · reviews 9,821 · seller 4.8

TikTok Shop — rating 4.6 · reviews 5,432 · seller 4.7

Amazon — rating 4.5 · reviews 15,680 · seller 4.6

Protected modules (unchanged)
-----------------------------
- Product Identity
- Product Matching
- DealScore Engine
- Recommendation Engine
- Price History
- Collection Operations
- Watchlists

Known limitations
-----------------
- Mock collectors only
- No live scraping
- No HTTP requests to marketplaces
- No browser automation
- No AI summaries
- No sentiment analysis
- No fake review detection
- No notifications
- In-memory persistence only (process-local; no DB migrations)
"""
