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
import pytz
import csv
import time
from datetime import datetime, timedelta
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pygame  # To play audio within Python

# Configure Gemini AI API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize Flask App
app = Flask(__name__)

# Cold Calling Scenarios
SCENARIOS = {
    "demo_scheduling": "Aap ek sales agent hain jo ERP demos schedule kar rahe hain. Availability ke bare mein puchiye, time slots suggest kijiye.",
    "interview_screening": "Aap ek HR agent hain jo candidates ko screen kar rahe hain. Experience aur skills ke bare mein relevant sawal puchiye.",
    "payment_followup": "Aap ek payment collection agent hain. Customers ko pending payments ke bare mein politely yaad dilaiye."
}

# Store scheduled meetings
scheduled_meetings = []

# Translator for Hinglish to Hindi conversion
translator = GoogleTranslator(source="en", target="hi")

def clean_text(text):
    """Removes special characters except for essential ones in Hindi pronunciation."""
    text = re.sub(r'[“”":,\'!@#$%^&*()_+=\[\]{}<>?/|\\]', '', text)  # Remove unwanted symbols
    text = text.replace('\n', ' ')  # Replace newlines with space
    return text

# Function: Convert Hinglish Text to Hindi Speech
def speak(text):
    try:
        text = clean_text(text)
        translation = translator.translate(text, src="en", dest="hi")
        hindi_text = translator.translate(text)

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
        print(f"Error in speak function: {e}")

