import smtplib
import ssl
from email.message import EmailMessage
from flask import Flask, request, jsonify

app = Flask(__name__)

# Define email sender credentials
EMAIL_SENDER = "shukla305adarsh@gmail.com"
EMAIL_PASSWORD = "vovfnibebenavmrv"  # Use an App Password, not your regular Gmail password.

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

        # Email subject and body
        subject = "📅 Your Demo Meeting is Scheduled!"
        body = f"""
        Dear {name},

        Your demo meeting has been successfully scheduled.

        📅 **Date:** {date}  
        ⏰ **Time:** {time}  
        📍 **Meeting Link:** [Click here to join]({event_link})  

        Please be on time. If you need to reschedule, reply to this email.

        Looking forward to speaking with you!

        Best regards,  
        **Adarsh Shukla**  
        iMAX Technologies  
        📞 +91-8707446780
        """

        # Create email message
        em = EmailMessage()
        em["From"] = EMAIL_SENDER
        em["To"] = email_receiver
        em["Subject"] = subject
        em.set_content(body)

        # Securely send email
        context = ssl.create_default_context()
        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.sendmail(EMAIL_SENDER, email_receiver, em.as_string())

        return jsonify({"message": f"Demo schedule sent to {name} ({email_receiver})!"}), 200

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)