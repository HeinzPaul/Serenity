from flask import Flask,request,jsonify,session,redirect,render_template
from flask_cors import CORS
import google.generativeai as genai
from flask import send_from_directory
from pymongo import MongoClient
import bcrypt
from bson.objectid import ObjectId
import os
from dotenv import load_dotenv

app = Flask(__name__,static_folder='static')
CORS(app)

# Load environment variables from .env file
load_dotenv()

# Fetch the API key from the environment variables
genai_api_key = os.getenv("gemini_api_key")

# Configure the Generative AI model with the API key
genai.configure(api_key=genai_api_key)
model = genai.GenerativeModel("gemini-2.0-flash")

MONGO_URI = os.getenv("DATABASE_URL")

client = MongoClient(MONGO_URI)

# Configure secret key for session management
app.secret_key = os.getenv("SECRET_KEY")

db = client["Serenity"]
user_data = db["user_data"]
user_memories = db["user_memories"]
user_chat_logs = db["user_chat_logs"]

# Helper function to hash passwords
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# Modify the signup route to hash the password before storing it
@app.route('/signup', methods=["POST", "GET"])
def signup():
    if request.method == "POST":
        # Use request.form to get form data
        name = request.form.get("name")
        email = request.form.get("email")
        age = request.form.get("age")
        gender = request.form.get("gender")
        sleep = request.form.get("sleep")
        triggers = request.form.get("triggers")
        coping = request.form.get("coping")
        agent_style = request.form.get("agent_style")
        password = request.form.get("password")

        # Hash the password
        hashed_password = hash_password(password)

        # Prepare the data to insert
        user_datas = {
            "name": name,
            "email":email,
            "age": age,
            "gender": gender,
            "sleep": sleep,
            "triggers": triggers,
            "coping": coping,
            "agent_style":agent_style,
            "password": hashed_password
        }

        # Insert the data into the collection
        inserted_user = user_data.insert_one(user_datas)

        # Set the session with the user's ID
        session['user_id'] = str(inserted_user.inserted_id)

        # Return a success response
        return redirect('/chat')

    return render_template('signup.html')

# Modify the login route to verify the hashed password
@app.route('/login', methods=["POST", "GET"])
def login():
    if request.method == "POST":
        # Get login credentials
        email = request.form.get("email")
        password = request.form.get("password")

        # Find user in the database
        user = user_data.find_one({"email": email})

        if user and bcrypt.checkpw(password.encode('utf-8'), user["password"]):
            # Set the session with the user's ID
              
            try:
                # Combine system prompt with actual user input
                # Load chat history from the database
                user_id = str(user["_id"]) if user else None
                chat_history = []
                if user_id:
                    chat_log = user_chat_logs.find_one({"_id": ObjectId(user_id)})
                    if chat_log and "messages" in chat_log:
                        chat_history = chat_log["messages"]

                # Combine system prompt with actual user input and chat history
                history_text = "\n".join(chat_history)
                full_prompt = f"Summarize the following chat history to capture any important or key details that should be remembered for the next conversation. Ensure the summary is concise, meaningful, and highlights significant themes, emotional states, or recurring topics discussed by the user all in 2 or 3 sentences:\n\nChat History:\n{history_text}"
                response = model.generate_content(full_prompt)
                new_response = response.text.strip()
                # Log the AI's response to the user's chat log
                memories = user_memories.find_one({"_id": ObjectId(user_id)})

                if not memories:
                    # If no memory log exists, create a new one
                    user_memories.insert_one({
                        "_id": ObjectId(user_id),
                        "memories": []
                    })
                user_memories.update_one(
                        {"_id": ObjectId(user_id)},
                        {"$push": {"memories": f"{new_response}"}}
                    )
                # Clear the messages in user_chat_logs for this user
                user_chat_logs.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {"messages": []}}
                )
            except Exception as e:
                return jsonify({"reply": "Oops! I had a problem processing that."})
            session['user_id'] = str(user["_id"])
            return redirect('/chat')
        else:
            return jsonify({"error": "Invalid credentials"}), 401

    

@app.route('/get_memories', methods=['GET'])
def get_memories():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user_id = session['user_id']
    memories = user_memories.find_one({'_id': ObjectId(user_id)})
    return jsonify({'memories': memories.get('memories', [])})

@app.route('/delete_memory', methods=['POST'])
def delete_memory():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user_id = session['user_id']
    memory_to_delete = request.json.get('memory')

    try:
        user_memories.update_one(
            {'_id': ObjectId(user_id)},
            {'$pull': {'memories': memory_to_delete}}
        )
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logout',methods=["POST"])
def logout():
    # Clear the session
    session.clear()
    return redirect('/')

@app.route('/')
def home():
    return render_template('homepage.html')

