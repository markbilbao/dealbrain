"""Unit tests for Knowledge Graph node canonicalization."""

from __future__ import annotations

from app.domain.entities.knowledge_graph import NodeType
from app.intelligence.knowledge_graph.canonicalization import (
    NodeCanonicalizationService,
    normalize_token,
)


class TestNormalizeToken:
    def test_lowercases_and_trims(self) -> None:
        assert normalize_token("  ASUS TUF  ") == "asus-tuf"

    def test_collapses_whitespace(self) -> None:
        assert normalize_token("a    b") == "a-b"

    def test_replaces_non_alnum(self) -> None:
        assert normalize_token("A15 (Ryzen 7)!") == "a15-ryzen-7"

    def test_empty_string(self) -> None:
        assert normalize_token("") == ""

    def test_none_like_falsy(self) -> None:
        assert normalize_token(None) == ""  # type: ignore[arg-type]


class TestCanonicalKeyProduct:
    def setup_method(self) -> None:
        self.svc = NodeCanonicalizationService()

    def test_brand_and_label_preferred(self) -> None:
        key = self.svc.canonical_key(
            NodeType.PRODUCT,
            source="shopee",
            source_id="shopee-123",
            label="ASUS TUF Gaming A15",
            brand="ASUS",
        )
        assert key == "product:asus:asus-tuf-gaming-a15"

    def test_same_brand_label_across_marketplaces_collapse(self) -> None:
        shopee_key = self.svc.canonical_key(
            NodeType.PRODUCT,
            source="shopee",
            source_id="shopee-1",
            label="ASUS TUF Gaming A15",
            brand="ASUS",
            marketplace="Shopee",
        )
        lazada_key = self.svc.canonical_key(
            NodeType.PRODUCT,
            source="lazada",
            source_id="lazada-9",
            label="ASUS TUF Gaming A15",
            brand="ASUS",
            marketplace="Lazada",
        )
        assert shopee_key == lazada_key

    def test_falls_back_to_source_and_source_id_without_brand(self) -> None:
        key = self.svc.canonical_key(
            NodeType.PRODUCT,
            source="shopee",
            source_id="shopee-123",
            label="",
        )
        assert key == "product:shopee:shopee-123"

    def test_falls_back_to_label_only(self) -> None:
        key = self.svc.canonical_key(NodeType.PRODUCT, label="Unbranded Widget")
        assert key == "product:unbranded-widget"

    def test_falls_back_to_unknown(self) -> None:
        key = self.svc.canonical_key(NodeType.PRODUCT)
        assert key == "product:unknown"

    def test_string_node_type_accepted(self) -> None:
        key = self.svc.canonical_key("product", brand="ASUS", label="TUF A15")
        assert key.startswith("product:asus:")


class TestCanonicalKeyOtherTypes:
    def setup_method(self) -> None:
        self.svc = NodeCanonicalizationService()

    def test_seller(self) -> None:
        key = self.svc.canonical_key(
            NodeType.SELLER, marketplace="Shopee", label="ASUS Official Store"
        )
        assert key == "seller:shopee:asus-official-store"

    def test_seller_falls_back_to_source(self) -> None:
        key = self.svc.canonical_key(NodeType.SELLER, source="lazada", source_id="seller-9")
        assert key == "seller:lazada:seller-9"

    def test_marketplace(self) -> None:
        assert self.svc.canonical_key(NodeType.MARKETPLACE, label="Lazada") == "marketplace:lazada"

    def test_brand(self) -> None:
        assert self.svc.canonical_key(NodeType.BRAND, label="ASUS") == "brand:asus"

    def test_category_prefers_category_kwarg(self) -> None:
        key = self.svc.canonical_key(NodeType.CATEGORY, category="Laptop", label="Different Label")
        assert key == "category:laptop"

    def test_topic(self) -> None:
        assert self.svc.canonical_key(NodeType.TOPIC, label="Battery Life") == "topic:battery-life"

    def test_evidence_like_types_use_source_and_source_id(self) -> None:
        for node_type in (
            NodeType.REVIEW,
            NodeType.COMMUNITY_EVIDENCE,
            NodeType.EVIDENCE,
            NodeType.AI_SUMMARY,
            NodeType.PRICE_OBSERVATION,
            NodeType.PRICE_HISTORY,
            NodeType.VIDEO,
            NodeType.ACCESSORY,
            NodeType.COMPATIBILITY,
        ):
            key = self.svc.canonical_key(
                node_type, source="reddit", source_id="thread-1", label="Some label"
            )
            assert key == f"{node_type.value}:reddit:thread-1"

    def test_evidence_like_falls_back_to_label_when_no_source_id(self) -> None:
        key = self.svc.canonical_key(NodeType.REVIEW, source="reddit", label="Great review")
        assert key == "review:reddit:great-review"

    def test_generic_fallback_for_unrecognized_type_string(self) -> None:
        key = self.svc.canonical_key("widget", label="A custom widget")
        assert key == "widget:a-custom-widget"

    def test_video_is_evidence_like(self) -> None:
        key = self.svc.canonical_key(NodeType.VIDEO, source="youtube", source_id="vid-1")
        assert key == "video:youtube:vid-1"


class TestDeterministicIds:
    def setup_method(self) -> None:
        self.svc = NodeCanonicalizationService()

    def test_node_id_is_deterministic(self) -> None:
        id_a = self.svc.deterministic_node_id(NodeType.PRODUCT, "product:asus:tuf-a15")
        id_b = self.svc.deterministic_node_id(NodeType.PRODUCT, "product:asus:tuf-a15")
        assert id_a == id_b
        assert id_a.startswith("kg:product:")

    def test_node_id_differs_by_key(self) -> None:
        id_a = self.svc.deterministic_node_id(NodeType.PRODUCT, "product:asus:tuf-a15")
        id_b = self.svc.deterministic_node_id(NodeType.PRODUCT, "product:acer:nitro-v15")
        assert id_a != id_b

    def test_node_id_differs_by_type(self) -> None:
        id_a = self.svc.deterministic_node_id(NodeType.PRODUCT, "same-key")
        id_b = self.svc.deterministic_node_id(NodeType.BRAND, "same-key")
        assert id_a != id_b

    def test_edge_id_is_deterministic(self) -> None:
        id_a = self.svc.deterministic_edge_id("MADE_BY", "n1", "n2")
        id_b = self.svc.deterministic_edge_id("MADE_BY", "n1", "n2")
        assert id_a == id_b
        assert id_a.startswith("kg:edge:")

    def test_edge_id_direction_sensitive(self) -> None:
        forward = self.svc.deterministic_edge_id("SIMILAR_TO", "n1", "n2")
        backward = self.svc.deterministic_edge_id("SIMILAR_TO", "n2", "n1")
        assert forward != backward
