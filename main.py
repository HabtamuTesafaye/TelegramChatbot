import os
import httpx
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Initialize the Telegram bot with your token from an environment variable
TELEGRAM_TOKEN = os.getenv(
    'TELEGRAM_TOKEN')  # Set your Telegram token in environment variables
GEMINI_API_KEY = os.getenv(
    'GEMINI_API_KEY')  # Ensure your Gemini API key is set here

# Create the application
application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    custom_keyboard = [['Help', 'About']]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard,
                                       one_time_keyboard=True,
                                       resize_keyboard=True)
    await update.message.reply_text(
        "Hello! I'm your AI chatbot powered by Gemini. How can I assist you today?",
        reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Here are some commands you can use:\n"
        "/start - Start the bot\n"
        "/about - Learn more about this bot\n"
        "Just type any question or send an image, and I will do my best to help you!"
    )
    await update.message.reply_text(help_text)

# Temporary user profile store (for demonstration purposes)
user_profiles = {}

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    profile = user_profiles.get(user_id, {"Name": "Not set", "Email": "Not set", "Bio": "Not set"})

    profile_text = (
        f"**Profile Information**:\n"
        f"**Name**: {profile['Name']}\n"
        f"**Email**: {profile['Email']}\n"
        f"**Bio**: {profile['Bio']}\n"
    )

    await update.message.reply_text(profile_text, parse_mode='MarkdownV2')

async def edit_profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send your new profile details in the format:\n"
                                      "`Name, Email, Bio`")

async def handle_profile_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        name, email, bio = update.message.text.split(",")
        user_profiles[user_id] = {
            "Name": name.strip(),
            "Email": email.strip(),
            "Bio": bio.strip()
        }
        await update.message.reply_text("Profile updated successfully!")
    except ValueError:
        await update.message.reply_text("Please provide your details in the correct format.")

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = "I am a chatbot powered by Gemini, designed to assist you with various queries!"
    await update.message.reply_text(about_text)


async def reply_to_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text  # Get user message
    await context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                       action='typing')

    try:
        gemini_response = await query_gemini(user_message)  # Query Gemini
        formatted_response = format_response(
            gemini_response)  # Format the response
        await update.message.reply_text(formatted_response
                                        )  # Send response back to user
    except Exception as e:
        await update.message.reply_text("Sorry, something went wrong.")
        print(f"Error: {e}")  # Log the error for debugging purposes


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = update.message.photo[-1]
    file_id = photo_file.file_id

    try:
        new_file = await context.bot.get_file(file_id)
        file_path = new_file.file_path

        async with httpx.AsyncClient() as client:
            response = await client.get(file_path)
            if response.status_code == 200:
                local_image_path = 'user_photo.jpg'
                with open(local_image_path, 'wb') as f:
                    f.write(response.content)

                await update.message.reply_text("Image downloaded successfully.")

                prompt = update.message.caption or ""
                gemini_response = await query_gemini(local_image_path, prompt)
                await update.message.reply_text(gemini_response)
            else:
                await update.message.reply_text(f"Failed to download image, status code: {response.status_code}")
    except Exception as e:
        print(f"Error handling photo: {e}")
        await update.message.reply_text("Sorry, I couldn't process the photo.")



async def query_gemini(prompt=None, image_path=None):
    GEMINI_API_URL = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}'
    headers = {'Content-Type': 'application/json'}

    async with httpx.AsyncClient() as client:
        try:
            data = {
                'contents': [{
                    'parts': [{
                        'text': prompt
                    }]
                }]
            } if prompt else {
                'contents': []
            }

            # Send a request to the AI
            response = await client.post(GEMINI_API_URL, headers=headers, json=data)
            response.raise_for_status()  # Raise an error for bad responses

            # Extract the text and potentially an image from the response
            api_response = response.json()
            candidates = api_response.get('candidates', [])
            if candidates:
                content = candidates[0].get('content', {})
                parts = content.get('parts', [])
                if parts:
                    text_response = parts[0].get('text', 'No response text found.')
                    image_url = content.get('image_url', None)  # Get the image URL if available
                    return text_response, image_url  # Return both text and image URL
            return 'No response text found.', None  # Default message if text is not found
        except Exception as e:
            print(f"Error querying Gemini API: {e}")
            return "Sorry, I couldn't process your request.", None  # Handle errors


async def reply_to_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text  # Get user message
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    try:
        # Query the AI for a response and an image
        text_response, image_url = await query_gemini(user_message)

        # Send the text response back to the user
        await update.message.reply_text(format_response(text_response))

        # If there is an image URL, send the image
        if image_url:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=image_url)

    except Exception as e:
        await update.message.reply_text("Sorry, something went wrong.")
        print(f"Error: {e}")  # Log the error for debugging purposes



def format_response(response_text):
    # Remove Markdown-style formatting and hash characters
    response_text = response_text.replace("*", "") \
                                 .replace("`", "") \
                                 .replace("#", "") \
                                 .replace("\n", "\n")  # Optionally keep line breaks

    return response_text


# Register handlers
application.add_handler(CommandHandler('start', start))
application.add_handler(CommandHandler('help', help_command))
application.add_handler(CommandHandler('about', about_command))
application.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, reply_to_message))
application.add_handler(MessageHandler(filters.PHOTO,
                                       handle_photo))  # Handle photo messages
# Register profile command handlers before general message handlers
application.add_handler(CommandHandler('profile', profile_command))
application.add_handler(CommandHandler('edit_profile', edit_profile_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_profile_update))


# Start polling
if __name__ == '__main__':
    application.run_polling()
