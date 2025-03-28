from slack_sdk.errors import SlackApiError
from typing import Optional, Tuple

class SlackErrorHandler:
    # Common Slack error codes and their user-friendly messages
    ERROR_MESSAGES = {
        'not_in_channel': 'I need to be invited to this channel to perform this action.',
        'channel_not_found': 'I cannot find this channel. It might have been deleted or I might not have access to it.',
        'invalid_auth': 'There seems to be an issue with my authentication. Please contact the administrator.',
        'token_expired': 'My authentication has expired. Please contact the administrator.',
        'rate_limited': 'I\'m being rate limited by Slack. Please try again in a moment.',
        'permission_denied': 'I don\'t have permission to perform this action.',
        'no_permission': 'I don\'t have the necessary permissions. Please check my OAuth scopes.',
        'account_inactive': 'The Slack account is inactive. Please contact the administrator.',
        'missing_scope': 'I\'m missing some permissions. Please check my OAuth scopes.',
        'not_allowed': 'This action is not allowed in this workspace.',
        'invalid_cursor': 'There was an error paginating through results. Please try again.',
    }

    @classmethod
    def handle_error(cls, error: SlackApiError) -> Tuple[str, bool]:
        """
        Handle a Slack API error and return a user-friendly message and whether the error is recoverable.
        
        Args:
            error: The SlackApiError that occurred
            
        Returns:
            Tuple[str, bool]: (user-friendly error message, whether error is recoverable)
        """
        error_code = error.response.get('error', '')
        
        # Get the user-friendly message or create a generic one
        message = cls.ERROR_MESSAGES.get(
            error_code,
            f"An error occurred: {error_code}"
        )
        
        # Determine if the error is recoverable
        recoverable = error_code in {
            'rate_limited',
            'invalid_cursor',
            'channel_not_found'  # Might be recoverable if user invites bot
        }
        
        # Add retry suggestion for recoverable errors
        if recoverable:
            message += "\nYou can try this command again later."
            
        # Add admin contact suggestion for auth issues
        if error_code in {'invalid_auth', 'token_expired', 'account_inactive'}:
            message += "\nThis requires administrator attention to fix."
            
        # Add permission guidance
        if error_code in {'permission_denied', 'no_permission', 'missing_scope'}:
            message += "\nAn administrator needs to grant me additional permissions."
            
        return message, recoverable

    @classmethod
    def format_rate_limit_message(cls, error: SlackApiError) -> str:
        """
        Format a rate limit error message with the retry delay.
        """
        retry_after = error.response.headers.get('Retry-After', '60')
        return f"I'm being rate limited by Slack. Please try again in {retry_after} seconds."

    @classmethod
    async def handle_error_with_retry(cls, client, channel: str, error: SlackApiError) -> None:
        """
        Handle a Slack API error and attempt to notify the user.
        
        Args:
            client: The Slack client to use for sending messages
            channel: The channel to send the error message to
            error: The SlackApiError that occurred
        """
        try:
            message, recoverable = cls.handle_error(error)
            
            # Special handling for rate limits
            if error.response['error'] == 'rate_limited':
                message = cls.format_rate_limit_message(error)
            
            # Try to send the error message
            await client.chat_postMessage(
                channel=channel,
                text=message
            )
        except Exception as e:
            # If we can't send the message, just log it
            print(f"Error sending error message: {str(e)}")
            print(f"Original error: {str(error)}")

def is_retryable_error(error: SlackApiError) -> bool:
    """
    Check if a Slack API error is retryable.
    """
    if not error.response:
        return False
        
    error_code = error.response.get('error', '')
    return error_code in {
        'rate_limited',
        'invalid_cursor',
        'channel_not_found'
    }
