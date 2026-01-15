from audiomason.pipeline.orchestrator import PipelineOrchestrator
from audiomason.pipeline.steps.import_audio import ImportAudioStep
from audiomason.pipeline.steps.enrich_metadata import EnrichMetadataStep

def test_pipeline_execution():
    """Ensure that the stubbed pipeline runs end-to-end."""
    steps = [ImportAudioStep(), EnrichMetadataStep()]
    orchestrator = PipelineOrchestrator(steps)
    result = orchestrator.run_pipeline({})
    assert isinstance(result, dict)
