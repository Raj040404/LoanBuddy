import requests
 import base64
 import os
 import sounddevice as sd
 import numpy as np
 import wave
 import json
 from llama_cpp import Llama
 from flask import Flask, request
 from urllib.request import urlopen
 
 # Sarvam API details
 API_KEY = "6e4561d4-58c2-40ba-bd2d-46ee2fc4c520"
 TEXT_ANALYTICS_URL = "https://api.sarvam.ai/text-analytics"
 SPEECH_TO_TEXT_URL = "https://api.sarvam.ai/speech-to-text"
 TEXT_TO_SPEECH_URL = "https://api.sarvam.ai/text-to-speech"
 HEADERS = {"api-subscription-key": API_KEY}
 
 # WhatsMeow service endpoint
 WHATSMEOW_URL = "http://localhost:8080/send"
 
 # Predefined context for loans
 LOAN_CONTEXT = """
 To check loan eligibility, you need a steady income and a good credit score above 600.
 To apply for a loan, gather your ID, income proof, and address proof, then submit an application online or at a bank.
 For financial tips, save 20% of your income monthly and avoid unnecessary debt to improve your financial health.
 """
 
 # Load LLaMA model
 try:
     llm = Llama(
         model_path="/home/Bruce/LoanAdvisor/LoanAdv_New/llama-2-7b-chat.Q4_K_M.gguf",
         n_gpu_layers=35,
         n_ctx=2048,
         verbose=True
     )
     print("LLaMA loaded successfully. Running with GPU support.")
 except Exception as e:
     print(f"Error loading LLaMA: {e}. Using fallback.")
     llm = None
 
 app = Flask(__name__)
 sarvam = None
 
 # Store user states (e.g., language preference)
 user_states = {}
 
 class SarvamAI:
     def __init__(self, api_key):
         self.api_key = api_key
         self.base_url = "https://api.sarvam.ai"
         self.headers = {"api-subscription-key": self.api_key}
 
     def text_analytics(self, text):
         if not text or "Error" in text:
             return "Error: Invalid or missing transcription."
         questions = [{"id": "q001", "text": f"What should the user do or know based on this query: '{text}'? Answer in English only.", "type": "short answer"}]
         payload = {"text": LOAN_CONTEXT + "\nUser query: " + text, "questions": json.dumps(questions)}
         try:
             response = requests.post(TEXT_ANALYTICS_URL, headers=HEADERS, data=payload)
             return response.json()["answers"][0].get("utterance", "No clear response.")
         except requests.exceptions.RequestException as e:
             return f"Error: API request failed. {str(e)}"
 
     def speech_to_text(self, audio_file, model="saarika:v2"):
         url = f"{self.base_url}/speech-to-text"
         if not os.path.exists(audio_file):
             return f"Error: File '{audio_file}' not found."
         try:
             with open(audio_file, "rb") as file:
                 files = {"file": (audio_file, file, "audio/wav")}
                 data = {"model": model, "with_diarization": "false"}
                 response = requests.post(url, headers=self.headers, files=files, data=data)
                 return response.json().get("transcript", "Error: 'transcript' key missing.")
         except requests.exceptions.RequestException as e:
             return f"Error: STT API request failed. {str(e)}"
 
     def text_to_speech(self, text, language):
         if not text or "Error" in text:
             return "Error: No valid text for TTS."
         lang_codes = {"english": "en-IN", "hindi": "hi-IN", "assamese": "as-IN"}
         speakers = {"english": "arvind", "hindi": "meera", "assamese": "arvind"}
         payload = {
             "inputs": [text],
             "target_language_code": lang_codes.get(language, "en-IN"),
             "speaker": speakers.get(language, "meera"),
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
                 with open("response_audio.wav", "wb") as f:
                     f.write(audio_bytes)
                 return "response_audio.wav"
             return f"Error: Failed to generate audio. {response_data}"
         except requests.exceptions.RequestException as e:
             return f"Error: TTS API failed. {str(e)}"
 
 def refine_response(raw_response, user_input, language):
     if "Error" in str(raw_response) or "No clear" in raw_response:
         if language == "hindi":
             return "पागल है क्या भोस्डीके, लोन की बात समझ में नहीं आई!"
         elif language == "assamese":
             return "পাগল নেকি বোহতী, লোনৰ কথা বুজি পোৱা নাই!"
         else:
             return "Are you nuts, bro? Couldn’t figure out the loan thing!"
     if llm is None:
         return f"Bro, for the loan, {raw_response}."
     prompt = f"Rephrase this into one short, clear, friendly sentence, no nonsense: '{raw_response}' for '{user_input}' [END]"
     try:
         output = llm(prompt, max_tokens=100, temperature=0.3, top_k=10, top_p=0.7, repeat_penalty=1.5, stop=["[END]"])
         return output["choices"][0]["text"].split(":")[-1].split("[END]")[0].strip()
     except Exception as e:
         print(f"LLaMA refinement error: {e}")
         return raw_response
 
 def send_whatsapp_message(to, message, media_path=None):
     payload = {"to": to, "message": message}
     try:
         if media_path and os.path.exists(media_path):
             files = {"file": (os.path.basename(media_path), open(media_path, "rb"), "audio/wav")}
             response = requests.post(WHATSMEOW_URL, files=files, data={"to": to, "message": message})
         else:
             response = requests.post(WHATSMEOW_URL, json=payload)
         if response.status_code == 200:
             print(f"Message sent to {to}: {message}")
             if media_path:
                 os.remove(media_path)  # Clean up temporary file
         else:
             print(f"Failed to send message: {response.text}")
     except requests.exceptions.RequestException as e:
         print(f"Error sending message: {e}")
 
 @app.route("/incoming", methods=["POST"])
 def incoming_message():
     global sarvam
     if sarvam is None:
         sarvam = SarvamAI(API_KEY)
 
     data = request.json
     if not data or "from" not in data or "message" not in data:
         return "Invalid request", 400
 
     from_number = data["from"]
     user_query = data["message"].strip()
     language = user_states.get(from_number, "english")  # Default to English if not set
 
     if from_number not in user_states:
         user_states[from_number] = {"language": "english", "state": "awaiting_start"}
 
     if user_query.lower() == "/start" and user_states[from_number]["state"] == "awaiting_start":
         menu = (
             "Welcome to Loan Advisor! Choose an option:\n"
             "1. Loan Eligibility Check\n"
             "2. Loan Application Guidance\n"
             "3. Financial Literacy Tips\n"
             "4. Set Language (English/Hindi/Assamese)\n"
             "Reply with the number (e.g., '1') to select."
         )
         send_whatsapp_message(from_number, menu)
         user_states[from_number]["state"] = "awaiting_choice"
         return "OK", 200
 
     if user_states[from_number]["state"] == "awaiting_choice":
         if user_query.lower().startswith("set "):
             lang = user_query.split(" ")[1].lower()
             if lang in ["english", "hindi", "assamese"]:
                 user_states[from_number]["language"] = lang
                 send_whatsapp_message(from_number, f"Language set to {lang}")
                 send_whatsapp_message(from_number, "Choose an option:\n1. Loan Eligibility Check\n2. Loan Application Guidance\n3. Financial Literacy Tips\nReply with the number.")
             else:
                 send_whatsapp_message(from_number, "Invalid language. Use 'set english', 'set hindi', or 'set assamese'.")
             return "OK", 200
         elif user_query.isdigit() and int(user_query) in [1, 2, 3]:
             options = {
                 "1": "How do I know if I’m eligible for a loan?",
                 "2": "How do I apply for a loan?",
                 "3": "Give me some financial tips."
             }
             user_query = options[user_query]
             raw_response = sarvam.text_analytics(user_query)
             refined_response = refine_response(raw_response, user_query, language)
             send_whatsapp_message(from_number, refined_response)
             # Send audio response
             audio_file = sarvam.text_to_speech(refined_response, language)
             if isinstance(audio_file, str) and os.path.exists(audio_file):
                 send_whatsapp_message(from_number, "Here’s your audio response:", media_path=audio_file)
             user_states[from_number]["state"] = "awaiting_start"
             return "OK", 200
         else:
             send_whatsapp_message(from_number, "Invalid choice. Reply with a number (1-3) or 'set language'.")
             return "OK", 200
 
     if user_query.lower() == "exit":
         send_whatsapp_message(from_number, "Catch you later!")
         user_states.pop(from_number, None)
         return "OK", 200
 
     return "OK", 200
 
 if __name__ == "__main__":
     sarvam = SarvamAI(API_KEY)
     print("Starting WhatsApp Loan Buddy on port 5000...")
     app.run(host="0.0.0.0", port=5000)
