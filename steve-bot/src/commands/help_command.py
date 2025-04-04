from .base_command import BaseCommand
from slack_sdk.web.async_client import AsyncWebClient

class HelpCommand(BaseCommand):
    @property
    def keyword(self) -> str:
        return "help"

    @property
    def help_text(self) -> str:
        return "Shows this help message with a list of all available commands. Usage: @<bot> help"

    async def execute(self, client: AsyncWebClient, channel: str, user: str, args: list) -> str:
        try:
            # Get the bot's commands from the bot instance
            # We can access this through the client's token owner
            auth = await client.auth_test()
            bot_name = auth.get('user', 'SlackBot')

            # Start with a header
            response = [
                f"*{bot_name} Commands*",
                "_Mention me with any of these commands:_\n"
            ]

            # Get all commands from the bot instance (accessible through the module)
            from bot import SlackBot
            bot = SlackBot.get_instance()
            
            # Make sure we have the bot instance
            if bot is None:
                print("Warning: Could not get bot instance, using direct command list")
                # Fallback - just list this command's help
                response.append(f"• *help*: {self.help_text}")
                response.append(f"• *channel-info*: Shows detailed information about the current channel.")
                response.append(f"• *summarize*: Summarizes the last 24 hours of conversation in the current channel.")
            else:
                print(f"Found bot instance with {len(bot.commands)} commands")
                # Sort commands by keyword for consistent display
                commands = sorted(bot.commands.items(), key=lambda x: x[0])
                
                # Add each command and its help text
                for keyword, command in commands:
                    response.append(f"• *{keyword}*: {command.help_text}")

            return "\n".join(response)

        except Exception as e:
            print(f"Error in help command: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Fallback help message
            return "Available commands: help, channel-info, summarize\n" + \
                   "For more details, type: @<bot> help"
