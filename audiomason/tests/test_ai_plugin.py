from audiomason.plugins.ai_assist import enrich_metadata

def test_ai_plugin_stub_response():
    """Ensure the stubbed AI plugin returns predictable output."""
    data = enrich_metadata("1984", "George Orwell")
    assert "suggested_tags" in data
    assert "ai_notes" in data
    assert "1984" in data["ai_notes"]
