from instagrapi import Client
import os
import time
from google import genai
import datetime
import json
import re

# Instagram credentials - for testing only
username = ''
password = ''
# Gemini API setup
genai_api_key = ""  
client = genai.Client(api_key=genai_api_key)


cl = Client()
try:
    cl.login(username, password)
    print("Successfully logged in to Instagram")
except Exception as e:
    print(f"Login error: {e}")
    exit(1)

# Target a specific user for testing
test_recipient = ''  

# Keep track of processed messages
processed_message_ids = set()

# Store conversation context data
CONTEXT_FILE = "conversation_context.json"

# Try to load existing context data
def load_context_data():
    try:
        if os.path.exists(CONTEXT_FILE):
            with open(CONTEXT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading context data: {e}")
        return {}

# Save context data to file
def save_context_data(context_data):
    try:
        with open(CONTEXT_FILE, 'w', encoding='utf-8') as f:
            json.dump(context_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving context data: {e}")

# Initialize context data
context_data = load_context_data()

personality_prompt = """
You are now responding as the Instagram user "sm", a 20-year-old student named Rayen. You're chill, funny, and easy to talk to  You're active on Instagram, chatting with school friends, joking around, and keeping it light.

PERSONALITY TRAITS:
- Friendly, relaxed, and always down for a chat
- Likes to joke, but can also talk seriously when needed
- Speaks naturally in Derja, sometimes mixing in light French or English
- Keeps convos fun, casual, and relatable
- Listens well and replies like a real friend would

COMMUNICATION STYLE:
- Uses short, casual messages with Derja expressions
- Responds like you're talking in real life or on a voice note
- Always sounds natural and not too formal
- Can talk about school, life, stress, fun, anything

INTERESTS:
- Hanging out with friends online or IRL
- Talking about school, exams, and future plans
- Memes, jokes, and funny moments
- Chill convos about daily life, vibes, or random stuff

When replying to DMs, always stay real. Act like Rayen would with his classmates—friendly, casual, sometimes silly, but always honest and down to talk.
"""

# Function to get user ID with error handling
def get_user_id(username):
    try:
        return cl.user_id_from_username(username)
    except Exception as e:
        print(f"Error getting user ID for {username}: {e}")
        return None

# Function to fetch and store user info for better context
def get_user_info(username, user_id):
    if username not in context_data:
        context_data[username] = {
            "profile": {},
            "conversation_history": [],
            "topics": {},
            "conversation_state": "general",
            "last_interaction": ""
        }
    
    # Only fetch profile info if we don't have it yet
    if not context_data[username]["profile"]:
        try:
            user_info = cl.user_info(user_id)
            context_data[username]["profile"] = {
                "username": username,
                "full_name": user_info.full_name,
                "bio": user_info.biography,
                "follower_count": user_info.follower_count,
                "following_count": user_info.following_count,
                "is_private": user_info.is_private
            }
            save_context_data(context_data)
        except Exception as e:
            print(f"Error fetching user info: {e}")
    
    return context_data[username]

# Analyze message content for topic detection
def detect_topic(message_text):
    topics = {
        "school": ["school", "class", "exam", "study", "homework", "teacher", "professor", "assignment"],
        "social": ["hangout", "party", "friend", "meeting", "event"],
        "tech": ["phone", "computer", "app", "instagram", "game", "gaming", "tech"],
        "personal": ["feel", "sad", "happy", "tired", "bored", "excited", "love", "hate"],
        "planning": ["tomorrow", "next week", "weekend", "plan", "schedule"]
    }
    
    message_lower = message_text.lower()
    detected_topics = []
    
    for topic, keywords in topics.items():
        for keyword in keywords:
            if keyword in message_lower:
                detected_topics.append(topic)
                break
    
    return detected_topics if detected_topics else ["general"]

# Update the conversation state based on message content
def update_conversation_state(user_context, message_text):
    # Simple state tracking
    if "?" in message_text:
        return "question"
    
    topics = detect_topic(message_text)
    if "personal" in topics:
        return "emotional"
    if "planning" in topics:
        return "planning"
    if "school" in topics:
        return "academic"
    
    # Default to previous state or general
    return user_context.get("conversation_state", "general")

# Function to generate response with Gemini with enhanced context
def generate_ai_response(username, message_content):
    try:
        user_context = context_data.get(username, {})
        profile_info = user_context.get("profile", {})
        conversation_history = user_context.get("conversation_history", [])
        
        # Get current time for contextual awareness
        current_time = datetime.datetime.now()
        day_of_week = current_time.strftime("%A")
        time_of_day = "morning" if 5 <= current_time.hour < 12 else "afternoon" if 12 <= current_time.hour < 18 else "evening"
        
        # Update topics based on message content
        detected_topics = detect_topic(message_content)
        if "topics" not in user_context:
            user_context["topics"] = {}
            
        for topic in detected_topics:
            if topic not in user_context["topics"]:
                user_context["topics"][topic] = 0
            user_context["topics"][topic] += 1
        
        # Update conversation state
        user_context["conversation_state"] = update_conversation_state(user_context, message_content)
        
        # Format conversation history for the prompt
        formatted_history = ""
        if conversation_history:
            # Only use the last 5 message exchanges for context
            recent_history = conversation_history[-10:]
            formatted_history = "\n".join([f"{entry['sender']}: {entry['message']}" for entry in recent_history])
        
        # Build a rich context prompt
        context_prompt = f"""
CURRENT TIME: {current_time.strftime("%H:%M")} {time_of_day} on {day_of_week}

USER PROFILE:
- Username: {profile_info.get('username', username)}
- Name: {profile_info.get('full_name', '')}
- Bio: {profile_info.get('bio', '')}

CONVERSATION CONTEXT:
- Main topics: {', '.join(user_context.get('topics', {}).keys())}
- Current conversation state: {user_context.get('conversation_state', 'general')}
- Last interaction: {user_context.get('last_interaction', '')}

RECENT CONVERSATION HISTORY:
{formatted_history}

INCOMING MESSAGE: "{message_content}"

YOUR RESPONSE (as sm):
"""

        # Create a complete prompt
        complete_prompt = f"{personality_prompt}\n\n{context_prompt}"

        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=complete_prompt
        )
        
        # Update last interaction time
        user_context["last_interaction"] = current_time.strftime("%Y-%m-%d %H:%M:%S")
        save_context_data(context_data)
        
        # Return just the AI's response
        return response.text
    except Exception as e:
        print(f"Error generating AI response: {e}")
        return "Sorry, I couldn't process your message right now."

# Function to check and respond to messages
def check_and_respond():
    try:
        # Get user ID first
        user_id = get_user_id(test_recipient)
        if not user_id:
            print(f"Could not find user ID for {test_recipient}")
            return False
        
        # Get or create user context
        user_context = get_user_info(test_recipient, user_id)
            
        # Get direct threads
        threads = cl.direct_threads()
        
        # Find the thread with our test recipient
        target_thread = None
        for thread in threads:
            for user in thread.users:
                if user.username == test_recipient:
                    target_thread = thread
                    break
            if target_thread:
                break
                
        if not target_thread:
            print(f"No thread found with {test_recipient}")
            return False
            
        # Get messages from the thread
        messages = cl.direct_messages(thread_id=target_thread.id)
        
        if messages:
            # Check if there are new messages (not processed yet)
            new_messages = []
            for message in messages:
                if message.id not in processed_message_ids and message.user_id == user_id:
                    new_messages.append(message)
                    processed_message_ids.add(message.id)
            
            if new_messages:
                # Process the latest unprocessed message
                latest_message = new_messages[0]
                
                # Handle text attribute safely
                message_text = latest_message.text if hasattr(latest_message, 'text') and latest_message.text else "[media or non-text content]"
                print(f"{datetime.datetime.now()} - New message from {test_recipient}: {message_text}")
                
                # Skip processing for non-text messages
                if message_text == "[media or non-text content]":
                    print("Skipping non-text message")
                    return True
                
                # Handle timestamp - fix for the error
                if hasattr(latest_message, 'timestamp'):
                    # Make sure timestamp is an integer (Unix timestamp)
                    if isinstance(latest_message.timestamp, (int, float)):
                        timestamp = datetime.datetime.fromtimestamp(latest_message.timestamp).strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        # If timestamp is already a datetime object, use it directly
                        timestamp = latest_message.timestamp.strftime("%Y-%m-%d %H:%M:%S") if isinstance(latest_message.timestamp, datetime.datetime) else datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                else:
                    # If no timestamp, use current time
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Add message to conversation history
                if "conversation_history" not in user_context:
                    user_context["conversation_history"] = []
                    
                user_context["conversation_history"].append({
                    "sender": test_recipient,
                    "message": message_text,
                    "timestamp": timestamp
                })
                
                # Keep only the last 20 messages for history
                if len(user_context["conversation_history"]) > 20:
                    user_context["conversation_history"] = user_context["conversation_history"][-20:]
                
                # Generate AI response with enhanced context
                ai_response = generate_ai_response(test_recipient, message_text)
                
                # Add the bot's response to conversation history
                current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                user_context["conversation_history"].append({
                    "sender": "sm",
                    "message": ai_response,
                    "timestamp": current_timestamp
                })
                
                # Save updated context
                save_context_data(context_data)
                
                # Send the response
                cl.direct_send(ai_response, [user_id])
                print(f"{datetime.datetime.now()} - ✅ Responded to @{test_recipient}: {ai_response[:50]}...")
                
                return True  # Indicate we processed a message
    except Exception as e:
        print(f"Error in check_and_respond: {e}")
        import traceback
        traceback.print_exc()  # Print full traceback for debugging
    
    return False  # No new messages processed

# Main loop to continuously check for messages
print("Starting message monitoring with enhanced context understanding...")
try:
    # On first run, mark all existing messages as processed
    user_id = get_user_id(test_recipient)
    if user_id:
        # Initialize user context
        user_context = get_user_info(test_recipient, user_id)
        
        threads = cl.direct_threads()
        for thread in threads:
            thread_processed = False
            for user in thread.users:
                if user.username == test_recipient:
                    messages = cl.direct_messages(thread_id=thread.id)
                    
                    # Add existing messages to conversation history
                    if "conversation_history" not in user_context:
                        user_context["conversation_history"] = []
                        
                    for message in messages:
                        processed_message_ids.add(message.id)
                        if hasattr(message, 'text') and message.text:
                            # Handle timestamp properly
                            if hasattr(message, 'timestamp'):
                                # Fix: Check if timestamp is already a datetime object
                                if isinstance(message.timestamp, (int, float)):
                                    timestamp = datetime.datetime.fromtimestamp(message.timestamp).strftime("%Y-%m-%d %H:%M:%S")
                                else:
                                    timestamp = message.timestamp.strftime("%Y-%m-%d %H:%M:%S") if isinstance(message.timestamp, datetime.datetime) else datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            else:
                                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            # Add to history based on who sent it
                            if message.user_id == user_id:
                                user_context["conversation_history"].append({
                                    "sender": test_recipient,
                                    "message": message.text,
                                    "timestamp": timestamp
                                })
                            else:
                                user_context["conversation_history"].append({
                                    "sender": "sm",
                                    "message": message.text,
                                    "timestamp": timestamp
                                })
                    
                    # Keep only the last 20 messages
                    if len(user_context["conversation_history"]) > 20:
                        user_context["conversation_history"] = user_context["conversation_history"][-20:]
                    
                    save_context_data(context_data)
                    print(f"Initialized with {len(processed_message_ids)} existing messages")
                    thread_processed = True
                    break
            
            if thread_processed:
                break

    while True:
        if check_and_respond():
            # If we processed a message, wait a bit shorter time before checking again
            time.sleep(5)
        else:
            # If no new messages, wait longer to avoid API rate limits
            print(f"{datetime.datetime.now()} - No new messages, waiting...")
            time.sleep(30)
except KeyboardInterrupt:
    print("Bot stopped by user")
except Exception as e:
    print(f"Fatal error: {e}")
    import traceback
    traceback.print_exc()  # Print full traceback for debugging