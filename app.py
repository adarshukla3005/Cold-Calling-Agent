import os
import google.generativeai as genai
import speech_recognition as sr
import requests
import streamlit as st
from flask import Flask, request, jsonify
import threading
from deep_translator import GoogleTranslator
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
import io
import re
from datetime import datetime
import datetime
import pygame
from src.scenario.interview_screening import interview_screening,generate_question,evaluate_response
from src.scenario.followup_payment import payment_followup
from src.scenario.demo_scheduling import demo_scheduling
from src.prompt.prompt import get_scenario_prompt
import smtplib
import ssl
from email.message import EmailMessage
from flask import Flask, request, jsonify
import speech_recognition as sr
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure Gemini AI API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize Flask App
app = Flask(__name__)

# Store scheduled meetings
scheduled_meetings = []

# Initialize Translator
translator = GoogleTranslator(source="auto", target="hi")

def recognize_speech():
    """Recognizes speech from microphone and returns text."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎤 Listening... Speak now!")
        
        # Reduce background noise dynamically
        recognizer.adjust_for_ambient_noise(source, duration=1)

        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)  # Wait for speech
            text = recognizer.recognize_google(audio, language="en-IN")  # Recognize speech
            return text
        except sr.WaitTimeoutError:
            return "No speech detected. Please try again."
        except sr.UnknownValueError:
            return "Sorry, mujhe samajh nahi aaya."
        except sr.RequestError:
            return "Speech Recognition service filhaal uplabdh nahi hai."
        except Exception as e:
            return f"Error: {e}"

def clean_text(text):
    """Cleans the text by removing special characters."""
    text = re.sub(r'[""":,\'!@#$%^&*()_+=\[\]{}<>?/|\\]', '', text)  # Remove unwanted symbols
    text = text.replace('\n', ' ')  # Replace newlines with space
    return text

def speak(text):
    """Converts Hinglish text to Hindi speech and plays it."""
    try:
        text = clean_text(text)  # Clean input text
        hindi_text = translator.translate(text)  # Translate to Hindi

        # Generate Hindi Speech using gTTS
        tts = gTTS(text=hindi_text, lang="hi")

        # Save to buffer instead of a file
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)

        # Play the audio directly
        audio = AudioSegment.from_file(audio_buffer, format="mp3")
        play(audio)

    except Exception as e:
        print(f"Error in speech synthesis: {e}")

