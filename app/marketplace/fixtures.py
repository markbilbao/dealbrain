"""Deterministic marketplace data fixtures for Sprint 18 demos and tests."""

from __future__ import annotations

from typing import Any

# Catalog entries used for deterministic product matching.
CATALOG_PRODUCTS: tuple[dict[str, Any], ...] = (
    {
        "product_id": "canon-iphone-15-pro-256",
        "brand": "Apple",
        "model": "iPhone 15 Pro",
        "title": "Apple iPhone 15 Pro 256GB",
        "sku": "IP15PRO-256",
        "upc": "194253431413",
        "aliases": ("iphone 15 pro 256", "apple iphone 15 pro"),
    },
    {
        "product_id": "canon-galaxy-s24-256",
        "brand": "Samsung",
        "model": "Galaxy S24",
        "title": "Samsung Galaxy S24 256GB",
        "sku": "SGS24-256",
        "upc": "887276798012",
        "aliases": ("galaxy s24 256", "samsung galaxy s24"),
    },
    {
        "product_id": "canon-sony-wh1000xm5",
        "brand": "Sony",
        "model": "WH-1000XM5",
        "title": "Sony WH-1000XM5 Wireless Headphones",
        "sku": "WH1000XM5",
        "upc": "027242925004",
        "aliases": ("sony wh-1000xm5", "wh1000xm5"),
    },
)

FIXTURE_OFFERS: tuple[dict[str, Any], ...] = (
    {
        "marketplace_product_id": "fix-iphone-15-pro-256",
        "title": "Apple iPhone 15 Pro 256GB Natural Titanium",
        "brand": "Apple",
        "model": "iPhone 15 Pro",
        "category": "Smartphones",
        "description": "Fixture demo listing for iPhone 15 Pro",
        "sku": "IP15PRO-256",
        "upc": "194253431413",
        "currency": "PHP",
        "regular_price": 72990.0,
        "sale_price": 69990.0,
        "shipping_cost": 0.0,
        "availability": "in_stock",
        "inventory_quantity": 12,
        "seller_id": "fixture-seller-1",
        "seller_name": "Fixture Mobile Hub",
        "seller_rating": 4.8,
        "marketplace_url": "https://fixtures.dealbrain.local/iphone-15-pro",
        "image_url": "https://fixtures.dealbrain.local/img/iphone-15-pro.jpg",
        "condition": "new",
        "warranty": "12 months",
        "observed_at": "2026-07-20T08:00:00+00:00",
    },
    {
        "marketplace_product_id": "fix-galaxy-s24-256",
        "title": "Samsung Galaxy S24 256GB Onyx Black",
        "brand": "Samsung",
        "model": "Galaxy S24",
        "category": "Smartphones",
        "description": "Fixture demo listing for Galaxy S24",
        "sku": "SGS24-256",
        "upc": "887276798012",
        "currency": "PHP",
        "regular_price": 49990.0,
        "sale_price": 45990.0,
        "shipping_cost": 99.0,
        "availability": "limited",
        "inventory_quantity": 3,
        "seller_id": "fixture-seller-2",
        "seller_name": "Fixture Gadget Store",
        "seller_rating": 4.6,
        "marketplace_url": "https://fixtures.dealbrain.local/galaxy-s24",
        "image_url": "https://fixtures.dealbrain.local/img/galaxy-s24.jpg",
        "condition": "new",
        "warranty": "12 months",
        "observed_at": "2026-07-18T10:00:00+00:00",
    },
)

SIMULATED_LIVE_OFFERS: tuple[dict[str, Any], ...] = (
    {
        "marketplace_product_id": "sim-sony-wh1000xm5",
        "title": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
        "brand": "Sony",
        "model": "WH-1000XM5",
        "category": "Audio",
        "description": "Simulated live listing — NOT a real marketplace connection",
        "sku": "WH1000XM5",
        "upc": "027242925004",
        "currency": "PHP",
        "regular_price": 19990.0,
        "sale_price": 16990.0,
        "shipping_cost": 120.0,
        "availability": "in_stock",
        "inventory_quantity": 25,
        "seller_id": "sim-seller-audio",
        "seller_name": "Simulated Audio Market",
        "seller_rating": 4.9,
        "marketplace_url": "https://simulated.dealbrain.local/sony-wh1000xm5",
        "image_url": "https://simulated.dealbrain.local/img/wh1000xm5.jpg",
        "condition": "new",
        "warranty": "24 months",
        "observed_at": "2026-07-29T01:00:00+00:00",
        "simulated": True,
    },
    {
        "marketplace_product_id": "sim-iphone-15-pro-256",
        "title": "Apple iPhone 15 Pro 256GB",
        "brand": "Apple",
        "model": "iPhone 15 Pro",
        "category": "Smartphones",
        "description": "Simulated live listing — NOT a real marketplace connection",
        "sku": "IP15PRO-256",
        "upc": "194253431413",
        "currency": "PHP",
        "regular_price": 71990.0,
        "sale_price": 68990.0,
        "shipping_cost": 0.0,
        "availability": "in_stock",
        "inventory_quantity": 8,
        "seller_id": "sim-seller-mobile",
        "seller_name": "Simulated Mobile Mart",
        "seller_rating": 4.7,
        "marketplace_url": "https://simulated.dealbrain.local/iphone-15-pro",
        "image_url": "https://simulated.dealbrain.local/img/iphone-15-pro.jpg",
        "condition": "new",
        "warranty": "12 months",
        "observed_at": "2026-07-29T01:05:00+00:00",
        "simulated": True,
    },
)

SAMPLE_CSV = (
    "marketplace_product_id,title,brand,model,category,sku,upc,currency,"
    "regular_price,sale_price,shipping_cost,availability,inventory_quantity,"
    "seller_name,seller_rating,marketplace_url,image_url,condition,warranty\n"
    "imp-iphone-15-pro-256,Apple iPhone 15 Pro 256GB Import,Apple,iPhone 15 Pro,"
    "Smartphones,IP15PRO-256,194253431413,PHP,71000,69500,50,in_stock,5,"
    "Import Seller PH,4.5,https://imported.dealbrain.local/iphone,"
    "https://imported.dealbrain.local/img/iphone.jpg,new,12 months\n"
    "imp-galaxy-s24-256,Samsung Galaxy S24 256GB Import,Samsung,Galaxy S24,"
    "Smartphones,SGS24-256,887276798012,PHP,48000,45500,80,limited,2,"
    "Import Seller PH,4.4,https://imported.dealbrain.local/s24,"
    "https://imported.dealbrain.local/img/s24.jpg,new,12 months\n"
)

SAMPLE_JSON = """
[
  {
    "marketplace_product_id": "imp-sony-wh1000xm5",
    "title": "Sony WH-1000XM5 Import Bundle",
    "brand": "Sony",
    "model": "WH-1000XM5",
    "category": "Audio",
    "sku": "WH1000XM5",
    "upc": "027242925004",
    "currency": "PHP",
    "regular_price": 18990,
    "sale_price": 17490,
    "shipping_cost": 100,
    "availability": "in_stock",
    "inventory_quantity": 7,
    "seller_name": "Import Audio Co",
    "seller_rating": 4.6,
    "marketplace_url": "https://imported.dealbrain.local/wh1000xm5",
    "image_url": "https://imported.dealbrain.local/img/wh1000xm5.jpg",
    "condition": "new",
    "warranty": "24 months"
  }
]
"""
