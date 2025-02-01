import os
import traceback
from dotenv import load_dotenv
import requests
import re
import time
import json
from pathlib import Path
from io import BytesIO
from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService
from PIL import Image
import pdfplumber
import google.generativeai as genai
from moviepy.editor import VideoFileClip, concatenate_videoclips

# Configure Manim settings for widescreen video (16:9 aspect ratio)
config.frame_width = 16
config.frame_height = 9
config.pixel_height = 1080
config.pixel_width = 1920
config.frame_rate = 30  # Standard 30 fps

# Configuration class
class Config:
    BASE_DIR = Path(r"D:\Nirma\6th Semester\MINeD").resolve()
    OUTPUT_DIR = BASE_DIR / "media/videos"
    PDF_FILE = BASE_DIR / "Xavier_Glorot.pdf"
    FINAL_VIDEO_FILE = OUTPUT_DIR / "final_video_new.mp4"
    
    load_dotenv()

    # Initialize Gemini
    GOOGLE_API_KEY = os.getenv('GEMINI_API_KEY')
    PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')

    @classmethod
    def setup_directories(cls):
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)

# Extract text content from the PDF file
def extract_paper_content(pdf_path):
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            pdf_text = " ".join([page.extract_text() or "" for page in pdf.pages])
        return pdf_text
    except Exception as e:
        print(f"Error extracting content: {e}")
        traceback.print_exc()
        return None

# Generate content using Gemini API
def generate_gemini_content(pdf_text, retries=3, delay=2):
    for attempt in range(retries):
        try:
            load_dotenv()
            genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
            model = genai.GenerativeModel("gemini-pro")

            prompt = f"""
            Your task is to analyze the provided research paper and create a storytelling-style explanation
            that is suitable for video narration. Ensure the explanation flows smoothly from beginning to end,
            covering all major aspects of the research study in a clear, natural, and engaging way.

            Research Paper:

            {pdf_text[:2500]}
            """

            response = model.generate_content(prompt)

            return response.text.strip()
        except Exception as e:
            print(f"Error in Gemini API call (attempt {attempt + 1}): {e}")
            traceback.print_exc()
            time.sleep(delay)

    return None

# Fetch an image from Pexels API
def fetch_image(keyword):
    try:
        headers = {"Authorization": Config.PEXELS_API_KEY}
        params = {"query": keyword, "per_page": 1}
        response = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if "photos" in data and data["photos"]:
            return data["photos"][0]["src"]["original"]
    except Exception as e:
        print(f"Error fetching image for keyword '{keyword}': {e}")
    return None


class PaperExplanationScene(VoiceoverScene):
    def __init__(self, content):
        super().__init__()
        self.content = content
        self.camera.background_color = WHITE  # Default background color
        self.set_speech_service(GTTSService(lang="en"))

    def construct(self):
        # AI/ML-related images to display in the background
        keywords_for_images = ["neural network", "data science"]  # AI/ML-related keywords
        images = []
        for keyword in keywords_for_images:
            image_url = fetch_image(keyword)
            if image_url:
                try:
                    response = requests.get(image_url)
                    img_content = BytesIO(response.content)
                    image = ImageMobject(Image.open(img_content)).scale_to_fit_height(config.frame_height).move_to(ORIGIN)
                    images.append(image)
                except Exception as e:
                    print(f"Error fetching/saving background image: {e}")

        # Display the first image in the background for the entire video
        if images:
            background_image = images[0]
            self.add(background_image)

        # Now add formatted, bold, and larger text in the center
        sections = self.content.split("\n")

        for section in sections:
            if not section.strip():
                continue

            # Format the text: Bold, larger font size, and center it
            text_for_scene = Text(
                section,
                font_size=72,  # Increased font size
                color=BLACK,
                line_spacing=1.2,
                font="Times New Roman",
                width=config.frame_width * 0.8  # Make sure text does not exceed 80% of the screen width
            ).move_to(ORIGIN)  # Center text horizontally and vertically

            # Add the text to the scene
            self.add(text_for_scene)

            # Add voiceover for the section
            with self.voiceover(section):
                self.wait(len(section) // 15)  # Adjust duration for the section based on length

            # Remove text after the speech is finished
            self.remove(text_for_scene)

        # Add closing text
        closing_text = Text(
            "Thank You for Watching!",
            font_size=72,  # Larger font size
            color=BLACK,
            font="Times New Roman",
        ).move_to(ORIGIN)

        self.add(closing_text)
        self.wait(3)
        self.play(FadeOut(closing_text))








# Main function
def main():
    try:
        Config.setup_directories()

        if not Config.PDF_FILE.exists():
            raise FileNotFoundError(f"PDF file not found at {Config.PDF_FILE}")

        pdf_text = extract_paper_content(Config.PDF_FILE)
        if not pdf_text:
            print("No text extracted from PDF.")
            return

        content = generate_gemini_content(pdf_text)
        if not content:
            print("Failed to generate content from Gemini.")
            return

        scene = PaperExplanationScene(content)
        scene.render()

        output_file = Path(scene.renderer.file_writer.movie_file_path)
        if output_file.exists():
            print(f"Animation created successfully at {output_file}")
        else:
            print("Error: Animation output not found.")

    except Exception as e:
        print(f"Error in main workflow: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()