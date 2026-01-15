# audiomason/pipeline/orchestrator.py
from typing import Any, Protocol


class PipelineStep(Protocol):
    """Protocol for all pipeline steps."""
    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        ...


class PipelineOrchestrator:
    """Executes a series of pipeline steps in order."""

    def __init__(self, steps: list[PipelineStep]):
        self.steps = steps

    def run_pipeline(self, context: dict[str, Any]) -> dict[str, Any]:
        for step in self.steps:
            context = step.run(context)
        return context
