from google import genai
from dotenv import load_dotenv
import os

# Load from .env file
load_dotenv()

# Access the keys
api_key = os.getenv("GOOGLE_GEMINI_API_KEY")

client = genai.Client(api_key=api_key)
llm_ = client.models
def llm(prompt:str):
    return llm_.generate_content(
        contents=prompt,
        model='gemini-2.0-flash').text
