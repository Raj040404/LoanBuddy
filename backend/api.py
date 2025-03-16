from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import base64
import os
import sounddevice as sd
import numpy as np
import wave
import json
import re
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
from bson.objectid import ObjectId

load_dotenv()
app = Flask(__name__)
CORS(app)

mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client['loan_buddy']
chats_collection = db['chats']

API_KEY = os.getenv("SARVAM_API_KEY")
SPEECH_TO_TEXT_URL = "https://api.sarvam.ai/speech-to-text"
TRANSLATE_URL = "https://api.sarvam.ai/translate"
TEXT_ANALYTICS_URL = "https://api.sarvam.ai/text-analytics"
TEXT_TO_SPEECH_URL = "https://api.sarvam.ai/text-to-speech"
HEADERS = {"api-subscription-key": API_KEY, "Content-Type": "application/json"}

LOAN_CONTEXT = """
To check loan eligibility, you need a steady income and a good credit score above 600.
### Types of Loans Available in India
1. Personal Loans: Unsecured loans for personal use (e.g., medical emergencies, weddings, travel). Interest rates: 9% to 24% p.a. Tenure: 1 to 5 years.
2. Home Loans: For purchasing, constructing, or renovating a house. Interest rates: 8% to 12% p.a. Tenure: Up to 30 years.
3. Car Loans: For purchasing new or used cars. Interest rates: 7% to 12% p.a. Tenure: 1 to 7 years.
4. Education Loans: For funding higher education in India or abroad. Interest rates: 8% to 14% p.a. Tenure: Up to 15 years.
5. Gold Loans: Secured loans against gold jewelry. Interest rates: 7% to 29% p.a. Tenure: 3 months to 3 years.
6. Business Loans: For business expansion, working capital, or equipment purchase. Interest rates: 10% to 24% p.a. Tenure: 1 to 5 years.
7. Loan Against Property (LAP): Secured loan against property (residential or commercial). Interest rates: 8% to 15% p.a. Tenure: Up to 20 years.
8. Two-Wheeler Loans: For purchasing two-wheelers (bikes, scooters). Interest rates: 10% to 18% p.a. Tenure: 1 to 5 years.
9. Agricultural Loans: For farmers for crop production, equipment, or land purchase. Interest rates: 2% to 12% p.a. (subsidized rates for farmers). Tenure: 1 to 5 years.
10. Microfinance Loans: Small loans for low-income individuals or self-help groups. Interest rates: 18% to 26% p.a. Tenure: 6 months to 3 years.

### Eligibility Criteria for Loans
1. Age: Minimum 21 years, Maximum 60-65 years (retirement age for salaried individuals).
2. Income: Minimum monthly income ₹15,000 to ₹25,000 for personal loans. Higher for home/business loans. ITR for self-employed (last 2-3 years).
3. Employment Type: Salaried (6 months to 1 year experience) or Self-employed (2-3 years business continuity).
4. Credit Score: 750+ (excellent, lowest rates), 700-749 (good), 650-699 (fair, higher rates), Below 650 (poor, may be rejected).
5. Debt-to-Income Ratio (DTI): EMI obligations should not exceed 40-50% of monthly income.
6. Documentation: PAN card, Aadhaar card, address proof, income proof (salary slips, bank statements), property documents (for secured loans).

### Loan Eligibility Based on Credit Score
- 750+: High eligibility, lowest interest rates.
- 700-749: Moderate eligibility, competitive rates.
- 650-699: Low eligibility, higher rates, may need collateral.
- Below 650: Very low eligibility, likely rejected unless secured.

### Tips to Improve Loan Eligibility
1. Maintain a good credit score by paying EMIs and bills on time.
2. Reduce existing debt to lower DTI ratio.
3. Show consistent income with salary slips or ITR.
4. Choose the right loan type for your needs.
5. Add a co-applicant for better approval chances.
"""

