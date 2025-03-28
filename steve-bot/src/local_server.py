import os
import asyncio
from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.web.async_client import AsyncWebClient
from bot import SlackBot

async def process_message(client, req):
    """Process incoming message events."""
    if req.type == "events_api":
        # Acknowledge the request
        await req.ack()
        
        # Get the event payload
        event = req.payload["event"]
        
        # Only process message events
        if event["type"] == "message":
            await bot.handle_message(event)

async def main():
    # Get the required tokens from environment
    app_token = os.getenv('SLACK_APP_TOKEN')
    user_token = os.getenv('SLACK_USER_TOKEN')
    
    if not app_token or not user_token:
        print("Error: Both SLACK_APP_TOKEN and SLACK_USER_TOKEN environment variables must be set")
        print("SLACK_APP_TOKEN should start with 'xapp-'")
        print("SLACK_USER_TOKEN should start with 'xoxp-'")
        return

    # Create the bot instance with an async web client
    global bot
    bot = SlackBot(AsyncWebClient(token=user_token))
    
    # Initialize Socket Mode client
    client = SocketModeClient(
        app_token=app_token,
        web_client=bot.client
    )
    
    # Add message handler
    client.socket_mode_request_listeners.append(process_message)
    
    # Start Socket Mode
    print("Connecting to Slack using Socket Mode...")
    await client.connect()
    
    # Keep the program running
    await asyncio.Future()  # run forever

if __name__ == '__main__':
    asyncio.run(main())
