from abc import ABC, abstractmethod
from slack_sdk.web.async_client import AsyncWebClient

class BaseCommand(ABC):
    """Base class for all bot commands."""
    
    @property
    @abstractmethod
    def keyword(self) -> str:
        """The command keyword that triggers this command."""
        pass

    @property
    @abstractmethod
    def help_text(self) -> str:
        """Help text explaining how to use this command."""
        pass

    @abstractmethod
    async def execute(self, client: AsyncWebClient, channel: str, user: str, args: list) -> str:
        """
        Execute the command.
        
        Args:
            client: Slack AsyncWebClient instance
            channel: The channel ID where the command was invoked
            user: The user ID who invoked the command
            args: List of command arguments
            
        Returns:
            str: The response message to send back to the channel
        """
        pass
