"""Product parser extraction rules."""

from app.intelligence.product_parser.rules.base import ParseRule
from app.intelligence.product_parser.rules.brand import BrandRule
from app.intelligence.product_parser.rules.color import ColorRule
from app.intelligence.product_parser.rules.connector import ConnectorRule
from app.intelligence.product_parser.rules.family_model import FamilyModelRule
from app.intelligence.product_parser.rules.screen_size import ScreenSizeRule
from app.intelligence.product_parser.rules.storage import StorageRule


def default_rules() -> list[ParseRule]:
    """Return the default rule set (engine sorts by priority)."""
    return [
        BrandRule(),
        FamilyModelRule(),
        StorageRule(),
        ConnectorRule(),
        ColorRule(),
        ScreenSizeRule(),
    ]


__all__ = [
    "BrandRule",
    "ColorRule",
    "ConnectorRule",
    "FamilyModelRule",
    "ParseRule",
    "ScreenSizeRule",
    "StorageRule",
    "default_rules",
]
