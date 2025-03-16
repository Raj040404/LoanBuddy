# Loan Buddy - A Multilingual Loan Application Assistant

Loan Buddy is a Flutter-based mobile application designed to assist users in applying for loans in India. It features a conversational interface powered by AI, supports multiple India>

---

## Features

- **Multilingual Support**: Chat in English, Hindi, Assamese, Kannada, or Tamil.
- **Voice Interaction**: Use speech-to-text to input queries and listen to responses via text-to-speech.
- **Loan Eligibility Assistance**: Provide your credit score, loan amount, and loan type to get personalized loan advice.
- **Natural Conversations**: Powered by Google Gemini for human-like responses.
- **Session Management**: Tracks user inputs (credit score, loan amount, loan type, tenure) across the conversation.
- **Responsive UI**: Clean and user-friendly interface with dark/light theme support.

---

## Tech Stack

- **Frontend**: Flutter (Dart)
- **Backend**: Flask (Python)
- **APIs**:
  - Sarvam AI: Speech-to-Text (STT) and Text-to-Speech (TTS)
  - Google Gemini: Natural Language Processing
- **Dependencies**:
  - Flutter: `flutter_sound`, `http`, `http_parser`, `permission_handler`, `google_fonts`, `flutter_spinkit`
  - Flask: `flask`, `flask-session`, `flask-cors`, `pydub`, `requests`

---

## Prerequisites

Before setting up the project, ensure you have the following installed:

### For Flutter (Frontend)
- **Flutter SDK**: Version 3.0.0 or higher
- **Dart**: Included with Flutter
- **Android Studio** or **VS Code** with Flutter and Dart plugins
- An Android/iOS emulator or physical device

### For Flask (Backend)
- **Python**: Version 3.8 or higher
- **pip**: Python package manager
- **FFmpeg**: For audio conversion (`pydub` dependency)
  - Ubuntu: `sudo apt install ffmpeg`
  - macOS: `brew install ffmpeg`
  - Windows: Download from [FFmpeg website](https://ffmpeg.org/download.html) and add to PATH

### API Keys
- **Sarvam AI API Key**: For STT and TTS (replace in `mola.py`)
- **Google Gemini API Key**: For NLP (replace in `mola.py`)

---

## Setup Instructions

### 1. Clone the Repository

git clone https://github.com/your-username/loan-buddy.git
cd loan-buddy

flutter pub get

flutter run

loan-buddy/
│
├── backend/
│   ├── mola.py              # Flask backend with STT, TTS, and Gemini integration
│   ├── flask_session/       # Session storage directory
│   └── requirements.txt     # Backend dependencies
│
├── frontend/
│   ├── lib/
│   │   ├── screens/
│   │   │   ├── home_screen.dart  # Home screen with input fields
│   │   │   └── chat_screen.dart  # Chat screen with ListView
│   │   └── main.dart        # App entry point
│   ├── pubspec.yaml         # Flutter dependencies
│   └── android/             # Android-specific files
│
└── README.md                # Project documentation

API_KEY = "your-sarvam-api-key"
GEMINI_API_KEY = "your-gemini-api-key"
