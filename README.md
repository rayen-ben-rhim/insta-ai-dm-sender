# Instagram AI DM Sender

An automated Instagram direct messaging bot that uses AI to generate personalized, contextually-aware responses to Instagram DMs.

## Features

- Auto-responds to Instagram direct messages
- Uses Google's Gemini AI to generate human-like responses
- Maintains conversation context and history
- Detects message topics and adapts conversation style
- Tracks user profiles and interaction patterns

## Requirements

- Python 3.6+
- instagrapi
- Google Generative AI Python SDK

## Setup

1. Clone the repository

```bash
git clone https://github.com/rayen-ben-rhim/insta-ai-dm-sender.git
cd insta-ai-dm-sender
```

2. Install dependencies

```bash
pip install instagrapi google-generativeai
```

3. Configure your credentials
   Edit `main.py` and add your:

- Instagram username and password
- Google Gemini API key
- Target recipient username for testing

## Usage

Run the main script to start the bot:

```bash
python main.py
```

The bot will:

- Log in to Instagram
- Initialize conversation history with the target user
- Continuously monitor for new messages
- Respond to new messages using the Gemini AI
- Save conversation context between runs

## Customization

You can customize the AI's personality by modifying the `personality_prompt` variable in the script.

## Notes

- Use responsibly and in accordance with Instagram's terms of service
- The bot includes rate limiting to avoid API restrictions
- For testing purposes only, not recommended for production use without proper rate limiting and error handling

## License

[MIT License](LICENSE)