# Flask Route: AI Chatbot
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    scenario = data.get("scenario")
    user_input = data.get("message", "")

    try:
        # Get the appropriate prompt using our new prompt module
        prompt = get_scenario_prompt(scenario, user_input)
        
        # Generate response using the model
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)

        # Get the response text, fallback to error message if no response
        ai_response = response.text if response and response.text else "Sorry, I couldn't process that."
        return jsonify({"response": ai_response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/schedule", methods=["POST"])
def schedule_meeting():
    try:
        data = request.json
        name = data.get("name")
        email = data.get("email")
        contact = data.get("contact")
        date = datetime.strptime(data.get("date"), "%Y-%m-%d").date()
        time = datetime.strptime(data.get("time"), "%H:%M:%S").time()

        # Call the function from demo_scheduling.py
        event_link = demo_scheduling(name, email, contact, date, time)

        if isinstance(event_link, dict) and "error" in event_link:
            return jsonify({"error": event_link["error"]}), 400
        
        return jsonify({"message": "Meeting scheduled successfully!", "event_link": event_link})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/extract', methods=['POST'])
def extract():
    data = request.json
    message = data.get("message", "")

    # Dummy logic for entity extraction (Replace with LLM API)
    extracted_info = {
        "name": "Adarsh",
        "date": "2025-03-05",
        "time": "14:00"
    }
    return jsonify(extracted_info)

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

@app.route("/payment_followup", methods=["POST"])
def send_email():
    try:
        # Get JSON data from Streamlit request
        data = request.get_json()
        name = data.get("name")
        email_receiver = data.get("email")  # Customer's email from Streamlit
        amount = data.get("amount")

        if not name or not email_receiver or not amount:
            return jsonify({"error": "Missing required fields"}), 400

        # Email subject
        subject = "🔔 Payment/Order Follow-up Reminder"

        # **Formatted HTML Email Body**
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; padding: 20px;">
            <p>Dear <strong>{name}</strong>,</p>
            
            <p>I hope this email finds you well.</p>

            <p>We wanted to follow up regarding the pending payment of <strong>₹{amount}</strong> for your recent transaction with us.</p>

            <p>As per our records, the payment is yet to be received. We kindly request you to process the payment at your earliest convenience to ensure smooth operations and avoid any service disruptions.</p>

            <p>If the payment has already been made, please disregard this message. However, if you require any assistance or have any concerns, feel free to reach out.</p>

            <p>Best regards,</p>
            <p><strong>Adarsh Shukla</strong></p>
            <p>IIT Roorkee</p>
            <p>📞 +91-8707446780</p>
        </body>
        </html>
        """

        # Create email message
        em = EmailMessage()
        em["From"] = EMAIL_SENDER
        em["To"] = email_receiver
        em["Subject"] = subject
        em.set_content("This is a payment reminder.")  # Fallback text (optional)
        em.add_alternative(body, subtype="html")  # Add HTML content

        # Securely send email
        context = ssl.create_default_context()
        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.sendmail(EMAIL_SENDER, email_receiver, em.as_string())

        return jsonify({"message": f"Payment reminder sent to {name} ({email_receiver})!"}), 200

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500
    
@app.route("/send_demo_schedule", methods=["POST"])
def send_demo_schedule():
    try:
        # Get JSON data from Streamlit request
        data = request.get_json()
        name = data.get("name")
        email_receiver = data.get("email")
        date = data.get("date")
        time = data.get("time")
        event_link = data.get("event_link")  # Google Calendar event link

        if not name or not email_receiver or not date or not time or not event_link:
            return jsonify({"error": "Missing required fields"}), 400

        # Email subject
        subject = "📅 Your Demo Meeting is Scheduled!"

        # HTML Email Body
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; padding: 20px;">
            <p>Dear <b>{name}</b>,</p>
            
            <p>Your demo meeting has been successfully scheduled.</p>

            <p><b>Date:</b> {date} <br>
               <b>Time:</b> {time} <br>
               <b>Meeting Link:</b> <a href="{event_link}" style="color: #1a73e8; text-decoration: none;">Join</a>
            </p>

            <p>Please be on time. If you need to reschedule, reply to this email.</p>

            <p>Looking forward to speaking with you!</p>

            <p>Best regards,</p>
            <p><b>Adarsh Shukla</b></p>
            <p>IIT Roorkee</p>
            <p>+91-8707446780</p>
        </body>
        </html>
        """

        # Create email message
        em = EmailMessage()
        em["From"] = EMAIL_SENDER
        em["To"] = email_receiver
        em["Subject"] = subject
        em.add_alternative(body, subtype="html")  # Use HTML for formatting

        # Securely send email
        context = ssl.create_default_context()
        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.sendmail(EMAIL_SENDER, email_receiver, em.as_string())

        return jsonify({"message": f"Demo schedule sent to {name} ({email_receiver})!"}), 200

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500


# Interview session storage
interview_sessions = {}

@app.route('/start', methods=['POST'])
def start_interview():
    """Start a new interview session."""
    try:
        data = request.json
        job_role = data.get("job_role", "").strip()

        if not job_role:
            return jsonify({"error": "Job role is required"}), 400  

        session_id = len(interview_sessions) + 1
        interview_sessions[session_id] = {"job_role": job_role, "questions": [], "answers": []}

        question = generate_question(job_role, [])
        interview_sessions[session_id]["questions"].append(question)

        return jsonify({"session_id": session_id, "question": question})

    except Exception as e:
        print(f"❌ Error in /start: {e}")  
        return jsonify({"error": str(e)}), 500  

@app.route('/respond', methods=['POST'])
def respond():
    """Process user answer and generate next question."""
    try:
        data = request.json
        session_id = data.get("session_id")
        answer = data.get("answer", "").strip()

        if not session_id or session_id not in interview_sessions:
            return jsonify({"error": "Invalid session"}), 400

        job_role = interview_sessions[session_id]["job_role"]
        interview_sessions[session_id]["answers"].append(answer)
        evaluation = evaluate_response(job_role, answer)

        if len(interview_sessions[session_id]["questions"]) < 8:
            next_question = generate_question(job_role, interview_sessions[session_id]["answers"])
            interview_sessions[session_id]["questions"].append(next_question)
        else:
            next_question = "Interview complete! ✅"

        return jsonify({"evaluation": evaluation, "next_question": next_question})

    except Exception as e:
        print(f"❌ Error in /respond: {e}")  
        return jsonify({"error": str(e)}), 500  


# Function to run Flask in a separate thread
def run_flask():
    app.run(debug=False, use_reloader=False)

# Start Flask in a thread
threading.Thread(target=run_flask, daemon=True).start()

# # Sidebar - Company Details
# Sidebar - Company Details
st.sidebar.title("Defsys Software Solutions")
st.sidebar.write("Welcome to Defsys Technologies, a leader in AI-powered business solutions.")
# st.sidebar.write("At Defsys, we specialize in innovative AI applications that transform business processes and enhance operational efficiency.")

# # Sidebar - Your Details
# st.sidebar.title("About Developer")
# st.sidebar.write("👤 **Adarsh Shukla**")
# st.sidebar.write("📞 Contact: 8707446780")

# Streamlit UI
st.title("Hinglish Cold Calling AI")
# Add scenario selection buttons to sidebar
st.sidebar.title("Select Scenario")

# Initialize scenario in session state if not already there
if 'current_scenario' not in st.session_state:
    st.session_state.current_scenario = None

# Create buttons that stay visible and update scenario when clicked
if st.sidebar.button("Demo Scheduling"):
    st.session_state.current_scenario = "demo_scheduling"
if st.sidebar.button("Interview Screening"):
    st.session_state.current_scenario = "interview_screening" 
if st.sidebar.button("Payment Follow-up"):
    st.session_state.current_scenario = "payment_followup"
if st.sidebar.button("Reset Scenario"):
    st.session_state.current_scenario = None

# Display current mode
current_mode = st.session_state.current_scenario if st.session_state.current_scenario else "General (All Scenarios)"
st.sidebar.success(f"Current Mode: {current_mode}")

# Streamlit UI
st.title("AI Voice Assistant")

# Initialize response variables
if 'ai_response' not in st.session_state:
    st.session_state.ai_response = ""
if 'ai_speech_response' not in st.session_state:
    st.session_state.ai_speech_response = ""

# Speech Input Button
if st.button("🎙️ Speak", key="speak_button"):
    user_input = recognize_speech()
    st.write(f"Recognized: {user_input}")
else:
    user_input = st.text_input("Enter Message:")

if st.button("Send"):
    # Include the selected scenario in the request
    request_data = {
        "message": user_input,
        "scenario": st.session_state.current_scenario
    }
    response = requests.post("http://127.0.0.1:5000/chat", json=request_data)

    if response.status_code == 200:
        st.session_state.ai_response = response.json().get("response", "No response from AI.")
        
        # Extract AI's pure response (remove "User:" part)
        lines = st.session_state.ai_response.split("\n")
        st.session_state.ai_speech_response = "\n".join(lines[1:]) if "User:" in lines[0] else st.session_state.ai_response
    else:
        st.session_state.ai_speech_response = f"Error: {response.json().get('error', 'Unknown error')}"
        st.session_state.ai_response = st.session_state.ai_speech_response

    # Display the response
    st.write("AI Response:", st.session_state.ai_response)
    speak(st.session_state.ai_speech_response)  # Speak only AI's response

# Display the last response if it exists
elif st.session_state.ai_response:
    st.write("AI Response:", st.session_state.ai_response)

# Initialize Pygame mixer for audio playback
pygame.mixer.init()

# Scenario-specific UI
scenario = st.session_state.current_scenario
if scenario == "demo_scheduling":
    demo_scheduling()
elif scenario == "interview_screening":
    interview_screening()
elif scenario == "payment_followup":
    payment_followup(st, lambda msg: print(msg))