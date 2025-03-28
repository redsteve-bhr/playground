from datetime import datetime, timedelta
from .base_command import BaseCommand
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from utils import SlackErrorHandler

class SummarizeCommand(BaseCommand):
    @property
    def keyword(self) -> str:
        return "summarize"

    @property
    def help_text(self) -> str:
        return "Summarizes the last 24 hours of conversation in the current channel. Usage: @<bot> summarize"

    async def execute(self, client: AsyncWebClient, channel: str, user: str, args: list) -> str:
        try:
            # Get current time and 24 hours ago
            now = datetime.now()
            yesterday = now - timedelta(days=1)
            oldest_timestamp = yesterday.timestamp()

            # First check if we have access to the channel
            try:
                await client.conversations_info(channel=channel)
            except SlackApiError as e:
                if e.response['error'] in ['channel_not_found', 'not_in_channel']:
                    return "I need to be invited to this channel to provide a summary."
                raise

            # Fetch conversation history
            try:
                result = await client.conversations_history(
                    channel=channel,
                    oldest=oldest_timestamp
                )
            except SlackApiError as e:
                if e.response['error'] == 'not_in_channel':
                    return "I need to be invited to this channel to read its history."
                elif e.response['error'] == 'channel_not_found':
                    return "I can't find this channel. It might have been deleted or I might not have access to it."
                raise

            if not result['messages']:
                return "No messages found in the last 24 hours."

            # Process messages
            message_count = len(result['messages'])
            unique_users = set()
            threads = 0
            reactions = 0

            for msg in result['messages']:
                if 'user' in msg:
                    unique_users.add(msg['user'])
                if 'thread_ts' in msg:
                    threads += 1
                if 'reactions' in msg:
                    reactions += len(msg['reactions'])

            summary = (
                f"Channel Summary (last 24 hours):\n"
                f"• Total messages: {message_count}\n"
                f"• Unique participants: {len(unique_users)}\n"
                f"• Thread discussions: {threads}\n"
                f"• Reactions used: {reactions}"
            )

            return summary

        except SlackApiError as e:
            message, recoverable = SlackErrorHandler.handle_error(e)
            return message
        except Exception as e:
            return f"Error summarizing channel: {str(e)}"
