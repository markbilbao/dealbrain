"""Mock Shopee listing payloads (Shopee-shaped fields, no live API)."""

from __future__ import annotations

from typing import Any

# Prices use Shopee's integer micro-currency convention (PHP amount * 100_000).
SHOPEE_MOCK_LISTINGS: list[dict[str, Any]] = [
    {
        "itemid": "1001001",
        "shopid": "88001",
        "name": "Apple iPhone 17 Pro Max 256GB Black Titanium",
        "price": 7_499_900_000,  # 74_999.00 PHP
        "currency": "PHP",
        "shop_name": "Apple Authorized PH",
        "rating_star": 4.9,
        "stock": 42,
    },
    {
        "itemid": "1001002",
        "shopid": "88002",
        "name": "Apple iPhone 16 Pro 128GB White Titanium",
        "price": 5_899_900_000,
        "currency": "PHP",
        "shop_name": "GadgetHub Official",
        "rating_star": 4.7,
        "stock": 18,
    },
    {
        "itemid": "1001003",
        "shopid": "88003",
        "name": "Apple AirPods Pro 2 USB-C",
        "price": 1_299_900_000,
        "currency": "PHP",
        "shop_name": "AudioWorld Store",
        "rating_star": 4.8,
        "stock": 3,
    },
    {
        "itemid": "1001004",
        "shopid": "88004",
        "name": "Samsung Galaxy S25 Ultra 512GB",
        "price": 6_499_900_000,
        "currency": "PHP",
        "shop_name": "Samsung Flagship PH",
        "rating_star": 4.6,
        "stock": 0,
    },
    {
        "itemid": "1001005",
        "shopid": "88001",
        "name": "Apple MacBook Air M3 256GB Midnight",
        "price": 6_299_900_000,
        "currency": "PHP",
        "shop_name": "Apple Authorized PH",
        "rating_star": 4.9,
        "stock": 12,
    },
]
