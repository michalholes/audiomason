def enrich_metadata(title: str, author: str, description: str = '') -> dict:
    return {
        'suggested_tags': ['audiobook', 'literature'],
        'ai_notes': f'Stubbed AI response for {title} by {author}.'
    }
