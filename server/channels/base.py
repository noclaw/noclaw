"""Base class for communication channel plugins."""


class Channel:
    """Base class for NoClaw communication channels.

    Subclasses must implement start(), stop(), and is_configured().
    Place channel modules in server/channels/ — they are auto-discovered on startup.
    """

    name: str = "unknown"

    def __init__(self, assistant):
        self.assistant = assistant

    async def start(self):
        """Start the channel (connect to platform, begin listening)."""
        raise NotImplementedError

    async def stop(self):
        """Stop the channel (disconnect cleanly)."""
        raise NotImplementedError

    @classmethod
    def is_configured(cls) -> bool:
        """Return True if required env vars are set for this channel."""
        return False
