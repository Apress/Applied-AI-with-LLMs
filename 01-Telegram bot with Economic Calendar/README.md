# Economic Calendar Bot - MVP

A minimal Python application that fetches economic calendar data from MyFXBook RSS feed, analyzes it using Google Gemini AI, and sends trading insights to Telegram 1 hour before events.

## Features

- 📅 **RSS Feed Integration**: Fetches economic events from MyFXBook
- 🤖 **AI Analysis**: Uses Google Gemini for trading insights  
- 📱 **Telegram Notifications**: Sends alerts 1 hour before events
- ⏰ **Smart Scheduling**: Automatically schedules notifications
- 🎯 **High-Impact Filtering**: Focuses on important economic events

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment**:
   ```bash
   cp env.example .env
   # Edit .env with your API keys
   ```

3. **Run the application**:
   ```bash
   python script.py
   ```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `api_id` | Telegram API ID | Yes |
| `api_hash` | Telegram API hash | Yes |
| `session_name` | Telegram session name | Yes |
| `telegram_channel` | Target channel ID (integer) | Yes |
| `gemini_api_key` | Google Gemini API key | Yes |

## How It Works

1. **Data Fetching**: Fetches economic calendar data from MyFXBook RSS feed
2. **Event Filtering**: Filters for high/medium impact events
3. **AI Analysis**: Sends event data to Google Gemini for trading insights using a custom prompt template
4. **Scheduling**: Calculates notification time (1 hour before event) using asyncio
5. **Periodic Checks**: Automatically checks for new events every 30 minutes
6. **Delivery**: Sends formatted analysis to Telegram channel

## Project Structure

```
├── script.py              # Main application (435 lines)
├── prompts/
│   └── trading_analysis.txt  # AI prompt template
├── requirements.txt     # Dependencies
├── env.example         # Environment template
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## Dependencies

- `feedparser` - RSS feed parsing
- `google-genai` - Gemini AI integration
- `telethon` - Telegram client
- `python-dotenv` - Environment variables

## Notes

- **No database required**: Uses in-memory scheduling and caching
- **Free data source**: MyFXBook RSS feed (no API key needed)
- **Asyncio-based**: Uses async/await for efficient event handling
- **Caching**: AI analysis results are cached to avoid duplicate API calls
- **Auto-cleanup**: Automatically removes past events from memory to prevent growth

## License

MIT License