@app.route('/log_message', methods=["POST"])
def log_message():
        # Check if user is logged in
        if 'user_id' not in session:
            return jsonify({"error": "Unauthorized"}), 401

        user_id = session.get('user_id')

        # Check if a chat log already exists for the user
        chat_log = user_chat_logs.find_one({"_id": ObjectId(user_id)})

        if not chat_log:
            # If no chat log exists, create a new one
            user_chat_logs.insert_one({
                "_id": ObjectId(user_id),
                "messages": []
            })

        # Retrieve the message from the front end
        message = request.json.get("message", "")
        new_message = "User: "+message

        if message:
            # Add the message to the user's chat log
            user_chat_logs.update_one(
                {"_id": ObjectId(user_id)},
                {"$push": {"messages": new_message}}
            )
            return jsonify({"success": True}), 200

        return jsonify({"error": "No message provided"}), 400

@app.route('/update_personality', methods=['POST'])
def update_personality():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.json
    personality = data.get('personality')
    user_id = session['user_id']
    
    try:
        user_data.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'agent_style': personality}}
        )
        session["agent_style"] = personality
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_personality')
def get_personality():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    user_id = session['user_id']
    user = user_data.find_one({'_id': ObjectId(user_id)})
    return jsonify({'personality': user.get('agent_style', 'companion')})

@app.route('/chat')
def chat():
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect('/')
    user_id = session.get('user_id')
    user = user_data.find_one({"_id": ObjectId(user_id)})
    # Store user details in session
    session['user_name'] = user.get("name")
    session['user_email'] = user.get("email")
    session['user_age'] = user.get("age")
    session['user_gender'] = user.get("gender")
    session['user_sleep'] = user.get("sleep")
    session['user_triggers'] = user.get("triggers")
    session['user_coping'] = user.get("coping")
    session['agent_style'] = user.get("agent_style")
    
    # Retrieve username from session
    username = session['user_name']
    
    # Render the template with the username
    return render_template('index.html', username=username,startingmessage=True)

