# Loan Buddy - AI-Powered Loan Assistance Backend

This is the backend for **Loan Buddy**, an AI-powered loan assistance web application. It enables users to get insights into loan eligibility, types, and application processes through **speech-to-text, translation, text analytics, and text-to-speech services**.

---

## 🚀 Features

- **Speech-to-Text**: Converts user speech into text using **Sarvam AI**.
- **Text Translation**: Translates text between multiple Indian languages.
- **Text Analytics**: Provides loan-related insights based on user queries.
- **Text-to-Speech**: Converts responses into speech for better accessibility.
- **Loan Eligibility Analysis**: Extracts loan-related information from user inputs.
- **Session-based Conversation**: Stores and analyzes user queries for contextual responses.
- **MongoDB Integration**: Stores and retrieves chat history for better assistance.
- **Flask API**: Serves as a RESTful API for frontend integration.

---

## 🛠️ Tech Stack

- **Backend**: Flask, Python
- **Database**: MongoDB
- **API Services**: Sarvam AI, Google Gemini API
- **Others**: `dotenv` for environment variables, `Flask-CORS` for cross-origin requests

---

## 📦 Installation

### Prerequisites
- Python 3.x
- MongoDB (Cloud or Local)
- A valid **Sarvam AI API Key** and **Google Gemini API Key**

### Setup

1. **Clone the repository**
   ```sh
   git clone https://github.com/your-repo/loan-buddy-backend.git
   cd loan-buddy-backend
