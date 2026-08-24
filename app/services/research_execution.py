"""Future certified research execution interface.

Sprint 31 defines the entrypoint. It does not execute providers, fetch
live merchant data, or create a new canonical decision.
"""

from __future__ import annotations

from app.domain.entities.research_execution import ResearchExecutionPlan, ResearchExecutionTrace


def execute_research_plan(plan: ResearchExecutionPlan) -> ResearchExecutionTrace:
    """Reserved for Sprint 38 after Sprints 32–36 certify providers."""

    del plan
    raise NotImplementedError(
        "Certified live research execution is not implemented. "
        "Sprint 31 may only plan. Sprint 38 owns live execution after "
        "Sprints 32–36 certify market/provider paths."
    )
