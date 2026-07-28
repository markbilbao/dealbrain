"""Guard: Sprint 11 must not modify protected intelligence / ops modules."""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# SHA-256 digests of protected modules as of Sprint 11 branch creation (main).
PROTECTED_DIGESTS = {
    "app/intelligence/product_parser/engine.py": (
        "888dcd01639362dd453fbe9d1e0cbd4df16e449ecd1979ee9b4eea5a1c00e239"
    ),
    "app/intelligence/product_parser/tokenizer.py": (
        "239920b7b565ed8c99c86aa57c3ac664fb430e6d83d050458818ace4ef0c3ab5"
    ),
    "app/intelligence/canonical_registry/identity.py": (
        "25884242efa83eadf5e417a8d3824ea6cf9232d76584cfe98abeb73b2322a5f9"
    ),
    "app/intelligence/product_matcher/exact_variant.py": (
        "0c58d432b8ae79eb401b18814ca1dd6780f520eeb0703243092fe0a1b4faa7ea"
    ),
    "app/intelligence/dealscore/engine.py": (
        "6551417b32f8201ab4c7565e2970d71d2f3fd3ce6ef51aaa1b0a3dd1ebdfabf1"
    ),
    "app/intelligence/recommendation/engine.py": (
        "eeca61d051297f84ffb64aa2ad726a36b9306a61293919c444b3733681ef3df0"
    ),
    "app/intelligence/price_history/statistics.py": (
        "f864fe69b31441048b48e036edce022d4d13ded22ccb3ecccffa58d0723bd00c"
    ),
    "app/intelligence/collection/base.py": (
        "7dbc40b9f0f22302c46ba79e6bd6ba5f55234f908223a02e12c28850ef88dbd6"
    ),
    "app/services/marketplace_collection_service.py": (
        "2ea3ee962bc2b1907afdfc974186de1c2856fc0e93e81ea21879e204a1b549ae"
    ),
    "app/services/collection_operations_service.py": (
        "4b2d345aee1c36be0ee9a0669e5fcab5c39d506c033ee670d7f9b2847220135c"
    ),
    "app/services/watchlist_service.py": (
        "e83f98f59901e2c272d6f9a68795f383423aba2c0cf4a20df104e54f3c70d7ad"
    ),
    "app/intelligence/watchlists/memory.py": (
        "7697986703f1eaae6cbbd196aa0230915c540bbcb001cb1bca29224125be4bf3"
    ),
}


def test_protected_modules_unchanged() -> None:
    for relative, expected in PROTECTED_DIGESTS.items():
        path = ROOT / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == expected, f"Protected module changed: {relative}"


def test_review_module_is_independent() -> None:
    """Review Intelligence must not rewrite watchlist / collection ops code."""
    review_service = ROOT / "app/services/review_service.py"
    assert review_service.is_file()
    text = review_service.read_text(encoding="utf-8")
    assert "ReviewService" in text
    assert "Watchlist" not in text
    assert "CollectionOperations" not in text

    ops = ROOT / "app/services/collection_operations_service.py"
    assert "ReviewService" not in ops.read_text(encoding="utf-8")

    watchlist = ROOT / "app/services/watchlist_service.py"
    assert "ReviewService" not in watchlist.read_text(encoding="utf-8")