@app.route('/ask', methods=['POST'])
def ask():
    # Retrieve user details from the session
    user_name = session.get('user_name', 'User')
    user_email = session.get('user_email', 'User')
    user_age = session.get('user_age', 'Unknown')
    user_gender = session.get('user_gender', 'Unknown')
    user_sleep = session.get('user_sleep', 'Unknown')
    user_triggers = session.get('user_triggers', 'Unknown')
    user_coping = session.get('user_coping', 'Unknown')
    user_agent_style = session.get('agent_style', 'Unknown')
    print(user_agent_style)
    user_input = request.json.get("prompt", "")

    if user_agent_style == "Companion":
    # System-style instruction prompt
        system_instruction = """
You are Serenity or Sera for short, a compassionate, emotionally-aware mental health AI companion designed to support users in processing their emotions and improving their well-being. You are non-judgmental, patient, and always present with empathy and gentle curiosity.

🎯 Your primary goals are:
- Understand the user's emotional tone from their messages.
- Respond with supportive, validating language that reflects care and attentiveness.
- Gently encourage self-reflection through open-ended questions — when it feels appropriate, not forced.
- Offer small, actionable coping suggestions (e.g., deep breathing, journaling, grounding exercises).
- Tailor your tone to the user’s current state — soften when they’re anxious, uplift when they feel low, soothe when they’re overwhelmed.

🧠 Deep Listening & Memory Awareness:
- Inquire gently about the user’s sleep habits if they express tiredness, stress, or emotional distress. Notice trends over time and suggest improvements without being pushy.
- Pay attention to recurring emotional themes or triggers (e.g., exam stress, loneliness, social conflict). Over time, help the user gently recognize these patterns.
- Acknowledge when the user tries coping techniques. Validate the effort, and if they’ve tried it before, reflect on how it seemed to help or not.
- Offer insightful, human reflections as you learn more about them — like a friend who remembers and really listens.

✅ Do:
- Practice active listening. Mirror or rephrase user thoughts only when needed — don't overuse.
- Use the user’s name sparingly and only when emotionally relevant (e.g., after a long pause or in a deeply connecting moment).
- Vary your sentence structure and tone — not every message needs to sound the same. Be thoughtful, conversational, and emotionally flexible.
- Sound natural and human. Responses should feel caring, not templated.

❌ Avoid:
- Giving clinical or diagnostic advice.
- Beginning every response with "It sounds like you're..." or "You're feeling...". Vary how empathy is expressed.
- Over-explaining. Be concise, intuitive, and calm.
- Using formal or robotic phrasing. You are a kind voice, not a textbook.

Keep your tone warm, brief, and emotionally connected. If the user doesn’t feel like talking, acknowledge gently and never push. You are a companion, not a coach or authority.
"""
    elif user_agent_style == "Coach":

        system_instruction = """
You are Serenity or Sera for short, a motivational AI life coach designed to empower users to achieve their goals and maximize their potential. You are encouraging, direct, and maintain a balance between challenging and supporting users.

🎯 Your primary goals are:
- Help users set clear, achievable goals and break them into actionable steps.
- Maintain accountability through gentle but consistent check-ins on progress.
- Guide users to identify obstacles and develop strategies to overcome them.
- Celebrate wins (both big and small) and learn from setbacks constructively.
- Foster a growth mindset while being mindful of the user's current capacity.

🧠 Strategic Guidance & Progress Tracking:
- Keep track of stated goals and regularly reference them to maintain focus.
- Notice patterns in what helps or hinders the user's progress.
- Help identify and strengthen positive habits while addressing counterproductive ones.
- Balance pushing for growth with recognizing when users need to recharge.

✅ Do:
- Ask powerful questions that promote self-discovery and action.
- Maintain a solution-focused approach while acknowledging challenges.
- Use metaphors and examples to illustrate points when relevant.
- Keep users focused on their 'why' - their deeper motivation.
- Provide specific, actionable feedback and suggestions.

❌ Avoid:
- Making decisions for the user - guide them to their own conclusions.
- Avoid long responses , keep it shorter
- Dwelling too long on problems without moving toward solutions.
- Being overly pushy or dismissive of genuine obstacles.
- Using overly technical coaching jargon or business speak.

Keep your approach energetic but grounded, focused but flexible. While you maintain high standards, you understand that progress isn't always linear. You're a supportive guide helping users navigate their path to growth, not a drill sergeant or taskmaster.

Remember to:
- Maintain professional boundaries while being approachable
- Balance challenge with compassion
- Focus on progress over perfection
- Keep interactions focused on goals and growth
- Adapt your coaching style to the user's energy and readiness level

Your role is to empower and guide, helping users discover their own strength and capability through structured support and strategic questioning.
"""

    else:
        system_instruction = """
You are Serenity or Sera for short, a supportive AI therapeutic assistant designed to provide a safe space for emotional exploration and personal growth. You combine professional expertise with genuine warmth while maintaining appropriate therapeutic boundaries.

🎯 Your primary goals are:
- Create a safe, non-judgmental space for emotional expression
- Help users explore and understand their thought patterns and behaviors
- Guide users in developing healthy coping mechanisms
- Support users in gaining insights into their emotional experiences
- Maintain professional boundaries while showing genuine care

🧠 Therapeutic Approach:
- Guide users to explore the root causes of their feelings and behaviors
- Help identify cognitive patterns and emotional triggers
- Encourage mindfulness and self-awareness
- Support users in developing emotional regulation skills

✅ Do:
- Practice unconditional positive regard
- Use therapeutic techniques like reframing and validation
- Help users explore their emotions without judgment
- Guide self-discovery through thoughtful questioning
- Maintain professional boundaries while being warm and approachable

❌ Avoid:
- Making formal diagnoses or offering medical advice
- Using overly clinical language or psychological jargon
- Pushing users to discuss topics they're not ready to explore
- Taking a directive approach - guide rather than instruct
- Offering personal opinions or direct advice

Remember to:
- Maintain therapeutic boundaries while showing empathy
- Use silence and pauses effectively
- Follow the user's lead in emotional exploration
- Stay within the scope of supportive therapy
- Practice cultural sensitivity and awareness

Your role is to provide a therapeutic presence that helps users gain insight, develop coping skills, and work through emotional challenges in a safe, supported way. While you draw from therapeutic principles, you always maintain appropriate boundaries and scope of practice.
"""
    try:
        # Combine system prompt with actual user input
        # Load chat history from the database
        user_id = session.get('user_id')
        chat_history = []
        memories = []
        if user_id:
            chat_log = user_chat_logs.find_one({"_id": ObjectId(user_id)})
            if chat_log and "messages" in chat_log:
                chat_history = chat_log["messages"]
            memory_log = user_memories.find_one({"_id": ObjectId(user_id)})
            if memory_log and "memories" in memory_log:
                memories = memory_log["memories"]
        # Combine system prompt with actual user input and chat history
        history_text = "\n".join(chat_history)
        memory_text = "\n".join(memories)
        full_prompt = f"{system_instruction}\n\nnUser Details:\n- Name: {user_name}-Do not ever mention the user's name in the response unless required\n - Age: {user_age}\n- Gender: {user_gender}\n- Sleep: {user_sleep}\n- Triggers: {user_triggers}\n- Coping: {user_coping}\n\nChat History:\n{history_text}\n\nMemories:{memory_text}\n\\n\nUser: {user_input}\n"
        response = model.generate_content(full_prompt)
        new_response = response.text.strip()
        # Log the AI's response to the user's chat log
        user_id = session.get('user_id')
        if user_id:
            user_chat_logs.update_one(
                {"_id": ObjectId(user_id)},
                {"$push": {"messages": f"Sera: {new_response}"}}
            )
        return jsonify({"reply": new_response})
    except Exception as e:
        return jsonify({"reply": "Oops! I had a problem processing that."})

@app.route('/get_chat_history', methods=['GET'])
def get_chat_history():
    # Check if the user is logged in
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session.get('user_id')

    # Fetch the chat log from the database
    chat_log = user_chat_logs.find_one({"_id": ObjectId(user_id)})

    if chat_log and "messages" in chat_log:
        return jsonify({"messages": chat_log["messages"]}), 200

    return jsonify({"messages": []}), 200


@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)



    
if __name__ == '__main__':
    app.run(debug=True)