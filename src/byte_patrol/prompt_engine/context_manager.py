"""Manage context for large changes in code reviews."""

class ContextManager:
    """
    Handle prompt context partitioning to fit AI model limits.
    """
    def __init__(self, max_tokens: int = 2048):
        self.max_tokens = max_tokens
        self.chunks = []

    def split_context(self, text: str) -> list[str]:
        """
        Split text into chunks not exceeding max_tokens.
        """
        # TODO: implement splitting logic
        return [text]
