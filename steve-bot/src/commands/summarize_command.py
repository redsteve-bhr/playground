from datetime import datetime, timedelta
import json
import asyncio
import re
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
        return "Summarizes recent conversations in the channel. Usage: @<bot> summarize [days]" 

    async def placeholder_ai_summarize(self, conversation_text):
        """Placeholder for an external AI summarization API call.
        In a real implementation, this would call an LLM API to summarize the conversation.
        """
        # Simulate a slight delay as if making an API call
        await asyncio.sleep(0.5)
        
        # Length-based placeholder logic to make it slightly more realistic
        text_length = len(conversation_text)
        topic_count = conversation_text.count("Topic:") or 1
        
        # Create a placeholder summary based on conversation length/complexity
        if text_length < 500:
            return "Brief discussions occurred in the channel with minimal interaction."
        elif text_length < 2000:
            return f"Several conversations took place covering approximately {topic_count} topics. The discussions were moderately detailed and included some questions and responses between participants."
        else:
            return f"Extensive conversations occurred covering {topic_count} main topics. There were in-depth discussions with multiple participants sharing information, asking questions, and providing detailed responses."

    async def execute(self, client: AsyncWebClient, channel: str, user: str, args: list) -> str:
        try:
            # First check if we have access to the channel
            try:
                await client.conversations_info(channel=channel)
            except SlackApiError as e:
                if e.response['error'] in ['channel_not_found', 'not_in_channel']:
                    return "I need to be invited to this channel to provide a summary."
                raise

            # Determine time range - default to 24 hours
            now = datetime.now()
            lookback_days = 1
            
            # Check for optional time range argument
            if args and args[0].isdigit():
                lookback_days = min(int(args[0]), 7)  # Cap at 7 days to avoid excessive API calls
            
            start_time = now - timedelta(days=lookback_days)
            oldest_timestamp = start_time.timestamp()
            
            print(f"Fetching messages since {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

            # Fetch up to 100 most recent messages from the channel history
            try:
                result = await client.conversations_history(
                    channel=channel,
                    oldest=oldest_timestamp,
                    limit=100  # Fetch up to 100 messages
                )
            except SlackApiError as e:
                if e.response['error'] == 'not_in_channel':
                    return "I need to be invited to this channel to read its history."
                elif e.response['error'] == 'channel_not_found':
                    return "I can't find this channel. It might have been deleted or I might not have access to it."
                raise

            if not result['messages']:
                return f"No messages found in the last {lookback_days} day(s)."

            # Process messages to get user info and format the conversation
            messages = result['messages']
            messages.reverse()  # Start with oldest message first
            user_cache = {}
            conversation_text = ""
            
            # First pass: Collect user information
            user_ids = set()
            for msg in messages:
                if 'user' in msg:
                    user_ids.add(msg['user'])
            
            # Bulk fetch user info to minimize API calls
            for user_id in user_ids:
                try:
                    user_info = await client.users_info(user=user_id)
                    user_cache[user_id] = user_info['user']['real_name']
                except SlackApiError:
                    # Fall back to using the user ID if we can't get the name
                    user_cache[user_id] = f"User {user_id}"
            
            # Second pass: Format the conversation
            current_topic = "General Discussion"
            
            for msg in messages:
                # Skip bot messages and system messages
                if 'subtype' in msg and msg['subtype'] in ['bot_message', 'channel_join', 'channel_leave']:
                    continue
                    
                # Try to identify topic shifts
                text = msg.get('text', '')
                
                # Detect potential topic changes (this is a simple heuristic)
                if text.startswith('Topic:') or text.startswith('#') or 'agenda item' in text.lower():
                    topic_match = re.search(r'(?:Topic:|#)\s*([^\n]+)', text)
                    if topic_match:
                        current_topic = topic_match.group(1).strip()
                        conversation_text += f"\n\nTopic: {current_topic}\n"
                
                # Format this message
                timestamp = float(msg.get('ts', '0'))
                time_str = datetime.fromtimestamp(timestamp).strftime('%H:%M')
                user_name = user_cache.get(msg.get('user', 'unknown'), 'Unknown User')
                
                conversation_text += f"[{time_str}] {user_name}: {text}\n"
                
                # Handle thread replies if present
                if 'thread_ts' in msg and msg.get('thread_ts') == msg.get('ts'):
                    try:
                        replies = await client.conversations_replies(
                            channel=channel,
                            ts=msg['thread_ts'],
                            limit=20  # Limit thread replies
                        )
                        
                        # Skip the parent message since we've already added it
                        for reply in replies['messages'][1:]:
                            reply_timestamp = float(reply.get('ts', '0'))
                            reply_time = datetime.fromtimestamp(reply_timestamp).strftime('%H:%M')
                            reply_user = user_cache.get(reply.get('user', 'unknown'), 'Unknown User')
                            reply_text = reply.get('text', '')
                            
                            conversation_text += f"[{reply_time}] {reply_user} (in thread): {reply_text}\n"
                    except SlackApiError:
                        # If we can't fetch thread replies, just continue
                        conversation_text += f"[Thread replies not accessible]\n"
            
            # Get AI summary of the conversation
            summary = await self.placeholder_ai_summarize(conversation_text)
            
            # Format the final response
            time_range = "24 hours" if lookback_days == 1 else f"{lookback_days} days"
            
            full_summary = f"*Channel Summary (last {time_range})*\n\n{summary}"
            return full_summary

        except SlackApiError as e:
            message, recoverable = SlackErrorHandler.handle_error(e)
            return message
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"Error summarizing channel: {str(e)}"
