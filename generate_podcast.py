import logging
import os
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from template import enhance_prompt, initial_dialogue_prompt, plan_prompt
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from utils.script import generate_script, parse_script_plan
from utils.audio_gen import generate_podcast

# Load environment variables
load_dotenv()

# Initialize Gemini
GOOGLE_API_KEY = os.getenv('GEMINI_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not found")

genai.configure(api_key=GOOGLE_API_KEY)

# Initialize the Gemini model using LangChain
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0.7,
    google_api_key=GOOGLE_API_KEY,
)

# chains
chains = {
    "plan_script_chain": plan_prompt | llm | parse_script_plan,
    "initial_dialogue_chain": initial_dialogue_prompt | llm | StrOutputParser(),
    "enhance_chain": enhance_prompt | llm | StrOutputParser(),
}

def process_paper(pdf_path: str) -> str:
    try:
        # Generate the podcast script from the PDF
        logging.info("Generating podcast script...")
        script = generate_script(pdf_path, chains, llm)
        logging.info("Podcast script generation complete!")

        # Generate the podcast audio files and merge them
        logging.info("Generating podcast audio files...")
        output_file = generate_podcast(script)
        logging.info("Podcast generation complete!")

        return output_file

    except Exception as e:
        logging.error(f"Error processing paper: {str(e)}")
        raise
