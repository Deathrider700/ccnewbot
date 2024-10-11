import os
import json
import logging
from flask import Flask, request, jsonify
import telebot
from square.client import Client  # Square client
from square.error import ApiException  # For better error handling

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load configuration from a JSON file
def load_config():
    try:
        with open('config.json') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load configuration: {e}")
        return {}

config = load_config()

# Setup Square Client
square_client = Client(
    access_token=config['square']['access_token'],  # Access token from Square dashboard
    environment='production'  # Switch to 'production' for live transactions
)

# Initialize Flask app
app = Flask(__name__)

# Use environment variable for Telegram Bot Token
API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

# User input for target channel
target_channel = os.getenv('TARGET_CHANNEL')  # Use environment variable for the target channel

# Function to send confirmation to the target channel
def send_to_target_channel(transaction_info):
    try:
        bot.send_message(target_channel, f"Transaction Approved: {transaction_info}")
        logging.info(f"Sent to {target_channel}: Transaction Approved: {transaction_info}")
    except Exception as e:
        logging.error(f"Failed to send message: {e}")

# Function to handle the Square payment using the tokenized card nonce
async def process_payment(payment_nonce, amount=1):
    try:
        body = {
            "source_id": payment_nonce,
            "amount_money": {
                "amount": amount,
                "currency": "USD"
            },
            "idempotency_key": os.urandom(16).hex()  # Ensure each transaction is unique
        }

        result = square_client.payments.create_payment(body)
        if result.is_success:
            logging.info("Payment successful.")
            return result.body['payment']
        else:
            logging.warning(f"Payment failed: {result.errors}")
            return None

    except ApiException as e:
        logging.error(f"Square API error: {e}")
        return None

# Route for processing payments
@app.route('/process-payment', methods=['POST'])
def payment_route():
    data = request.get_json()
    payment_nonce = data.get('nonce')
    transaction_info = asyncio.run(process_payment(payment_nonce))
    if transaction_info:
        return jsonify({"status": "success", "transaction": transaction_info}), 200
    else:
        return jsonify({"status": "error"}), 400

# Route to serve the index HTML page
@app.route('/')
def index():
    return "Telegram Bot is running!"  # Simple response for the root route

# Start the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))  # Vercel sets the port
