"""Unit tests for the KnowledgeGraphService application facade."""

from __future__ import annotations

import pytest
from app.domain.entities.knowledge_graph import EdgeType, GraphLimits, NodeType
from app.domain.exceptions import (
    KnowledgeGraphNotFoundError,
    KnowledgeGraphValidationError,
)
from app.intelligence.knowledge_graph.engine import KnowledgeGraphEngine
from app.intelligence.knowledge_graph.fixtures import DEMO_PRODUCT_ID, DEMO_PRODUCT_LABEL
from app.intelligence.knowledge_graph.memory import InMemoryKnowledgeGraphRepository
from app.services.knowledge_graph_service import KnowledgeGraphService


def make_service(**kwargs) -> KnowledgeGraphService:
    repo = InMemoryKnowledgeGraphRepository()
    engine = KnowledgeGraphEngine(
        repo, limits=GraphLimits(max_depth=3, max_nodes=100, max_edges=200, max_paths=20)
    )
    return KnowledgeGraphService(engine, **kwargs)


class TestEnabledFlag:
    def test_disabled_service_rejects_reads(self) -> None:
        service = make_service(enabled=False)
        with pytest.raises(KnowledgeGraphValidationError):
            service.demo()

    def test_disabled_service_rejects_create_node(self) -> None:
        service = make_service(enabled=False)
        with pytest.raises(KnowledgeGraphValidationError):
            service.create_node(
                node_type=NodeType.PRODUCT, source="fixture", source_id="p1", label="X"
            )

    def test_disabled_service_rejects_import_snapshot(self) -> None:
        service = make_service(enabled=False)
        with pytest.raises(KnowledgeGraphValidationError):
            service.import_snapshot({"schema_version": 1, "nodes": [], "edges": []})

    def test_shopping_assistant_evidence_returns_empty_when_disabled(self) -> None:
        service = make_service(enabled=False)
        assert service.shopping_assistant_evidence(["p1"]) == []

    def test_enabled_by_default(self) -> None:
        service = make_service()
        assert service.enabled is True


class TestSeedingAndDemo:
    def test_demo_lazily_seeds_and_returns_subgraph(self) -> None:
        service = make_service()
        subgraph = service.demo()
        assert subgraph.root_node is not None
        assert subgraph.root_node.label == DEMO_PRODUCT_LABEL

    def test_ensure_seeded_only_seeds_once(self) -> None:
        service = make_service()
        service.ensure_seeded()
        count_after_first = len(service._engine.repository.nodes.all())  # noqa: SLF001
        service.ensure_seeded()
        assert len(service._engine.repository.nodes.all()) == count_after_first  # noqa: SLF001


class TestProductGraphAndNodes:
    def test_product_graph_by_source_id(self) -> None:
        service = make_service()
        subgraph = service.product_graph(DEMO_PRODUCT_ID)
        assert subgraph.root_node is not None
        assert subgraph.summary["brands"]

    def test_product_graph_missing_product_raises(self) -> None:
        service = make_service()
        with pytest.raises(KnowledgeGraphNotFoundError):
            service.product_graph("does-not-exist")

    def test_get_node_missing_raises(self) -> None:
        service = make_service()
        with pytest.raises(KnowledgeGraphNotFoundError):
            service.get_node("missing")

    def test_get_node_found_after_seeding(self) -> None:
        service = make_service()
        subgraph = service.demo()
        node = service.get_node(subgraph.root_node.node_id)
        assert node.node_id == subgraph.root_node.node_id


class TestNeighborsAndRelationships:
    def test_neighbors_of_demo_product(self) -> None:
        service = make_service()
        demo = service.demo()
        neighbors = service.neighbors(demo.root_node.node_id)
        assert neighbors.nodes

    def test_relationships_lists_outgoing_and_incoming(self) -> None:
        service = make_service()
        demo = service.demo()
        payload = service.relationships(demo.root_node.node_id)
        assert payload["node"]["node_id"] == demo.root_node.node_id
        assert isinstance(payload["outgoing"], list)
        assert isinstance(payload["incoming"], list)

    def test_relationships_missing_node_raises(self) -> None:
        service = make_service()
        with pytest.raises(KnowledgeGraphNotFoundError):
            service.relationships("missing")


class TestFindPaths:
    def test_find_paths_between_product_and_brand(self) -> None:
        service = make_service()
        demo = service.demo()
        brand_edges = [e for e in demo.edges if e.edge_type == EdgeType.MADE_BY]
        assert brand_edges
        payload = service.find_paths(demo.root_node.node_id, brand_edges[0].to_node_id)
        assert payload["paths"]
        assert payload["limits"]["max_depth"] <= 3

    def test_find_paths_missing_node_raises(self) -> None:
        service = make_service()
        service.ensure_seeded()
        with pytest.raises(KnowledgeGraphNotFoundError):
            service.find_paths("missing-1", "missing-2")


