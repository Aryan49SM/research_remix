from logging import config
import os
import time
from typing import Optional
import warnings
from pathlib import Path
from dotenv import load_dotenv
from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService
from moviepy.editor import VideoFileClip
import pdfplumber
import google.generativeai as genai
import json
import math
import re
import traceback
from datetime import datetime
#fi
# Configure Manim settings
config.frame_width = 9
config.frame_height = 16
config.pixel_height = 1920
config.pixel_width = 1080
config.frame_rate = 60

class Config:
    # Base directories
    BASE_DIR = Path(__file__).parent
    MEDIA_DIR = BASE_DIR / "media"
    TEMP_DIR = BASE_DIR / "temp"
    
    # Input/Output paths
    PDF_FILE: Optional[Path] = None  # Will be set dynamically
    FINAL_VIDEO_FILE: Optional[Path] = None  # Will be set dynamically
    
    # Video settings
    RESOLUTION = "1920x1080"
    FPS = 60
    BACKGROUND_COLOR = "#000000"
    TEXT_COLOR = "#FFFFFF"
    FONT_SIZE = 40
    DURATION = 3  # seconds per segment
    PRIMARY_COLOR = "#58A6FF"
    SECONDARY_COLOR = "#7EE787"
    ACCENT_COLOR = "#FF6B6B"
    BACKGROUND_COLOR = "#0D1117"

    
    load_dotenv()
    
    GOOGLE_API_KEY =os.getenv("GEMINI_API_KEY")

    @classmethod
    def setup_directories(cls):
        """Create necessary directories and set up paths"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create directories if they don't exist
        cls.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        cls.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        
        # Set up video output path
        video_dir = cls.MEDIA_DIR / "videos"
        video_dir.mkdir(parents=True, exist_ok=True)
        cls.FINAL_VIDEO_FILE = video_dir / f"reel_{timestamp}.mp4"

def get_default_story_content():
    return {
        'hook': "Welcome to an exciting journey of innovation and discovery.",
        'problem': "In today's world, researchers face complex challenges that require innovative solutions.",
        'solution': "Through groundbreaking research and advanced technology, we've developed a powerful approach.",
        'impact': "Our findings show remarkable improvements and real-world applications.",
        'future': "This opens new possibilities for future innovations and advancements."
    }


def process_paper_content(pdf_path):
    try:
        # Extract text from PDF
        with pdfplumber.open(str(pdf_path)) as pdf:
            text = " ".join([page.extract_text() or "" for page in pdf.pages])
        
        if not text.strip():
            print("No text extracted from PDF, using default content")
            return get_default_story_content()

        # Initialize Google AI
        load_dotenv()
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = """
        Analyze the given research paper and create a narrative that STRICTLY uses information from the paper itself.
        Extract the following sections:

        1. HOOK: One attention-grabbing sentence about the paper's main contribution
        2. PROBLEM: The specific research problem or gap addressed in this paper
        3. SOLUTION: The actual methodology or approach proposed in the paper
        4. IMPACT: The concrete results and findings reported in the paper
        5. FUTURE: Future work mentioned in the paper's conclusion

        Use ONLY information present in the paper. Do not add external context or generalizations.
        Keep each section concise but specific to the paper's content.

        Format the response exactly as:
        HOOK:
        [hook from paper]
        PROBLEM:
        [problem from paper]
        SOLUTION:
        [solution from paper]
        IMPACT:
        [impact from paper]
        FUTURE:
        [future from paper]
        """
        
        response = model.generate_content(prompt + "\n\nPaper text:\n" + text[:5000])
        content = parse_gemini_response(response.text)
        
        # Validate content
        if not all(content.values()):
            print("Invalid content from Gemini, using default")
            return get_default_story_content()
            
        return content
        
    except Exception as e:
        print(f"Error in processing: {e}")
        return get_default_story_content()


def parse_gemini_response(response_text):
    sections = {
        'hook': '',
        'problem': '',
        'solution': '',
        'impact': '',
        'future': ''
    }
    
    current_section = None
    
    for line in response_text.split('\n'):
        line = line.strip()
        lower_line = line.lower()
        
        if 'hook:' in lower_line:
            current_section = 'hook'
        elif 'problem:' in lower_line:
            current_section = 'problem'
        elif 'solution:' in lower_line:
            current_section = 'solution'
        elif 'impact:' in lower_line:
            current_section = 'impact'
        elif 'future:' in lower_line:
            current_section = 'future'
        elif current_section and line and ':' not in line:
            sections[current_section] += ' ' + line
    
    # Clean up the content
    for key in sections:
        sections[key] = sections[key].strip()
        if not sections[key]:
            sections[key] = get_default_story_content()[key]
    
    return sections

def get_voiceover_content(text_content):
    """Generate voiceover scripts that stick to paper content"""
    return {
        'hook': f"{text_content['hook']}",
        'problem': f"The researchers identified this challenge: {text_content['problem']}",
        'solution': f"Their approach was as follows: {text_content['solution']}",
        'impact': f"The research yielded these results: {text_content['impact']}",
        'future': f"Looking ahead, {text_content['future']}"
    }

def get_visual_descriptions(content):
    """Generate visual descriptions for each section using Gemini"""
    try:
        load_dotenv()
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = """
        For each section below, suggest a simple visual representation using basic geometric shapes that can be created with Manim.
        Use only these elements: circles, squares, rectangles, lines, dots, and arrows.
        Keep descriptions simple and focused on the main message.

        Format your response exactly as:
        HOOK_VISUAL:
        [visual description]
        PROBLEM_VISUAL:
        [visual description]
        SOLUTION_VISUAL:
        [visual description]
        IMPACT_VISUAL:
        [visual description]
        FUTURE_VISUAL:
        [visual description]

        Content to visualize:
        """
        
        response = model.generate_content(prompt + str(content))
        return parse_visual_response(response.text)
    except Exception as e:
        print(f"Error generating visuals: {e}")
        return get_default_visuals()

def parse_visual_response(response_text):
    visuals = {
        'hook_visual': '',
        'problem_visual': '',
        'solution_visual': '',
        'impact_visual': '',
        'future_visual': ''
    }
    
    current_section = None
    for line in response_text.split('\n'):
        line = line.strip()
        if '_VISUAL:' in line.upper():
            current_section = line.lower().replace(':', '').strip()
        elif current_section and line:
            visuals[current_section] = line.strip()
    
    return visuals or get_default_visuals()

def get_default_visuals():
    return {
        'hook_visual': 'A pulsing circle with radiating lines',
        'problem_visual': 'Three connected nodes showing complexity',
        'solution_visual': 'A path through obstacles showing progress',
        'impact_visual': 'Rising bars showing growth',
        'future_visual': 'An expanding star showing potential'
    }

class ReelContent(VoiceoverScene):
    def _init_(self):
        super()._init_()
        self.content = []
        self.camera.background_color = Config.BACKGROUND_COLOR
        self.content = get_default_story_content()
        self.voiceover_content = get_voiceover_content(self.content)
        self.visuals = get_visual_descriptions(self.content)

    def set_content(self, content):
        self.content = content if content else get_default_story_content()
        self.voiceover_content = get_voiceover_content(self.content)
        self.visuals = get_visual_descriptions(self.content)
    def get_global_wave_animation(self):
        # Create a wave-like animation that will persist throughout the video
        wave_group = VGroup()
        num_waves = 3  # Reduced number of waves
        wave_spacing = 0.3  # Reduced spacing
        
        for i in range(num_waves):
            wave = VMobject()
            wave.set_points_smoothly([
                [-3 + j*0.2, math.sin(j*0.5 + i*wave_spacing)*0.2, 0]  # Reduced amplitude (0.3 -> 0.2)
                for j in range(31)
            ])
            wave.set_color(color_gradient([Config.PRIMARY_COLOR, Config.SECONDARY_COLOR], 2))
            wave_group.add(wave)
        
        wave_group.arrange(DOWN, buff=0.1)  # Reduced buffer between waves
        wave_group.scale(0.8)  # Scale down the entire wave group
        wave_group.move_to(DOWN * 3.5)  # Move waves further down
        return wave_group


    def create_text_section(self, text, font_size=36):
    # Split text into sentences and wrap long sentences
        def wrap_text(text, max_chars=35):
            words = text.split()
            lines = []
            current_line = []
            current_length = 0
            
            for word in words:
                if current_length + len(word) + 1 <= max_chars:
                    current_line.append(word)
                    current_length += len(word) + 1
                else:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                    current_length = len(word)
            
            if current_line:
                lines.append(' '.join(current_line))
            return '\n'.join(lines)
        
        # Process each sentence
        sentences = text.split('. ')
        wrapped_sentences = [wrap_text(sentence) for sentence in sentences]
        
        # Create text objects with proper formatting
        formatted_text = VGroup(*[
            Text(
                sentence + ('.' if not sentence.endswith('.') else ''),
                font_size=font_size,
                line_spacing=1.5,  # Increased line spacing
                color=WHITE
            ).scale(0.8)
            for sentence in wrapped_sentences
        ]).arrange(DOWN, buff=0.5)  # Increased buffer between sentences
        
        # Add outline for better readability
        for text_obj in formatted_text:
            text_obj.set_stroke(color=Config.BACKGROUND_COLOR, width=0.5, opacity=0.5)
        
        # Position text higher on screen with more space
        formatted_text.move_to(UP * 0.8)
        
        return formatted_text

    def create_visual(self, section):
        if section == 'hook':
            # Create pulsing circle with radiating lines
            circle = Circle(radius=1.5).set_color(Config.PRIMARY_COLOR)
            lines = VGroup(*[
                Line(ORIGIN, RIGHT * 2).rotate(angle=i * PI/4)
                for i in range(8)
            ]).set_color(Config.SECONDARY_COLOR)
            return VGroup(circle, lines).move_to(DOWN * 2)
            
        elif section == 'problem':
            # Create connected nodes
            nodes = VGroup(*[
                Circle(radius=0.3).set_color(Config.ACCENT_COLOR)
                for _ in range(3)
            ]).arrange(RIGHT, buff=1)
            lines = VGroup(*[
                Line(nodes[i].get_center(), nodes[i+1].get_center())
                for i in range(len(nodes)-1)
            ]).set_color(Config.ACCENT_COLOR)
            return VGroup(nodes, lines).move_to(DOWN * 2)
            
        elif section == 'solution':
            # Create path through obstacles
            path = CurvedArrow(LEFT * 2, RIGHT * 2).set_color(Config.PRIMARY_COLOR)
            obstacles = VGroup(*[
                Square(side_length=0.5).set_color(Config.SECONDARY_COLOR)
                for _ in range(3)
            ]).arrange(RIGHT, buff=1).move_to(path.get_center())
            return VGroup(path, obstacles).move_to(DOWN * 2)
            
        elif section == 'impact':
            # Create rising bars
            bars = VGroup(*[
                Rectangle(height=h, width=0.4)
                for h in [0.5, 1, 1.5, 2, 2.5]
            ]).arrange(RIGHT, buff=0.2)
            bars.set_color_by_gradient(Config.PRIMARY_COLOR, Config.SECONDARY_COLOR)
            return bars.move_to(DOWN * 2)
            
        else:  # future
            # Create expanding star
            star = RegularPolygram(5, radius=1)
            star.set_color(Config.SECONDARY_COLOR)
            return star.move_to(DOWN * 2)

    def animate_visual(self, visual, section):
        if section == 'hook':
            self.play(Create(visual), run_time=1)
            self.play(
                visual[0].animate.scale(1.2),
                visual[1].animate.scale(1.1),
                run_time=1
            )
        elif section == 'problem':
            self.play(Create(visual[1]), run_time=1)  # Create lines first
            self.play(Create(visual[0]), run_time=1)  # Then nodes
        elif section == 'solution':
            self.play(Create(visual[0]), run_time=1)  # Create path
            self.play(Create(visual[1]), run_time=1)  # Create obstacles
        elif section == 'impact':
            self.play(*[GrowFromEdge(bar, DOWN) for bar in visual], run_time=2)
        else:  # future
            self.play(Create(visual), run_time=1)
            self.play(visual.animate.scale(1.5), run_time=1)
    def create_transition_effect(self):
        dots = VGroup(*[Dot() for _ in range(3)])
        dots.arrange(RIGHT, buff=0.3)
        dots.set_color(Config.SECONDARY_COLOR)
        return dots

    def animate_transition(self):
        dots = self.create_transition_effect()
        self.play(
            FadeIn(dots, shift=UP),
            run_time=0.5
        )
        self.play(
            *[dot.animate.scale(1.5).set_color(Config.PRIMARY_COLOR) for dot in dots],
            run_time=0.5
        )
        self.play(FadeOut(dots), run_time=0.5)


    def construct(self):
        self.set_speech_service(GTTSService(lang="en"))
        
        # Create the global wave animation
        wave_animation = self.get_global_wave_animation()
        self.play(Create(wave_animation))
        
        # Title Scene
        title = Text("Research Highlights", font_size=60, color=Config.PRIMARY_COLOR)
        subtitle = Text("An In-depth Analysis", font_size=36, color=Config.SECONDARY_COLOR)
        subtitle.next_to(title, DOWN)
        title_group = VGroup(title, subtitle)
        
        self.play(Write(title_group))
        self.wait(1)
        self.play(FadeOut(title_group))
        
        # Hook Scene with context
        if self.content['hook']:
            hook_obj = self.create_text_section(self.content['hook'], font_size=48)
            context = Text("Key Innovation", font_size=32, color=Config.ACCENT_COLOR)
            context.to_edge(UP)
            
            with self.voiceover(self.voiceover_content['hook']) as tracker:
                self.play(Write(context))
                self.play(Write(hook_obj))
                self.wait(tracker.duration - 3)
                self.play(FadeOut(VGroup(hook_obj, context)))
            
            self.animate_transition()

        # Problem Scene with emphasis
        if self.content['problem']:
            problem_obj = self.create_text_section(self.content['problem'])
            emphasis = Text("Challenge", font_size=32, color=Config.ACCENT_COLOR)
            emphasis.to_edge(UP)
            
            with self.voiceover(self.voiceover_content['problem']) as tracker:
                self.play(Write(emphasis))
                self.play(FadeIn(problem_obj))
                self.wait(tracker.duration - 3)
                self.play(FadeOut(VGroup(problem_obj, emphasis)))
                
            self.animate_transition()

        # Solution Scene with highlight
        if self.content['solution']:
            solution_obj = self.create_text_section(self.content['solution'])
            highlight = Text("Our Approach", font_size=32, color=Config.ACCENT_COLOR)
            highlight.to_edge(UP)
            
            with self.voiceover(self.voiceover_content['solution']) as tracker:
                self.play(Write(highlight))
                self.play(FadeIn(solution_obj))
                self.wait(tracker.duration - 3)
                self.play(FadeOut(VGroup(solution_obj, highlight)))
                
            self.animate_transition()

        # Impact Scene with metrics
        if self.content['impact']:
            impact_obj = self.create_text_section(self.content['impact'])
            metrics = Text("Results & Impact", font_size=32, color=Config.ACCENT_COLOR)
            metrics.to_edge(UP)
            
            with self.voiceover(self.voiceover_content['impact']) as tracker:
                self.play(Write(metrics))
                self.play(FadeIn(impact_obj))
                self.wait(tracker.duration - 3)
                self.play(FadeOut(VGroup(impact_obj, metrics)))
                
            self.animate_transition()

        # Future Scene with vision
        if self.content['future']:
            future_obj = self.create_text_section(self.content['future'])
            vision = Text("Future Directions", font_size=32, color=Config.ACCENT_COLOR)
            vision.to_edge(UP)
            
            with self.voiceover(self.voiceover_content['future']) as tracker:
                self.play(Write(vision))
                self.play(FadeIn(future_obj))
                self.wait(tracker.duration - 3)
                self.play(FadeOut(VGroup(future_obj, vision)))

        # Closing Scene
        closing = Text("Thank you for watching", font_size=48, color=Config.PRIMARY_COLOR)
        self.play(Write(closing))
        self.wait(1)
        self.play(FadeOut(closing))
        
        # Fade out the wave animation
        self.play(FadeOut(wave_animation))

def main():
    try:
        print("Starting video creation process...")
        print(f"Base directory: {Config.BASE_DIR}")
        print(f"PDF file path: {Config.PDF_FILE}")
        
        # Create directories
        print("Setting up directories...")
        Config.setup_directories()
        
        # Check PDF file
        if not Config.PDF_FILE.exists():
            print(f"PDF file not found at: {Config.PDF_FILE}")
            raise FileNotFoundError(f"PDF file not found at {Config.PDF_FILE}")
        else:
            print("PDF file found successfully")
        
        print("Processing paper content...")
        content = process_paper_content(Config.PDF_FILE)
        
        if not content:
            print("No content generated from PDF")
            return
            
        print(f"Content generated successfully: {list(content.keys())}")
        
        print("Creating animation...")
        scene = ReelContent()
        scene.set_content(content)
        
        print("Rendering scene...")
        scene.render()
        
        print("Checking for output file...")
        output_file = Path(scene.renderer.file_writer.movie_file_path)
        print(f"Expected output file: {output_file}")
        
        if output_file.exists():
            print(f"Animation created: {output_file}")
            
            print("Processing final video...")
            video = VideoFileClip(str(output_file))
            if video.duration > 60:
                video = video.subclip(0, 60)
            
            print(f"Saving to: {Config.FINAL_VIDEO_FILE}")
            os.makedirs(os.path.dirname(Config.FINAL_VIDEO_FILE), exist_ok=True)
            
            video.write_videofile(
                str(Config.FINAL_VIDEO_FILE),
                codec='libx264',
                audio_codec='aac',
                fps=30
            )
            video.close()
            print("Final video processing completed!")
        else:
            print("Error: Animation file not found")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()
        
def generate_reel(pdf_path: Path) -> Path:
    """
    Main function to generate a video reel from a PDF file.
    Returns the path to the generated video file.
    """
    try:
        # Set up configuration
        Config.PDF_FILE = pdf_path
        Config.setup_directories()
        
        # Process content
        content = process_paper_content(Config.PDF_FILE)
        
        # Create and render scene
        scene = ReelContent()
        scene.set_content(content)
        scene.render()
        
        return Config.FINAL_VIDEO_FILE
        
    except Exception as e:
        print(f"Error generating reel: {str(e)}")
        raise

# if __name__ == "__main__":
#     try:
#         print("Script starting...")
#         main()
#         print("Script completed.")
#     except Exception as e:
#         print(f"Fatal error: {str(e)}")
#         traceback.print_exc()

if __name__ == "__main__":
    # For testing purposes
    test_pdf = Path("path/to/your/test.pdf")
    output_path = generate_reel(test_pdf)
    print(f"Video generated at: {output_path}")