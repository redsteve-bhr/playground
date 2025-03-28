import json
import os
from bot import SlackBot

def lambda_handler(event, context):
    """AWS Lambda handler function."""
    try:
        # Get the Slack token from environment variables
        slack_token = os.environ['SLACK_USER_TOKEN']
        
        # Initialize the bot
        bot = SlackBot(slack_token)
        
        # Parse the event body
        body = json.loads(event.get('body', '{}'))
        
        # Handle Slack event
        if 'challenge' in body:
            # Handle URL verification challenge
            return {
                'statusCode': 200,
                'body': json.dumps({'challenge': body['challenge']})
            }
        
        # Handle other events
        if 'event' in body:
            event_data = body['event']
            if event_data.get('type') == 'message':
                bot.handle_message(event_data)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Event processed successfully'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
