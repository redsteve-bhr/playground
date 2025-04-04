import os
import asyncio
from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.web.async_client import AsyncWebClient
from bot import SlackBot

# Track processed event IDs to prevent duplicate processing
processed_event_ids = set()

async def process_message(client, req):
    """Process incoming message events."""
    try:
        print(f"Received event type: {req.type}")
        
        # Important: The Socket Mode client in the Slack SDK uses 'events_api' type, not 'events'
        if req.type == "events_api":
            payload = req.payload
            
            # Check for duplicate events using event_id
            event_id = payload.get("event_id")
            if event_id in processed_event_ids:
                print(f"Skipping duplicate event: {event_id}")
                return
            
            # Add this event to processed set
            if event_id:
                processed_event_ids.add(event_id)
                # Limit size of set to prevent memory leaks
                if len(processed_event_ids) > 1000:
                    # Remove oldest entries (approximation - removes random items)
                    # This is fine for our deduplication purposes
                    while len(processed_event_ids) > 800:
                        processed_event_ids.pop()
            
            print(f"Processing new event: {event_id}")
            
            # Get the event from the payload
            event = payload.get("event", {})
            event_type = event.get("type")
            print(f"Event type: {event_type}")
            
            # Only process app_mention events
            if event_type == "app_mention":
                user_id = event.get('user')
                # This check is unnecessary - we want to process all app_mention events
                # The bot won't send app_mention events to itself
                print(f"Processing message from user {user_id}")
                print(f"Message text: {event.get('text')}")
                print(f"Bot's user ID: {bot.bot_user_id}")
                
                # Process the message
                await bot.handle_message(event)
                print("Message processed by bot.handle_message")
    except Exception as e:
        print(f"Error processing message: {str(e)}")
        import traceback
        traceback.print_exc()

async def main():
    # Get the required tokens from environment
    app_token = os.getenv('SLACK_APP_TOKEN')
    user_token = os.getenv('SLACK_USER_TOKEN')
    
    if not app_token or not user_token:
        print("Error: Both SLACK_APP_TOKEN and SLACK_USER_TOKEN environment variables must be set")
        print("SLACK_APP_TOKEN should start with 'xapp-'")
        print("SLACK_USER_TOKEN should start with 'xoxp-'")
        return

    try:
        # Create the bot instance with an async web client
        global bot
        bot = SlackBot(AsyncWebClient(token=user_token))
        
        # Initialize the bot (get its user ID)
        await bot.initialize()
        
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
        print("Successfully connected! Bot is ready to receive messages.")
        
        # Keep the program running
        await asyncio.Future()  # run forever
        
    except Exception as e:
        print(f"Error starting bot: {str(e)}")
        raise

if __name__ == '__main__':
    asyncio.run(main())