class SarvamAI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.sarvam.ai"
        self.headers = {"api-subscription-key": self.api_key, "Content-Type": "application/json"}

    def record_audio(self, filename="user_input.wav", duration=5, sample_rate=16000):
        print("\U0001F3A4 Recording... Speak now!")
        audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype=np.int16)
        sd.wait()
        print("✅ Recording complete!")
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())
        return filename if os.path.exists(filename) else "Error: Audio file not saved."

    def speech_to_text(self, audio_file, language_code, model="saarika:v2"):
        url = f"{self.base_url}/speech-to-text"
        if not os.path.exists(audio_file):
            return f"Error: File '{audio_file}' not found."
        
        valid_languages = {'unknown', 'hi-IN', 'bn-IN', 'kn-IN', 'ml-IN', 'mr-IN', 'od-IN', 'pa-IN', 'ta-IN', 'te-IN', 'en-IN', 'gu-IN'}
        print(f"Debug: Received language_code for STT: {language_code}")
        
        language_map = {
            'english': 'en-IN', 'hindi': 'hi-IN', 'bengali': 'bn-IN', 'kannada': 'kn-IN', 'malayalam': 'ml-IN',
            'marathi': 'mr-IN', 'odia': 'od-IN', 'punjabi': 'pa-IN', 'tamil': 'ta-IN', 'telugu': 'te-IN', 'gujarati': 'gu-IN'
        }
        if language_code in language_map:
            language_code = language_map[language_code]
        if not isinstance(language_code, str) or language_code not in valid_languages:
            print(f"Warning: Invalid language_code '{language_code}' for STT, defaulting to 'en-IN'")
            language_code = 'en-IN'
        
        print(f"Debug: Sending language_code to STT: {language_code}")

        try:
            with open(audio_file, "rb") as file:
                files = {"file": (audio_file, file, "audio/wav")}
                data = {"model": model, "language_code": language_code, "with_diarization": "false"}
                response = requests.post(url, headers={"api-subscription-key": self.api_key}, files=files, data=data)
                response_data = response.json()
                if "transcript" not in response_data:
                    print(f"⚠️ STT API Response Error: {response_data}")
                    return "Error: 'transcript' key missing."
                print(f"Debug: STT response: {response_data['transcript']}")
                return response_data["transcript"]
        except requests.exceptions.RequestException as e:
            return f"Error: STT API request failed. {str(e)}"

    def translate(self, text, target_language_code, source_language_code="en-IN"):
        if not text or "Error" in text:
            return "Error: No valid text to translate."
        
        language_map = {
            'english': 'en-IN', 'hindi': 'hi-IN', 'bengali': 'bn-IN', 'kannada': 'kn-IN', 'malayalam': 'ml-IN',
            'marathi': 'mr-IN', 'odia': 'od-IN', 'punjabi': 'pa-IN', 'tamil': 'ta-IN', 'telugu': 'te-IN', 'gujarati': 'gu-IN'
        }
        if target_language_code in language_map:
            target_language_code = language_map[target_language_code]
        if source_language_code in language_map:
            source_language_code = language_map[source_language_code]
        
        print(f"Debug: Translating from {source_language_code} to {target_language_code}")

        payload = {
            "input": text,
            "source_language_code": source_language_code,
            "target_language_code": target_language_code,
            "model": "mayura:v1"
        }
        try:
            response = requests.post(TRANSLATE_URL, headers=self.headers, json=payload)
            response_data = response.json()
            if "translated_text" in response_data:
                print(f"Debug: Translated response: {response_data['translated_text']}")
                return response_data["translated_text"]
            print(f"Error: Translation failed - {response.text}")
            return text
        except requests.exceptions.RequestException as e:
            print(f"Error: Translate API failed - {str(e)}")
            return text

    def text_analytics(self, text):
        if not text or "Error" in text:
            return "Error: Invalid or missing transcription."
        questions = [{"id": "q001", "text": f"Given this query: '{text}', what specific advice should the user follow to address their situation? Answer in English only.", "type": "short answer"}]
        payload = {"text": LOAN_CONTEXT + "\nUser query: " + text, "questions": json.dumps(questions)}
        try:
            response = requests.post(TEXT_ANALYTICS_URL, headers={"api-subscription-key": self.api_key}, data=payload)
            response_data = response.json()
            if response.status_code == 200 and "answers" in response_data and response_data["answers"]:
                raw = response_data["answers"][0].get("utterance", "No clear response.")
                print(f"Debug: Text Analytics raw response: {raw}")
                return raw
            return f"Error: {response.status_code} - {response.text}"
        except requests.exceptions.RequestException as e:
            return f"Error: API request failed. {str(e)}"

    def text_to_speech(self, text, language_code):
        if not text or "Error" in text:
            return "Error: No valid text for TTS."
        
        valid_languages = {'hi-IN', 'bn-IN', 'kn-IN', 'ml-IN', 'mr-IN', 'od-IN', 'pa-IN', 'ta-IN', 'te-IN', 'en-IN', 'gu-IN'}
        print(f"Debug: Received language_code for TTS: {language_code}")
        
        language_map = {
            'english': 'en-IN', 'hindi': 'hi-IN', 'bengali': 'bn-IN', 'kannada': 'kn-IN', 'malayalam': 'ml-IN',
            'marathi': 'mr-IN', 'odia': 'od-IN', 'punjabi': 'pa-IN', 'tamil': 'ta-IN', 'telugu': 'te-IN', 'gujarati': 'gu-IN'
        }
        if language_code in language_map:
            language_code = language_map[language_code]
        if not isinstance(language_code, str) or language_code not in valid_languages:
            print(f"Warning: Invalid language_code '{language_code}' for TTS, defaulting to 'en-IN'")
            language_code = 'en-IN'
        
        print(f"Debug: Sending language_code to TTS: {language_code}")

        cleaned_text = re.sub(r'Here\'s.*?:', '', text, flags=re.DOTALL).strip()
        cleaned_text = re.sub(r'\*\*.*?\*\*', '', cleaned_text).strip()
        if language_code == "en-IN" and re.search(r'[A-Za-z]', cleaned_text):
            cleaned_text = cleaned_text.split('.')[0].strip()
        if len(cleaned_text) > 500:
            cleaned_text = cleaned_text[:500]
        print(f"Debug: Cleaned TTS input: {cleaned_text} (Length: {len(cleaned_text)} chars)")

        payload = {
            "inputs": [cleaned_text],
            "target_language_code": language_code,
            "speaker": "meera",
            "pitch": 0,
            "pace": 1.0,
            "loudness": 1.5,
            "speech_sample_rate": 22050,
            "enable_preprocessing": True,
            "model": "bulbul:v1"
        }
        try:
            response = requests.post(TEXT_TO_SPEECH_URL, headers=self.headers, json=payload)
            response_data = response.json()
            if "audios" in response_data and response_data["audios"]:
                audio_bytes = base64.b64decode(response_data["audios"][0])
                print(f"Debug: TTS audio length: {len(audio_bytes)} bytes")
                return audio_bytes
            return f"Error: Failed to generate audio - {response_data}"
        except requests.exceptions.RequestException as e:
            return f"Error: TTS request failed - {str(e)}"

