import os
import importlib
import pkgutil
from datetime import datetime, timedelta
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from commands import base_command
from utils import SlackErrorHandler

class SlackBot:
    _instance = None

    @classmethod
    def get_instance(cls):
        """Get the singleton instance of the bot."""
        return cls._instance

    def __init__(self, client: AsyncWebClient):
        self.client = client
        self.commands = {}
        self.bot_user_id = None
        self._load_commands()
        # Set this instance as the singleton
        SlackBot._instance = self

    async def initialize(self):
        """Initialize bot by getting its user ID."""
        try:
            auth_response = await self.client.auth_test()
            self.bot_user_id = auth_response['user_id']
            print(f"Bot initialized with user ID: {self.bot_user_id}")
        except SlackApiError as e:
            print(f"Error getting bot user ID: {e.response['error']}")
            raise

    def _load_commands(self):
        """Dynamically load all command modules from the commands package."""
        commands_package = 'commands'
        for _, name, _ in pkgutil.iter_modules([commands_package]):
            module = importlib.import_module(f'{commands_package}.{name}')
            for item_name in dir(module):
                item = getattr(module, item_name)
                if (isinstance(item, type) and 
                    issubclass(item, base_command.BaseCommand) and 
                    item != base_command.BaseCommand):
                    command_instance = item()
                    self.commands[command_instance.keyword] = command_instance

    async def handle_message(self, event):
        """Handle incoming message events."""
        channel = event.get('channel')
        
        try:
            if not self.bot_user_id:
                await self.initialize()

            text = event.get('text', '').strip()
            user = event.get('user')

            # Check if the message mentions the bot
            bot_mention = f"<@{self.bot_user_id}>"
            if not text or not bot_mention in text:
                return

            # Extract command text after the mention
            command_text = text.split(bot_mention, 1)[1].strip()
            command_parts = command_text.split()
            
            if not command_parts:
                # If mentioned without a command, show help
                command_parts = ['help']

            keyword = command_parts[0]
            args = command_parts[1:]

            if keyword in self.commands:
                try:
                    response = await self.commands[keyword].execute(
                        client=self.client,
                        channel=channel,
                        user=user,
                        args=args
                    )
                    
                    if response:
                        await self.client.chat_postMessage(
                            channel=channel,
                            text=response
                        )
                except SlackApiError as e:
                    await SlackErrorHandler.handle_error_with_retry(
                        self.client,
                        channel,
                        e
                    )
            else:
                # Direct users to the help command for unknown commands
                await self.client.chat_postMessage(
                    channel=channel,
                    text=f"Unknown command '{keyword}'. Type @<bot> help to see available commands."
                )
                
        except SlackApiError as e:
            await SlackErrorHandler.handle_error_with_retry(
                self.client,
                channel,
                e
            )
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            try:
                await self.client.chat_postMessage(
                    channel=channel,
                    text="Sorry, I encountered an unexpected error while processing your command."
                )
            except:
                pass  # If we can't send the error message, just log it