class TestEvidenceAndExplain:
    def test_evidence_missing_node_raises_not_found(self) -> None:
        service = make_service()
        with pytest.raises(KnowledgeGraphNotFoundError):
            service.evidence("missing")

    def test_evidence_for_demo_product(self) -> None:
        service = make_service()
        demo = service.demo()
        payload = service.evidence(demo.root_node.node_id)
        assert "evidence_nodes" in payload
        assert "contradictions" in payload

    def test_explain_requires_node_or_product_pair(self) -> None:
        service = make_service()
        with pytest.raises(KnowledgeGraphValidationError):
            service.explain()

    def test_explain_by_node_ids(self) -> None:
        service = make_service()
        demo = service.demo()
        brand_edges = [e for e in demo.edges if e.edge_type == EdgeType.MADE_BY]
        explanation = service.explain(
            from_node_id=demo.root_node.node_id, to_node_id=brand_edges[0].to_node_id
        )
        assert explanation.supported is True

    def test_explain_by_product_ids(self) -> None:
        service = make_service()
        service.ensure_seeded()
        explanation = service.explain(
            from_product_id=DEMO_PRODUCT_ID, to_product_id="sa-laptop-nitro-v15"
        )
        assert explanation.claim


class TestQuery:
    def test_query_sellers(self) -> None:
        service = make_service()
        service.ensure_seeded()
        sellers = service.query("sellers", product_id=DEMO_PRODUCT_ID)
        assert sellers

    def test_query_similar(self) -> None:
        service = make_service()
        service.ensure_seeded()
        similar = service.query("similar", product_id=DEMO_PRODUCT_ID)
        assert isinstance(similar, list)

    def test_query_unsupported_kind_raises(self) -> None:
        service = make_service()
        with pytest.raises(KnowledgeGraphValidationError):
            service.query("not-a-real-kind", product_id=DEMO_PRODUCT_ID)


class TestSnapshots:
    def test_export_snapshot_after_seed(self) -> None:
        service = make_service()
        snapshot = service.export_snapshot()
        assert snapshot.schema_version == 1
        assert len(snapshot.nodes) > 0

    def test_import_snapshot_replaces_graph_and_marks_seeded(self) -> None:
        service = make_service()
        exported = service.export_snapshot()
        fresh = make_service()
        fresh.import_snapshot(exported)
        assert fresh._seeded is True  # noqa: SLF001
        assert len(fresh._engine.repository.nodes.all()) == len(exported.nodes)  # noqa: SLF001

    def test_import_malformed_snapshot_rejected(self) -> None:
        service = make_service()
        with pytest.raises(KnowledgeGraphValidationError):
            service.import_snapshot({"schema_version": 999, "nodes": [], "edges": []})

    def test_clear_fixture_graph_resets_seeded_flag(self) -> None:
        service = make_service()
        service.ensure_seeded()
        service.clear_fixture_graph()
        assert service._seeded is False  # noqa: SLF001
        assert service._engine.repository.nodes.all() == []  # noqa: SLF001


class TestCreateNodeAndEdge:
    def test_create_node_via_service(self) -> None:
        service = make_service()
        node = service.create_node(
            node_type=NodeType.PRODUCT, source="fixture", source_id="p9", label="Custom Product"
        )
        assert node.label == "Custom Product"

    def test_create_edge_via_service(self) -> None:
        service = make_service()
        product = service.create_node(
            node_type=NodeType.PRODUCT, source="fixture", source_id="p9", label="Custom Product"
        )
        brand = service.create_node(
            node_type=NodeType.BRAND, source="fixture", source_id="b1", label="BrandX"
        )
        edge = service.create_edge(
            edge_type=EdgeType.MADE_BY, from_node_id=product.node_id, to_node_id=brand.node_id
        )
        assert edge.edge_type == EdgeType.MADE_BY

    def test_create_edge_unsupported_type_raises(self) -> None:
        service = make_service()
        product = service.create_node(
            node_type=NodeType.PRODUCT, source="fixture", source_id="p9", label="Custom Product"
        )
        with pytest.raises(KnowledgeGraphValidationError):
            service.create_edge(
                edge_type="NOT_REAL", from_node_id=product.node_id, to_node_id=product.node_id
            )


class TestShoppingAssistantEvidence:
    def test_returns_structured_evidence_for_known_product(self) -> None:
        service = make_service()
        items = service.shopping_assistant_evidence([DEMO_PRODUCT_ID])
        assert items
        assert all("evidence_id" in item for item in items)

    def test_unknown_product_ids_are_skipped_not_raised(self) -> None:
        service = make_service()
        items = service.shopping_assistant_evidence(["does-not-exist"])
        assert items == []

    def test_no_secrets_in_evidence_payload(self) -> None:
        service = make_service()
        items = service.shopping_assistant_evidence([DEMO_PRODUCT_ID])
        blob = str(items).lower()
        assert "api_key" not in blob
        assert "secret" not in blob


class TestMeta:
    def test_meta_reports_no_external_database(self) -> None:
        service = make_service()
        meta = service.meta()
        assert meta["external_graph_database"] is False
        assert meta["confidence_method"] == "minimum_edge_confidence"
        assert "product" in meta["node_types"]
        assert "MADE_BY" in meta["edge_types"]

    def test_meta_reports_demo_product(self) -> None:
        service = make_service()
        meta = service.meta()
        assert meta["demo_product_id"] == DEMO_PRODUCT_ID
        assert meta["demo_product_name"] == DEMO_PRODUCT_LABEL

    def test_meta_reports_limits(self) -> None:
        service = make_service()
        meta = service.meta()
        assert meta["limits"]["max_depth"] == 3
        assert meta["limits"]["max_nodes"] == 100
