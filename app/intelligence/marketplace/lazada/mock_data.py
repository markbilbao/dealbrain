"""Mock Lazada listing payloads (Lazada-shaped fields, no live API)."""

from __future__ import annotations

from typing import Any

LAZADA_MOCK_LISTINGS: list[dict[str, Any]] = [
    {
        "itemId": "2002001",
        "name": "Apple iPhone 17 Pro Max 256GB Black Titanium Official",
        "price": 74_500.0,
        "currency": "PHP",
        "sellerName": "Lazada Apple Store",
        "ratingScore": 4.95,
        "availability": "in stock",
        "productUrl": "https://www.lazada.com.ph/products/i2002001.html",
    },
    {
        "itemId": "2002002",
        "name": "Apple iPhone 15 256GB Blue",
        "price": 42_990.0,
        "currency": "PHP",
        "sellerName": "MobileZone Official",
        "ratingScore": 4.6,
        "availability": "in stock",
        "productUrl": "https://www.lazada.com.ph/products/i2002002.html",
    },
    {
        "itemId": "2002003",
        "name": "Apple AirPods Pro 2 USB-C with MagSafe Case",
        "price": 12_490.0,
        "currency": "PHP",
        "sellerName": "SoundLab LazMall",
        "ratingScore": 4.85,
        "availability": "limited stock",
        "productUrl": "https://www.lazada.com.ph/products/i2002003.html",
    },
    {
        "itemId": "2002004",
        "name": "Samsung Galaxy S25 Ultra 512GB Titanium Gray",
        "price": 63_990.0,
        "currency": "PHP",
        "sellerName": "Samsung Official Store",
        "ratingScore": 4.7,
        "availability": "out of stock",
        "productUrl": "https://www.lazada.com.ph/products/i2002004.html",
    },
    {
        "itemId": "2002005",
        "name": "Apple MacBook Pro 14 M4 512GB Space Black",
        "price": 119_990.0,
        "currency": "PHP",
        "sellerName": "Lazada Apple Store",
        "ratingScore": 4.9,
        "availability": "in stock",
        "productUrl": "https://www.lazada.com.ph/products/i2002005.html",
    },
]
