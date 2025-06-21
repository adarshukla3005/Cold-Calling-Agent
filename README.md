# Cold Calling Agent

An intelligent AI-powered cold calling agent that can handle various scenarios such as interview screening, payment follow-ups, and meeting scheduling.

## Features

- Interview screening automation
- Payment follow-up reminders
- Demo scheduling assistant
- Calendar integration
- Email sending capabilities
- Speech recognition

## Setup

1. Install dependencies:
```
pip install -r requirements.txt
```

2. Configure credentials:
   - Replace placeholder in `src/config/calendar_credentials.json` with your Google Calendar API credentials

3. Run the application:
```
python app.py
```

## Project Structure

- `app.py`: Main application entry point
- `data/`: Contains scenario-specific data files
- `src/`: Source code
  - `config/`: Configuration files
  - `prompt/`: Prompt templates
  - `scenario/`: Specific use case implementations
- `utils/`: Utility functions

## Scenarios

- **Interview Screening**: Automates candidate screening calls
- **Payment Follow-up**: Reminder calls for pending payments
- **Demo Scheduling**: Schedule product demos with potential clients 