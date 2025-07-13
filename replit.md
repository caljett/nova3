# Overview

This is a Telegram bot application that generates customized HTML pages for group chats and serves them via a Flask web server. The bot creates bookmarklet pages for nova.trade integration and manages wallet addresses for different Telegram group chats.

## User Preferences

- Preferred communication style: Simple, everyday language
- Simplified file structure: Single main.py file with config.json for settings
- Data organization: All data files in /data/ directory, generated pages in /page/

## System Architecture

### Backend Architecture (Updated January 2025)
- **Framework**: Flask web application with direct Telegram API integration
- **Bot Framework**: Direct HTTP requests to Telegram Bot API (simplified from python-telegram-bot)
- **Template Engine**: String replacement for HTML page generation
- **Storage**: JSON file-based storage system for persistence
- **Deployment**: WSGI-compatible application with ProxyFix middleware

### Key Design Decisions
- **Single File Structure**: All functionality consolidated into main.py for simplicity
- **Configuration-based**: Settings stored in data/config.json with fallback to environment variables
- **File-based Storage**: Uses JSON files instead of a database for simplicity and easy deployment
- **Webhook Integration**: Bot receives updates via webhook instead of polling for better performance
- **Direct API Calls**: Uses requests library for Telegram API instead of complex bot framework

## Key Components

### 1. Main Application (`main.py`)
- Single file containing all functionality
- Flask web server with webhook endpoint
- Telegram bot command handlers
- Storage system for chat data
- HTML page generation and serving
- Configuration loading from JSON

### 2. Configuration System (`data/config.json`)
- Telegram bot token
- Webhook URL for deployment
- Server settings (host, port)
- Session secret for Flask
- Required user verification (username that must be in group)
- Admin user IDs for privileged commands

### 3. Template System (`data/page.html`)
- HTML template for generated bookmarklet pages
- CHAT_ID placeholder replaced with actual chat ID
- nova.trade bookmarklet integration

### 4. Storage System (Integrated)
- JSON-based persistence in data/bot_data.json
- Stores wallet addresses mapped to chat IDs
- Stores generated page filenames mapped to chat IDs
- Automatic file creation and saving

## Data Flow

1. **Bot Interaction**: User sends commands to Telegram bot in group chat
2. **Data Processing**: Bot processes commands and stores relevant data (wallet addresses, chat IDs)
3. **Page Generation**: Bot generates random filename and creates HTML page from template
4. **File Storage**: Generated HTML is saved to `static/pages/` directory
5. **URL Sharing**: Bot responds with public URL to the generated page
6. **Web Serving**: Flask serves the generated HTML pages via `/page/<filename>` route

## External Dependencies

### Environment Variables
- `TELEGRAM_BOT_TOKEN`: Required for bot authentication with Telegram API
- `WEBHOOK_URL`: Base URL for the deployed application (used for page URLs)
- `SESSION_SECRET`: Flask session secret key (defaults to dev key)

### Third-party Services
- **Telegram Bot API**: For receiving and sending messages
- **nova.trade**: Target service for the generated bookmarklets

### Python Packages
- `flask`: Web framework
- `python-telegram-bot`: Telegram bot library
- `jinja2`: Template engine
- `werkzeug`: WSGI utilities

## Deployment Strategy

### Application Structure
- **Entry Point**: `main.py` starts the Flask development server
- **Production**: Application is WSGI-compatible via `app.py`
- **Static Files**: Generated pages stored in `static/pages/` directory
- **Data Persistence**: `bot_data.json` file in application root

### Scaling Considerations
- Current implementation uses file-based storage (single instance)
- JSON storage limits concurrent access and scalability
- Webhook-based bot updates reduce polling overhead
- Static file serving can be offloaded to CDN/reverse proxy

### Security Features
- Bot only operates in group chats (private chat protection)
- Required user verification (configurable username must be in group)
- Random filename generation prevents URL guessing
- Environment variable configuration for sensitive data
- ProxyFix middleware for proper header handling

## Development Notes

- The application is currently incomplete (bot.py file appears truncated)
- Missing database integration (JSON storage is temporary solution)
- Template system is set up but needs completion
- Error handling and logging are partially implemented
- Ready for extension with proper database backend (Drizzle/Postgres compatible)