# Flask Route: AI Chatbot
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    scenario = data.get("scenario", "demo_scheduling")
    user_input = data.get("message", "")

    try:
        prompt = f"{SCENARIOS[scenario]} Answer in Hinglish.\nUser: {user_input}\nAgent:"
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)

        ai_response = response.text if response and response.text else "Sorry, I couldn't process that."
        return jsonify({"response": ai_response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Function to Add Event to Open Source Calendar (Google Calendar or CalDAV)
def add_to_calendar(name, contact, date, time, scenario):
    try:
        event_data = {
            "summary": f"Appointment with {name}",
            "description": f"Contact: {contact}\nScenario: {scenario}",
            "start": {"dateTime": f"{date}T{time}:00", "timeZone": "Asia/Kolkata"},
            "end": {"dateTime": f"{date}T{(int(time.split(':')[0]) + 1)}:{time.split(':')[1]}:00", "timeZone": "Asia/Kolkata"},
        }

        # Replace this URL with your calendar API endpoint (Google Calendar API or CalDAV)
        calendar_api_url = "https://www.googleapis.com/calendar/v3/users/me/settings"

        response = requests.post(calendar_api_url, json=event_data)

        if response.status_code == 200:
            return "Schedule successfully added to the calendar!"
        else:
            return f"Failed to add schedule: {response.text}"

    except Exception as e:
        return f"Error adding event: {e}"

#------------------------------------------------------------------------
# Load Google Calendar API credentials
SCOPES = ["https://www.googleapis.com/auth/calendar"]
SERVICE_ACCOUNT_FILE = "calendar_credentials.json"  # Update with your actual file

# Authenticate with Google Calendar API
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
service = build("calendar", "v3", credentials=credentials)

def schedule_meeting(name, contact, date, time):
    """Creates an event in Google Calendar."""
    try:
        start_datetime = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S")
        end_datetime = start_datetime + timedelta(hours=1)  # Assume 1-hour meeting

        event = {
            "summary": f"ERP Demo with {name}",
            "description": f"Demo scheduled with {name} (Contact: {contact})",
            "start": {"dateTime": start_datetime.isoformat(), "timeZone": "Asia/Kolkata"},
            "end": {"dateTime": end_datetime.isoformat(), "timeZone": "Asia/Kolkata"},
        }

        created_event = service.events().insert(calendarId="primary", body=event).execute()
        return f"Meeting scheduled successfully on {date} at {time}!"

    except Exception as e:
        return f"Error scheduling meeting: {str(e)}"

@app.route("/schedule", methods=["POST"])
def schedule():
    """Handles scheduling requests from the UI."""
    data = request.json
    name = data.get("name")
    contact = data.get("contact")
    date = data.get("date")
    time = data.get("time")

    if not all([name, contact, date, time]):
        return jsonify({"error": "Missing required fields!"}), 400

    try:
        confirmation_msg = schedule_meeting(name, contact, date, time)
        return jsonify({"message": confirmation_msg})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#-------------------------------------------------------------------------

# Function to run Flask in a separate thread
def run_flask():
    app.run(debug=False, use_reloader=False)

# Start Flask in a thread
threading.Thread(target=run_flask, daemon=True).start()

# Streamlit UI
st.title("Hinglish Cold Calling AI")
scenario = st.selectbox("Select Scenario:", ["demo_scheduling", "interview_screening", "payment_followup"])

# Speech Input Button
if st.button("🎙️ Speak"):
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.write("Listening...")
        audio = recognizer.listen(source)

    try:
        user_input = recognizer.recognize_google(audio, language="en-IN")
        st.write(f"Recognized: {user_input}")
    except sr.UnknownValueError:
        user_input = "Sorry, mujhe samajh nahi aaya."
    except sr.RequestError:
        user_input = "Speech Recognition service filhaal uplabdh nahi hai."
else:
    user_input = st.text_input("Enter Message:")

if st.button("Send"):
    response = requests.post("http://127.0.0.1:5000/chat", json={"scenario": scenario, "message": user_input})

    if response.status_code == 200:
        ai_response = response.json().get("response", "No response from AI.")
    else:
        ai_response = f"Error: {response.json().get('error', 'Unknown error')}"

    st.write("AI Response:", ai_response)

    # Speak AI Response in Hindi
    speak(ai_response)

#---------------------------------------------
if scenario == "demo_scheduling":
    st.subheader("📅 Schedule a Demo Meeting")
    
    name = st.text_input("Enter Your Name:")
    contact = st.text_input("Enter Contact Number:")
    date = st.date_input("Select Date:")
    time = st.time_input("Select Time:")
    email = st.text_input("Enter Email Address:")

    if st.button("Schedule Meeting"):
        meeting_details = {
            "name": name,
            "contact": contact,
            "email": email,
            "date": str(date),
            "time": str(time),
        }

        response = requests.post("http://127.0.0.1:5000/schedule", json=meeting_details)

        if response.status_code == 200:
            st.success(response.json().get("message", "Meeting scheduled!"))
            speak("Meeting successfully scheduled!")  # Speak confirmation
        else:
            st.error(response.json().get("error", "An error occurred!"))

CSV_FILE = "meetings.csv"  # File to store meetings

def save_meetings_to_csv(meetings):
    """Save or update meetings in a CSV file."""
    fieldnames = ["Meeting Summary        " "Date  "     "Time (IST)"     "Email"]
    
    # Ensure CSV file exists
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(fieldnames)  # Write header
    
    # Read existing meetings to avoid duplicates
    existing_meetings = set()
    try:
        with open(CSV_FILE, mode="r") as file:
            reader = csv.reader(file)
            next(reader, None)  # Skip header
            for row in reader:
                existing_meetings.add(tuple(row))
    except Exception as e:
        print(f"Error reading CSV file: {e}")

    # Prepare new meetings list
    new_meetings = set(meetings)
    updated_meetings = sorted(existing_meetings.union(new_meetings), key=lambda x: x[1])  # Sort by date

    # Write updated data back to CSV
    try:
        with open(CSV_FILE, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(fieldnames)  # Write header
            writer.writerows(updated_meetings)  # Write updated meeting records
        print("✅ Meetings successfully saved in meetings.csv")
    except Exception as e:
        print(f"Error writing to CSV file: {e}")

def list_scheduled_meetings():
    """Fetch upcoming meetings and save them to a CSV file."""
    now = datetime.datetime.now(datetime.UTC).isoformat()

    try:
        events_result = service.events().list(
            calendarId="primary", timeMin=now, maxResults=50, singleEvents=True, orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])

        if not events:
            print("No upcoming meetings found.")
            return

        meeting_list = []
        ist_timezone = pytz.timezone("Asia/Kolkata")  

        for event in events:
            start_utc = event["start"].get("dateTime", event["start"].get("date"))
            start_datetime_utc = datetime.datetime.fromisoformat(start_utc[:-1])  
            start_datetime_ist = start_datetime_utc.replace(tzinfo=datetime.UTC).astimezone(ist_timezone)
            email = event.get("attendees", [{}])[0].get("email", "N/A")

            meeting_summary = event['summary']
            meeting_date = start_datetime_ist.strftime('%Y-%m-%d')
            meeting_time = start_datetime_ist.strftime('%H:%M:%S')

            meeting_list.append((meeting_summary, meeting_date, meeting_time, email))

        # Save meetings to CSV
        save_meetings_to_csv(meeting_list)

    except Exception as e:
        print(f"Error fetching Google Calendar events: {e}")

list_scheduled_meetings()


    # Initialize pygame mixer
pygame.mixer.init()

if scenario == "interview_screening":
    st.subheader("🗣️ AI-Powered Interview Screening")

    def speak(text):
        """Converts text to speech and plays it in real-time."""
        tts = gTTS(text=text, lang="hi")  # Use Hindi pronunciation
        filename = "response.mp3"
        tts.save(filename)  # Save audio

        pygame.mixer.music.load(filename)  # Load into player
        pygame.mixer.music.play()  # Play the speech
        
        # Wait till the speech finishes
        while pygame.mixer.music.get_busy():
            time.sleep(0.5)

        pygame.mixer.music.stop()  # Stop the music
        pygame.mixer.quit()  # Properly close the mixer
        time.sleep(0.5)  # Allow system to release file

        os.remove(filename)  # Safely remove the file

    name = st.text_input("Enter Candidate Name:")
    if name:
        speak(f"Hello {name}, kripya apna introduction dijiye.")

    experience = st.text_input("Enter Years of Experience:")
    if experience:
        speak(f"{experience} badhiya hai, kripya apna work experience share kare.")

    skills = st.text_input("Enter Key Skills:")
    if skills:
        speak(f"Great! Your key skills are {skills}.")

    email = st.text_input("Enter Candidate Email:")

    if st.button("Send Interview Invite"):
        interview_details = {
            "name": name,
            "experience": experience,
            "skills": skills,
            "email": email,
        }
        speak("Your interview details have been recorded. You will receive an email shortly.")
        st.success("✅ Interview invite sent successfully!")