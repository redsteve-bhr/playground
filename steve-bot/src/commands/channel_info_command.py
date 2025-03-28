from datetime import datetime
from .base_command import BaseCommand
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from utils import SlackErrorHandler

class ChannelInfoCommand(BaseCommand):
    @property
    def keyword(self) -> str:
        return "channel-info"

    @property
    def help_text(self) -> str:
        return "Shows detailed information about the current channel. Usage: @<bot> channel-info"

    async def execute(self, client: AsyncWebClient, channel: str, user: str, args: list) -> str:
        try:
            # Get channel information
            try:
                channel_info = (await client.conversations_info(channel=channel))['channel']
            except SlackApiError as e:
                if e.response['error'] == 'channel_not_found':
                    return "I can't access this channel. Please make sure I'm invited to it."
                raise
            
            # Get member count
            try:
                member_count = len((await client.conversations_members(channel=channel))['members'])
            except SlackApiError as e:
                if e.response['error'] in ['channel_not_found', 'not_in_channel']:
                    return "I need to be invited to this channel to get member information."
                member_count = "Unknown (insufficient permissions)"
            
            # Format creation time
            created_time = datetime.fromtimestamp(channel_info['created']).strftime('%Y-%m-%d %H:%M:%S')
            
            # Build response
            info = [
                f"*Channel Information for #{channel_info['name']}*",
                f"• *Created:* {created_time}",
                f"• *Members:* {member_count}",
                f"• *Created by:* <@{channel_info['creator']}>",
                f"• *Private:* {'Yes' if channel_info['is_private'] else 'No'}"
            ]
            
            # Add topic if it exists and we have access
            try:
                if channel_info.get('topic') and channel_info['topic'].get('value'):
                    info.append(f"• *Topic:* {channel_info['topic']['value']}")
            except SlackApiError:
                info.append("• *Topic:* Unable to access topic information")
            
            # Add purpose if it exists and we have access
            try:
                if channel_info.get('purpose') and channel_info['purpose'].get('value'):
                    info.append(f"• *Purpose:* {channel_info['purpose']['value']}")
            except SlackApiError:
                info.append("• *Purpose:* Unable to access purpose information")

            return "\n".join(info)

        except SlackApiError as e:
            message, recoverable = SlackErrorHandler.handle_error(e)
            return message
        except Exception as e:
            return f"Error fetching channel information: {str(e)}"