def process_response(user_input, language_code, sarvam, session, chat_history):
    # Only translate if language_code is not en-IN
    query_text = user_input
    if language_code != "en-IN":
        translated_query = sarvam.translate(user_input, "en-IN", language_code)
        if "Error" in translated_query:
            print(f"Query translation to English failed, using original: {user_input}")
            query_text = user_input
        else:
            query_text = translated_query

    # Update session with new information
    credit_score_match = re.search(r'credit score.*?(\d+)', query_text, re.IGNORECASE)
    income_proof_match = re.search(r'\b(yes|no)\b', query_text.lower()) and "proof" in query_text.lower()
    loan_amount_match = re.search(r'loan.*?(\d+)', query_text, re.IGNORECASE)
    income_match = re.search(r'income.*?(\d+)', query_text, re.IGNORECASE)
    property_value_match = re.search(r'property.*?(\d+)', query_text, re.IGNORECASE)

    if credit_score_match and not session.get("credit_score"):
        session["credit_score"] = int(credit_score_match.group(1))
    if income_proof_match and session.get("income_proof") is None:
        session["income_proof"] = "yes" in query_text.lower()
    if loan_amount_match:
        session["loan_amount"] = int(loan_amount_match.group(1))
    if income_match:
        session["income"] = int(income_match.group(1))
    if property_value_match:
        session["property_value"] = int(property_value_match.group(1))

    # Set loan type if not already set
    loan_types = ["personal", "home", "car", "education", "gold", "business", "loan against property", 
                  "two-wheeler", "agricultural", "microfinance"]
    if not session.get("loan_type"):
        for loan_type in loan_types:
            if re.search(rf'\b{loan_type}\b', query_text.lower()) or re.search(rf'\b{loan_type.replace(" ", "-")}\b', query_text.lower()):
                session["loan_type"] = loan_type.capitalize()
                break

    # Use Gemini API for all queries
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    headers = {"Content-Type": "application/json"}
    session_context = f"User's current session details: {json.dumps(session)}"
    
    # Format chat history for the prompt
    history_text = "Conversation history:\n"
    if chat_history and isinstance(chat_history, list):
        for msg in chat_history:
            if isinstance(msg, dict):
                sender = msg.get("sender", "unknown")
                content = msg.get("content", "")
                history_text += f"{sender.capitalize()}: {content}\n"
            else:
                print(f"Debug: Skipping invalid message format: {msg}")
    else:
        history_text += "No prior conversation.\n"

    # Check if key eligibility data is available
    has_eligibility_data = session.get("credit_score") is not None and session.get("income_proof") is not None

    # Craft a more polite and user-friendly prompt
    prompt = (
        f"{LOAN_CONTEXT}\n\n"
        f"{session_context}\n\n"
        f"{history_text}\n\n"
        f"User's latest query (translated to English if needed): '{query_text}'. "
        f"Provide a warm, polite, and user-friendly English response under 500 characters. "
        f"Use a supportive tone to guide the user, explaining why any requested info (e.g., credit score, income proof) is needed "
        f"to help them secure their {session.get('loan_type', 'desired')} loan. "
        f"Use the session data (credit_score: {session.get('credit_score')}, income_proof: {session.get('income_proof')}, "
        f"loan_type: {session.get('loan_type')}, property_value: {session.get('property_value')}, income: {session.get('income')}) "
        f"and the conversation history to avoid repeating questions already asked or answered. "
    )
    if has_eligibility_data:
        prompt += (
            f"The user has shared enough details (credit_score: {session['credit_score']}, income_proof: {session['income_proof']}) "
            f"to confirm basic eligibility for a {session['loan_type']} loan. Offer clear, encouraging next steps to apply, "
            f"like gathering documents or visiting a bank, and why these steps matter. "
            f"End with a friendly follow-up question (e.g., 'How much loan do you need?' or 'Which bank would you like to use?')."
        )
    else:
        prompt += (
            f"Respond to the latest query with kindness and clarity, avoiding repetition from the history or session. "
            f"If asking for info (e.g., credit score or income proof), explain it’s to ensure they get the best loan terms. "
            f"End with a gentle follow-up question to gather missing details (e.g., 'Could you share your credit score?' "
            f"or 'Do you have income proof handy?') based on what’s not yet provided."
        )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", headers=headers, json=payload)
        response_data = response.json()
        if response.status_code == 200 and "candidates" in response_data and response_data["candidates"]:
            refined_english = response_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            print(f"Debug: Gemini refined (English): {refined_english}")
            final_refined = refined_english if language_code == "en-IN" else sarvam.translate(refined_english, language_code, "en-IN")
            if "Error" in final_refined:
                print(f"Translation to {language_code} failed, using English: {refined_english}")
                return refined_english
            return final_refined
        else:
            print(f"Debug: Gemini API error: {response_data}")
            return "I’m sorry, I couldn’t process that—could you please try again?"
    except Exception as e:
        print(f"Gemini refinement error: {e}")
        return "I’m sorry, something went wrong—let’s try that again, okay?"

