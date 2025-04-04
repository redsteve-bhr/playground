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
            # The auth_test is returning the user ID, not the bot ID
            # We'll override this in the handle_message method with the correct ID
            # from the event authorizations
            self.bot_user_id = auth_response['user_id']
            print(f"Bot temporary ID from auth_test: {self.bot_user_id}")
        except SlackApiError as e:
            print(f"Error getting bot user ID: {e.response['error']}")
            raise

    def _load_commands(self):
        """Dynamically load all command modules from the commands package."""
        commands_package = 'commands'
        print(f"Loading commands from {commands_package} package")
        for _, name, _ in pkgutil.iter_modules([commands_package]):
            print(f"Found module: {name}")
            module = importlib.import_module(f'{commands_package}.{name}')
            for item_name in dir(module):
                item = getattr(module, item_name)
                if (isinstance(item, type) and 
                    issubclass(item, base_command.BaseCommand) and 
                    item != base_command.BaseCommand):
                    command_instance = item()
                    self.commands[command_instance.keyword] = command_instance
                    print(f"Loaded command: {command_instance.keyword} - {command_instance.help_text}")        
        print(f"Total commands loaded: {len(self.commands)}")
        print(f"Available commands: {', '.join(self.commands.keys())}")

    async def handle_message(self, event):
        """Handle incoming message events."""
        channel = event.get('channel')
        print(f"Processing message in channel: {channel}")
        
        try:
            # Get the actual bot ID from the authorizations in the event
            # This is more reliable than auth_test
            if 'authorizations' in event:
                auth_info = event.get('authorizations', [])
                if auth_info and 'user_id' in auth_info[0]:
                    actual_bot_id = auth_info[0]['user_id']
                    if self.bot_user_id != actual_bot_id:
                        print(f"Updating bot ID from {self.bot_user_id} to {actual_bot_id}")
                        self.bot_user_id = actual_bot_id

            if not self.bot_user_id:
                await self.initialize()
                print(f"Bot initialized with user ID: {self.bot_user_id}")

            text = event.get('text', '').strip()
            user = event.get('user')
            print(f"Message from user: {user}, text: '{text}'")

            # Look for bot mention in the text - check both possible formats
            # Either '<@BOT_ID>' format or directly extract from message text
            mention_pattern = f"<@{self.bot_user_id}>"
            
            # For app_mention events, we know the bot was mentioned 
            # So if we can't find the mention pattern, we'll extract the command directly
            if mention_pattern in text:
                # Extract command after the mention
                command_text = text.split(mention_pattern, 1)[1].strip()
            else:
                # Just take everything after the first mention (which should be the bot)
                matches = text.split('<@', 1)
                if len(matches) > 1:
                    # Format: <@U0783GA3C3H> command
                    rest = matches[1]
                    # Extract everything after the first '>' which closes the mention
                    if '>' in rest:
                        command_text = rest.split('>', 1)[1].strip()
                    else:
                        command_text = ""
                else:
                    command_text = text.strip()
            
            print(f"Extracted command text: '{command_text}'")
            command_parts = command_text.split()
            print(f"Command parts: {command_parts}")
            
            if not command_parts:
                # If mentioned without a command, show help
                command_parts = ['help']
                print("No command specified, defaulting to 'help'")

            keyword = command_parts[0]
            args = command_parts[1:]
            print(f"Using command keyword: '{keyword}' with args: {args}")

            if keyword in self.commands:
                print(f"Found registered command: {keyword}")
                try:
                    print(f"Executing command: {keyword}")
                    response = await self.commands[keyword].execute(
                        client=self.client,
                        channel=channel,
                        user=user,
                        args=args
                    )
                    print(f"Command executed, response: {response}")
                    
                    if response:
                        print(f"Sending response to channel {channel}")
                        await self.client.chat_postMessage(
                            channel=channel,
                            text=response
                        )
                        print("Response sent")
                    else:
                        print("Command returned no response to send")
                except SlackApiError as e:
                    print(f"SlackApiError: {e}")
                    await SlackErrorHandler.handle_error_with_retry(
                        self.client,
                        channel,
                        e
                    )
                except Exception as e:
                    print(f"Unexpected error executing command {keyword}: {str(e)}")
                    import traceback
                    traceback.print_exc()
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
