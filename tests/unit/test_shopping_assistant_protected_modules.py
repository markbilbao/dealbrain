"""Guard: Sprint 13 must not modify protected intelligence / ops modules."""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# SHA-256 digests of protected modules as of Sprint 13 branch creation (main + Sprint 12).
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
    "app/services/review_service.py": (
        "b633f325bbc1edd050be95c4176b37aaa1524408e536b7bd68f532db4d452ba3"
    ),
    "app/intelligence/reviews/memory.py": (
        "623c98c3c21550e072db6eab9c245db36d00734884f258ed48e5295fa94b9e6f"
    ),
    "app/intelligence/reviews/base.py": (
        "efb326b75d421936914112bb532774cd23eb3c79c69d2e941150982754867b6b"
    ),
    "app/intelligence/reviews/fixtures.py": (
        "7d582408fbdc908b9805a50ebd2d74991de4578a5f54199a5d0d2d647690c447"
    ),
    "app/api/v1/endpoints/reviews.py": (
        "29fca0c0d73b845ee28165352eeb0b14803c5d6cbb0619ec77a96321aeacc453"
    ),
    "app/domain/entities/review.py": (
        "b54a560dc949d9549812d8e557fe061b989fad2868936c537f71f97ea4218966"
    ),
    # AI Review Summary / multi-model (Sprint 12) — protected for Sprint 13.
    "app/services/review_summary_service.py": (
        "8cae6c78fe7f23c85d13fc6de654516c7b0b79c7a87a0bbd7438cd32a841b3e3"
    ),
    "app/intelligence/review_summary/deterministic.py": (
        "c25240da6eca7cbebf82d0cb6bd3833645c398d170e01c7bad8c50ebd4e4adff"
    ),
    "app/intelligence/review_summary/memory.py": (
        "1013a47983f39400f5b005fd4eea0303aee8610c7940cd94b9edf2b7b8cdb7b5"
    ),
    "app/intelligence/review_summary/fixtures.py": (
        "f6702d018355ade58044fc5605ce916ccee490bfa2dc0c7ceda99043e719e02a"
    ),
    "app/intelligence/review_summary/registry.py": (
        "a99ec4e23f67a25b309b956199cd6d495bbc05c34640e5f5f152eaa4f5f0aa03"
    ),
    "app/intelligence/review_summary/health.py": (
        "a4cd917339de600d6c3c8ba26d40bffae279e43b15f56dfead3df4aec4978825"
    ),
    "app/intelligence/review_summary/validator.py": (
        "88d513c6b0f4d7f94cee141a042732f5391794767d612d12036ae74d16eafac6"
    ),
    "app/intelligence/review_summary/consensus.py": (
        "16b063f3a711314988bdb6b04e932b32fc6ce71f7fb3d40281d35785602152c6"
    ),
    "app/intelligence/review_summary/orchestrator.py": (
        "201fdab64be573b91ef2440d663a6a693fa401fe8087d2b3188c3856ad1b30e9"
    ),
    "app/infrastructure/ai/transports.py": (
        "c731c556a2ebc9936727508b146b6f206807a3443cacf51ba89db052a8042fed"
    ),
    "app/infrastructure/ai/review_providers/base.py": (
        "c0de9034bbd860ce68be9bf7a2b14db3132511e64396c6a6d88cadd8bf3f0ca5"
    ),
    "app/infrastructure/ai/review_providers/parsing.py": (
        "a791fee2b5a41373f3cdd42c1738b5b9d3d73750c27185b760ba6a879a185e9e"
    ),
    "app/infrastructure/ai/review_providers/openai_provider.py": (
        "710ea5d6cefcfdec4e913e1134c9397d93109b19ecf9e750582e6c38a1ad7228"
    ),
    "app/infrastructure/ai/review_providers/claude_provider.py": (
        "a1bcf5c4f72eb9048c283558399a2b0b56fedc2de40bdd877f5143f90a4a8e64"
    ),
    "app/infrastructure/ai/review_providers/gemini_provider.py": (
        "94504e405be1e3e6736d0e7e2fa95f79cc47da9b93b353a8f30ff3382041078e"
    ),
    "app/infrastructure/ai/review_providers/deterministic_provider.py": (
        "dd3dede8f312d73ea8a31dd4131f93bfa499621c276a0e29545224c4792587b0"
    ),
    "app/api/v1/endpoints/review_summary.py": (
        "d82cc269f4c250be83e6095a99b2c0b1e9383cba49b0f8371753c53a4431bd82"
    ),
    "app/domain/entities/review_summary.py": (
        "296f149f39e6b2ae6fbdc4683093ac595244c35445e05862f82475d7977d1c0a"
    ),
    "app/domain/entities/review_analysis.py": (
        "d2de5a29b7e36cb126d522c95dfcef62e11b4180cd5ab4cc1625f2e5ca756351"
    ),
    "app/domain/interfaces/ai_review_provider.py": (
        "b1b41bb0112164688b6cf604faefa2777971ceb802a9cb563b711463809e6d30"
    ),
}


def test_protected_modules_unchanged() -> None:
    for relative, expected in PROTECTED_DIGESTS.items():
        path = ROOT / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == expected, f"Protected module changed: {relative}"


def test_shopping_assistant_module_is_independent() -> None:
    """Shopping Assistant may compose services but must not rewrite protected ones."""
    assistant = ROOT / "app/services/shopping_assistant_service.py"
    assert assistant.is_file()
    text = assistant.read_text(encoding="utf-8")
    assert "ShoppingAssistantService" in text
    # Must not embed vendor SDKs or provider adapters directly.
    assert "OpenAIShoppingProvider" not in text
    assert "ClaudeShoppingProvider" not in text
    assert "GeminiShoppingProvider" not in text
    assert "import openai" not in text.lower()
    assert "import anthropic" not in text.lower()

    review_summary = ROOT / "app/services/review_summary_service.py"
    assert "ShoppingAssistantService" not in review_summary.read_text(encoding="utf-8")

    watchlist = ROOT / "app/services/watchlist_service.py"
    assert "ShoppingAssistantService" not in watchlist.read_text(encoding="utf-8")

    dealscore = ROOT / "app/intelligence/dealscore/engine.py"
    assert "ShoppingAssistantService" not in dealscore.read_text(encoding="utf-8")

    recommendation = ROOT / "app/intelligence/recommendation/engine.py"
    assert "ShoppingAssistantService" not in recommendation.read_text(encoding="utf-8")
