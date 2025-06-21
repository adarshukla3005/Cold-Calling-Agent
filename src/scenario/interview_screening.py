import streamlit as st
import json
import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
import os
import time
from src.config.config import llm

# =================== Function Definitions =================== #

def generate_question(job_role, previous_answers):
    """Generate the next question dynamically in Hinglish based on previous answers."""
    context = "\n".join(previous_answers) if previous_answers else "No previous answers."
    prompt = f"""
    Tum ek AI interviewer ho jo {job_role} ke liye interview le raha hai.
    Ye candidate ke pehle ke answers hain:
    {context}
    Tumhe iske jawab ke basis par ek logical agla sawal puchna hai jo role se related ho.
    Sawal **Hinglish** (mix of Hindi and English in Latin script) me likhna hai.
    Bas ek sawal likho bina kisi explanation ke.
    """
    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        return response.strip() if isinstance(response, str) else response.get("content", "Error: No question generated").strip()
    except Exception as e:
        return f"Error generating question: {str(e)}"
    
def evaluate_response(job_role, answer):
    """Evaluate the candidate's response (stored in JSON but not displayed)."""
    prompt = f"""
    Tum ek AI interviewer ho jo {job_role} ke liye interview le raha hai.
    Candidate ne ye jawab diya:
    "{answer}"
    Evaluation sirf Hinglish me likhna hai (Hindi + English in Latin script).
    Tumhe candidate ke jawab ka short aur precise evaluation dena hai.
    Ye batao ki jawab kahan weak tha aur kya missing tha.
    Aur agar kuch acha jawab hain toh unhe bhi mention karo.
    two line me crisp response do. Extra explanation mat do.
    """
    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        return response.strip() if isinstance(response, str) else response.get("content", "Error: No evaluation generated").strip()
    except Exception as e:
        return f"Error evaluating response: {str(e)}"

def speak_text(text):
    """Generate audio using gTTS and autoplay it in Streamlit."""
    import tempfile
    import base64
    import os
    
    # Create a temporary file with a .mp3 extension
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
        temp_audio_path = temp_file.name
    
    # Generate the audio file
    tts = gTTS(text=text, lang="en")
    tts.save(temp_audio_path)
    
    # Read the audio file and encode it
    with open(temp_audio_path, "rb") as audio_file:
        audio_bytes = audio_file.read()
    
    # Create an audio element with autoplay
    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
    audio_html = f"""
        <audio autoplay="true">
            <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
            Your browser does not support the audio element.
        </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)
    
    # Clean up the temporary file
    try:
        os.remove(temp_audio_path)
    except:
        pass  # If file cannot be deleted now, it will be cleaned up later

def save_interview_data():
    """Save session questions and answers to a JSON file."""
    data = {
        "name": st.session_state["candidate_name"],
        "role": st.session_state["selected_role"],
        "questions": st.session_state["questions"],
        "answers": st.session_state["answers"]
    }
    with open("data/interview_data.json", "a") as f:
        json.dump(data, f, indent=4)
        f.write("\n")  # ✅ Append new interviews in a structured way

def record_voice():
    """Capture and return the user's voice input."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.write("🎤 Listening... Speak now!")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return "❌ Could not understand the audio, please try again."
    except sr.RequestError:
        return "⚠️ Google Speech API not responding."

# =================== 🌟 Streamlit UI =================== #

def interview_screening():
    st.title("🎙 AI-Powered Interviewer")

    job_roles = [
        "Software Engineer", "AI/ML Engineer", "Machine Learning Engineer",
        "Data Analyst", "Cybersecurity Analyst", "DevOps Engineer", "Data Scientist","Product Analyst"
    ]

    candidate_name = st.text_input("Enter Your Name:", key="candidate_name")
    selected_role = st.selectbox("Select Job Role:", job_roles, key="selected_role")

    if st.button("Start Interview", key="start_interview"):
        if candidate_name and selected_role:
            st.session_state["session_id"] = f"{candidate_name}-{selected_role}"
            st.session_state["questions"] = []
            st.session_state["answers"] = []
            st.session_state["interview_started"] = True

            # ✅ Start with Greeting + Introduction Request
            greeting = f"Namaste {candidate_name}! Please give a short introduction about yourself."
            st.session_state["questions"].append(greeting)
            st.session_state["current_question"] = greeting

            speak_text(greeting)

        else:
            st.warning("Please enter your name and select a role to proceed.")

    if st.session_state.get("interview_started"):
        # ✅ Show conversation history
        for i, (question, answer) in enumerate(zip(st.session_state["questions"], st.session_state["answers"])):
            st.write(f"**Q{i+1}:** {question}")
            st.write(f"🗣 **Your Answer:** {answer}")

        # ✅ Show the current question
        if len(st.session_state["questions"]) < 5:
            st.write(f"**Q{len(st.session_state['questions'])}:** {st.session_state['current_question']}")

        if st.button("🎤 Speak Answer"):
            user_answer = record_voice()

            if "❌" in user_answer or "⚠️" in user_answer:
                st.warning(user_answer)
            else:
                st.session_state["answers"].append(user_answer)

                if len(st.session_state["questions"]) < 4:
                    next_question = generate_question(st.session_state["selected_role"], st.session_state["answers"])
                    st.session_state["questions"].append(next_question)
                    st.session_state["current_question"] = next_question
                    speak_text(next_question)
                else:
                    # ✅ If it's the 4th question, show Finish Interview button
                    st.session_state["show_finish_button"] = True

        if st.session_state.get("show_finish_button", False):
            if st.button("✅ Finish Interview"):
                final_message = "Aapka interview complete ho gaya hai. Hum aapko aage ke process ke baare mein inform karenge. Dhanyawad!"
                st.write(f"🎉 **{final_message}**")
                speak_text(final_message)

                # ✅ Save the interview data
                save_interview_data()

                # ✅ Reset the session state for a new interview
                time.sleep(2)
                for key in ["interview_started", "questions", "answers", "session_id", "show_finish_button"]:
                    st.session_state.pop(key, None)

if __name__ == "__main__":
    interview_screening()