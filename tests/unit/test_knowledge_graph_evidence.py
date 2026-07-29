"""Unit tests for Knowledge Graph evidence, path, and contradiction services."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.domain.entities.knowledge_graph import EdgeType, GraphLimits, NodeType
from app.domain.exceptions import KnowledgeGraphValidationError
from app.intelligence.knowledge_graph.engine import KnowledgeGraphEngine
from app.intelligence.knowledge_graph.evidence import (
    ContradictionService,
    EvidencePathService,
    EvidenceValidationService,
    GraphEvidenceService,
)
from app.intelligence.knowledge_graph.memory import InMemoryKnowledgeGraphRepository


def make_engine() -> KnowledgeGraphEngine:
    repo = InMemoryKnowledgeGraphRepository()
    return KnowledgeGraphEngine(
        repo, limits=GraphLimits(max_depth=3, max_nodes=100, max_edges=200, max_paths=20)
    )


class TestEvidenceValidationService:
    def setup_method(self) -> None:
        self.validator = EvidenceValidationService()

    def test_ai_summary_cannot_be_its_own_evidence(self) -> None:
        engine = make_engine()
        summary = engine.create_node(
            node_type=NodeType.AI_SUMMARY, source="ai", source_id="s1", label="AI Summary"
        )
        with pytest.raises(KnowledgeGraphValidationError):
            self.validator.validate_evidence_refs(subject=summary, evidence_nodes=[summary])

    def test_ai_summary_referencing_other_evidence_produces_warning(self) -> None:
        engine = make_engine()
        product = engine.create_node(
            node_type=NodeType.PRODUCT, source="fixture", source_id="p1", label="X"
        )
        summary = engine.create_node(
            node_type=NodeType.AI_SUMMARY, source="ai", source_id="s1", label="Summary"
        )
        warnings = self.validator.validate_evidence_refs(subject=product, evidence_nodes=[summary])
        assert warnings
        assert "interpretive" in warnings[0]

    def test_non_ai_evidence_produces_no_warning(self) -> None:
        engine = make_engine()
        product = engine.create_node(
            node_type=NodeType.PRODUCT, source="fixture", source_id="p1", label="X"
        )
        review = engine.create_node(
            node_type=NodeType.REVIEW, source="reviews", source_id="r1", label="Review"
        )
        warnings = self.validator.validate_evidence_refs(subject=product, evidence_nodes=[review])
        assert warnings == []

    def test_reject_unsupported_claim_raises(self) -> None:
        with pytest.raises(KnowledgeGraphValidationError):
            self.validator.reject_unsupported_claim("some claim", supported=False)

    def test_reject_unsupported_claim_noop_when_supported(self) -> None:
        # Should not raise.
        self.validator.reject_unsupported_claim("some claim", supported=True)


class TestGraphEvidenceService:
    def test_evidence_for_missing_node(self) -> None:
        engine = make_engine()
        svc = GraphEvidenceService(engine.repository)
        payload = svc.evidence_for("missing")
        assert payload["evidence_nodes"] == []
        assert payload["warnings"] == ["Node not found."]

    def test_evidence_for_collects_reviews_and_community(self) -> None:
        engine = make_engine()
        product = engine.create_node(
            node_type=NodeType.PRODUCT, source="fixture", source_id="p1", label="X"
        )
        review = engine.create_node(
            node_type=NodeType.REVIEW, source="reviews", source_id="r1", label="Great review"
        )
        community = engine.create_node(
            node_type=NodeType.COMMUNITY_EVIDENCE,
            source="reddit",
            source_id="c1",
            label="Reddit thread",
        )
        engine.create_edge(
            edge_type=EdgeType.HAS_REVIEW, from_node_id=product.node_id, to_node_id=review.node_id
        )
        engine.create_edge(
            edge_type=EdgeType.HAS_COMMUNITY_EVIDENCE,
            from_node_id=product.node_id,
            to_node_id=community.node_id,
        )
        svc = GraphEvidenceService(engine.repository)
        payload = svc.evidence_for(product.node_id)
        node_ids = {item["node_id"] for item in payload["evidence_nodes"]}
        assert review.node_id in node_ids
        assert community.node_id in node_ids
        assert payload["data_status"] == "mock"

    def test_evidence_for_follows_evidence_ids_on_edges(self) -> None:
        engine = make_engine()
        product = engine.create_node(
            node_type=NodeType.PRODUCT, source="fixture", source_id="p1", label="X"
        )
        evidence = engine.create_node(
            node_type=NodeType.EVIDENCE, source="dealscore", source_id="e1", label="DealScore 90"
        )
        engine.create_edge(
            edge_type=EdgeType.HAS_EVIDENCE,
            from_node_id=product.node_id,
            to_node_id=evidence.node_id,
            evidence_ids=(evidence.node_id,),
        )
        svc = GraphEvidenceService(engine.repository)
        payload = svc.evidence_for(product.node_id)
        node_ids = {item["node_id"] for item in payload["evidence_nodes"]}
        assert evidence.node_id in node_ids

    def test_evidence_for_deduplicates_nodes(self) -> None:
        engine = make_engine()
        product = engine.create_node(
            node_type=NodeType.PRODUCT, source="fixture", source_id="p1", label="X"
        )
        evidence = engine.create_node(
            node_type=NodeType.EVIDENCE, source="dealscore", source_id="e1", label="DealScore"
        )
        engine.create_edge(
            edge_type=EdgeType.HAS_EVIDENCE,
            from_node_id=product.node_id,
            to_node_id=evidence.node_id,
            evidence_ids=(evidence.node_id,),
        )
        svc = GraphEvidenceService(engine.repository)
        payload = svc.evidence_for(product.node_id)
        node_ids = [item["node_id"] for item in payload["evidence_nodes"]]
        assert node_ids.count(evidence.node_id) == 1

    def test_evidence_for_produces_ai_summary_warning(self) -> None:
        engine = make_engine()
        product = engine.create_node(
            node_type=NodeType.PRODUCT, source="fixture", source_id="p1", label="X"
        )
        summary = engine.create_node(
            node_type=NodeType.AI_SUMMARY, source="ai", source_id="s1", label="Summary"
        )
        # evidence_ids is followed regardless of edge type, so this surfaces the AI
        # summary as evidence and triggers the "must not replace evidence" warning.
        engine.create_edge(
            edge_type=EdgeType.HAS_AI_SUMMARY,
            from_node_id=product.node_id,
            to_node_id=summary.node_id,
            evidence_ids=(summary.node_id,),
        )
        svc = GraphEvidenceService(engine.repository)
        payload = svc.evidence_for(product.node_id)
        assert payload["warnings"]

    def test_is_stale_by_explicit_metadata_flag(self) -> None:
        engine = make_engine()
        node = engine.create_node(
            node_type=NodeType.EVIDENCE,
            source="fixture",
            source_id="e1",
            label="Old evidence",
            metadata={"stale": True},
        )
        assert GraphEvidenceService.is_stale(node) is True

    def test_is_stale_by_age(self) -> None:
        import dataclasses

        engine = make_engine()
        node = engine.create_node(
            node_type=NodeType.EVIDENCE, source="fixture", source_id="e1", label="Evidence"
        )
        stale_node = dataclasses.replace(
            node,
            updated_at=datetime.now(UTC) - timedelta(days=200),
            created_at=datetime.now(UTC) - timedelta(days=200),
        )
        assert GraphEvidenceService.is_stale(stale_node) is True

    def test_is_stale_fresh_node_is_not_stale(self) -> None:
        engine = make_engine()
        node = engine.create_node(
            node_type=NodeType.EVIDENCE, source="fixture", source_id="e1", label="Evidence"
        )
        assert GraphEvidenceService.is_stale(node) is False

    def test_is_stale_no_timestamp_is_not_stale(self) -> None:
        import dataclasses

        engine = make_engine()
        node = engine.create_node(
            node_type=NodeType.EVIDENCE, source="fixture", source_id="e1", label="Evidence"
        )
        untimed = dataclasses.replace(node, created_at=None, updated_at=None)
        assert GraphEvidenceService.is_stale(untimed) is False


class TestEvidencePathService:
    def test_supporting_paths_delegates_to_engine(self) -> None:
        engine = make_engine()
        product = engine.create_node(
            node_type=NodeType.PRODUCT, source="fixture", source_id="p1", label="X", brand="ASUS"
        )
        brand = engine.create_node(
            node_type=NodeType.BRAND, source="fixture", source_id="asus", label="ASUS"
        )
        engine.create_edge(
            edge_type=EdgeType.MADE_BY, from_node_id=product.node_id, to_node_id=brand.node_id
        )
        svc = EvidencePathService(engine)
        paths = svc.supporting_paths(product.node_id, brand.node_id)
        assert len(paths) == 1

    def test_path_score_uses_minimum_confidence(self) -> None:
        engine = make_engine()
        product = engine.create_node(
            node_type=NodeType.PRODUCT, source="fixture", source_id="p1", label="X"
        )
        mid = engine.create_node(
            node_type=NodeType.TOPIC, source="fixture", source_id="t1", label="Topic"
        )
        end = engine.create_node(
            node_type=NodeType.EVIDENCE, source="fixture", source_id="e1", label="Evidence"
        )
        e1 = engine.create_edge(
            edge_type=EdgeType.HAS_TOPIC,
            from_node_id=product.node_id,
            to_node_id=mid.node_id,
            confidence=0.9,
        )
        e2 = engine.create_edge(
            edge_type=EdgeType.SUPPORTED_BY,
            from_node_id=mid.node_id,
            to_node_id=end.node_id,
            confidence=0.4,
        )
        svc = EvidencePathService(engine)
        score, band = svc.path_score([e1.edge_id, e2.edge_id])
        assert score == pytest.approx(0.4)
        assert band == "low"

    def test_path_score_ignores_missing_edges(self) -> None:
        engine = make_engine()
        svc = EvidencePathService(engine)
        score, band = svc.path_score(["does-not-exist"])
        assert score == 0.0
        assert band == "low"


class TestContradictionService:
    def test_contradictions_for_node(self) -> None:
        engine = make_engine()
        left = engine.create_node(
            node_type=NodeType.COMMUNITY_EVIDENCE,
            source="reddit",
            source_id="c1",
            label="Battery good",
        )
        right = engine.create_node(
            node_type=NodeType.REVIEW, source="reviews", source_id="r1", label="Battery bad"
        )
        engine.create_edge(
            edge_type=EdgeType.CONTRADICTS,
            from_node_id=left.node_id,
            to_node_id=right.node_id,
            confidence=0.7,
            evidence_ids=(left.node_id, right.node_id),
        )
        svc = ContradictionService(engine.repository)
        results = svc.contradictions_for(left.node_id)
        assert len(results) == 1
        assert results[0]["confidence_band"] == "medium"
        assert results[0]["other_label"] == "Battery bad"

    def test_no_contradictions_returns_empty(self) -> None:
        engine = make_engine()
        node = engine.create_node(
            node_type=NodeType.PRODUCT, source="fixture", source_id="p1", label="X"
        )
        svc = ContradictionService(engine.repository)
        assert svc.contradictions_for(node.node_id) == []

    def test_contradictions_visible_from_either_endpoint(self) -> None:
        engine = make_engine()
        left = engine.create_node(
            node_type=NodeType.COMMUNITY_EVIDENCE, source="reddit", source_id="c1", label="A"
        )
        right = engine.create_node(
            node_type=NodeType.REVIEW, source="reviews", source_id="r1", label="B"
        )
        engine.create_edge(
            edge_type=EdgeType.CONTRADICTS, from_node_id=left.node_id, to_node_id=right.node_id
        )
        svc = ContradictionService(engine.repository)
        assert svc.contradictions_for(left.node_id)
        assert svc.contradictions_for(right.node_id)