# Update /api/ask
@app.route('/api/ask', methods=['POST'])
def ask_question():
    data = request.json
    question = data.get('question')
    chat_id = data.get('chatId')
    generate_audio = data.get('generate_audio', False)
    chat = chats_collection.find_one({"_id": ObjectId(chat_id)})
    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    language_code = chat.get('language', 'en-IN')
    session = chat['session']
    chat_history = chat.get('messages', [])  # Retrieve chat history as a list of dicts

    final_response = process_response(question, language_code, sarvam, session, chat_history)
    
    # Save updated session and messages
    chats_collection.update_one(
        {"_id": ObjectId(chat_id)},
        {
            "$set": {"session": session},
            "$push": {"messages": [
                {"sender": "user", "content": question, "timestamp": datetime.now()},
                {"sender": "bot", "content": final_response, "timestamp": datetime.now()}
            ]}
        }
    )

    if generate_audio:
        audio_bytes = sarvam.text_to_speech(final_response, language_code)
        if isinstance(audio_bytes, bytes):
            return jsonify({"answer": final_response, "audio": base64.b64encode(audio_bytes).decode('utf-8')})
        return jsonify({"answer": final_response, "error": audio_bytes}), 500
    return jsonify({"answer": final_response})

# Update /api/record
@app.route('/api/record', methods=['POST'])
def record_and_process():
    data = request.json
    chat_id = data.get('chatId')
    chat = chats_collection.find_one({"_id": ObjectId(chat_id)})
    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    language_code = chat.get('language', 'en-IN')
    session = chat['session']
    chat_history = chat.get('messages', [])  # Retrieve chat history as a list of dicts

    recorded_file = sarvam.record_audio()
    if "Error" in recorded_file:
        return jsonify({"error": recorded_file}), 500
    
    transcript = sarvam.speech_to_text(recorded_file, language_code)
    if "Error" in transcript:
        return jsonify({"error": transcript}), 500

    final_response = process_response(transcript, language_code, sarvam, session, chat_history)
    audio_bytes = sarvam.text_to_speech(final_response, language_code)

    chats_collection.update_one(
        {"_id": ObjectId(chat_id)},
        {
            "$set": {"session": session},
            "$push": {"messages": [
                {"sender": "user", "content": transcript, "timestamp": datetime.now()},
                {"sender": "bot", "content": final_response, "timestamp": datetime.now()}
            ]}
        }
    )

    if isinstance(audio_bytes, bytes):
        return jsonify({
            "transcript": transcript,
            "answer": final_response,
            "audio": base64.b64encode(audio_bytes).decode('utf-8')
        })
    return jsonify({"transcript": transcript, "answer": final_response, "error": audio_bytes}), 500


