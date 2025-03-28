# Steve Bot - Slack Personal Assistant

A Slack bot that acts as a personal assistant, responding to keyword-based commands. The bot uses Slack's Socket Mode for real-time messaging, eliminating the need for a public URL. It's designed to run as an AWS Lambda function and can be extended with new commands easily.

## Features
- Keyword-based command system
- Uses Slack Socket Mode for real-time messaging
- Extensible architecture - add new commands by creating new files in the `commands` directory
- Built-in channel summary command
- AWS Lambda ready
- Local development support with Docker

## Setup
1. Create a Slack App and enable Socket Mode:
   - Go to api.slack.com/apps
   - Create a new app
   - Enable Socket Mode
   - Generate an App-Level Token with `connections:write` scope
   - Add bot event subscriptions for `message.channels`
   - Under "OAuth & Permissions", add these scopes:
     - `channels:history`
     - `channels:read`
     - `chat:write`
   - Install the app to your workspace

2. Set your environment variables:
   ```bash
   export SLACK_APP_TOKEN='xapp-your-app-token'  # Starts with xapp-
   export SLACK_USER_TOKEN='xoxp-your-user-token'  # Starts with xoxp-
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run locally with Docker:
   ```bash
   docker build -t steve-bot .
   docker run -e SLACK_APP_TOKEN -e SLACK_USER_TOKEN steve-bot
   ```

## Available Commands
Mention the bot by its Slack display name (e.g., @Security Bot) followed by a command:
- `help` - Shows a list of all available commands with descriptions
- `summarize` - Provides a summary of the last 24 hours of conversation in the current channel
- `channel-info` - Shows detailed information about the current channel including creation date, member count, and purpose

You can also just mention the bot without any command to see the help message.

Example:
```
@Security Bot help
@Security Bot channel-info
```

## Adding New Commands
1. Create a new Python file in the `src/commands` directory
2. Extend the `BaseCommand` class
3. Implement the required methods:
   - `keyword` property
   - `help_text` property
   - `execute` method

The command will be automatically loaded when the bot starts.