sarvam = SarvamAI(API_KEY)

@app.route('/api/chats/<user_id>', methods=['GET'])
def get_chats(user_id):
    chats = list(chats_collection.find({"userId": user_id}).sort("createdAt", -1))
    for chat in chats:
        chat['_id'] = str(chat['_id'])
    return jsonify(chats)

@app.route('/api/chats/new', methods=['POST'])
def new_chat():
    data = request.json
    user_id = data.get('userId')
    language = data.get('language', 'en-IN')
    chat = {
        "userId": user_id,
        "language": language,
        "messages": [],
        "session": {"credit_score": None, "loan_amount": None, "has_income_proof": None, "loan_type": None},
        "createdAt": datetime.now()
    }
    result = chats_collection.insert_one(chat)
    chat['_id'] = str(result.inserted_id)
    return jsonify(chat), 201

@app.route('/api/chats/<chat_id>/message', methods=['POST'])
def add_message(chat_id):
    data = request.json
    sender = data.get('sender')
    content = data.get('content')
    chat = chats_collection.find_one({"_id": ObjectId(chat_id)})
    if not chat:
        return jsonify({"error": "Chat not found"}), 404
    chats_collection.update_one(
        {"_id": ObjectId(chat_id)},
        {"$push": {"messages": {"sender": sender, "content": content, "timestamp": datetime.now()}}}
    )
    updated_chat = chats_collection.find_one({"_id": ObjectId(chat_id)})
    updated_chat['_id'] = str(updated_chat['_id'])
    return jsonify(updated_chat)



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)), debug=True, use_reloader=False)