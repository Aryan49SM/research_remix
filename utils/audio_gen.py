import datetime
import os
import glob
import re
from gtts import gTTS
from pydub import AudioSegment
import logging
import uvicorn

def create_directories():
    """Create necessary directories if they don't exist"""
    # Create main podcast directory
    os.makedirs("podcast", exist_ok=True)
    # Create directory for final podcasts
    os.makedirs("podcast/final", exist_ok=True)
    # Create directory for temporary audio segments
    os.makedirs("podcast/segments", exist_ok=True)

def generate_host(text: str, segment_dir: str):
    logging.info("Generating host audio...")
    try:
        now = int(datetime.datetime.now().timestamp())
        output_path = os.path.join(segment_dir, f"host_{now}.mp3")
        tts = gTTS(text=text, lang='en', tld='ca')
        tts.save(output_path)
        logging.info(f"Audio saved to {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"Error in generate_host: {str(e)}")
        raise

def generate_expert(text: str, segment_dir: str):
    logging.info("Generating expert audio...")
    try:
        now = int(datetime.datetime.now().timestamp())
        output_path = os.path.join(segment_dir, f"expert_{now}.mp3")
        tts = gTTS(text=text, lang='en', tld='ie')
        tts.save(output_path)
        logging.info(f"Audio saved to {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"Error in generate_expert: {str(e)}")
        raise

def generate_learner(text: str, segment_dir: str):
    logging.info("Generating learner audio...")
    try:
        now = int(datetime.datetime.now().timestamp())
        output_path = os.path.join(segment_dir, f"learner_{now}.mp3")
        tts = gTTS(text=text, lang='en', tld='co.in')
        tts.save(output_path)
        logging.info(f"Audio saved to {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"Error in generate_learner: {str(e)}")
        raise

def merge_mp3_files(segment_dir: str, output_file: str):
    logging.info(f"Starting to merge MP3 files from {segment_dir}")
    try:
        mp3_files = [os.path.basename(x) for x in glob.glob(os.path.join(segment_dir, "*.mp3"))]
        logging.info(f"Found {len(mp3_files)} MP3 files")

        sorted_files = sorted(
            mp3_files,
            key=lambda x: re.search(r"(\d{10})", x).group(0)
        )
        logging.info("Files sorted by timestamp")

        merged_audio = AudioSegment.empty()

        for file in sorted_files:
            logging.info(f"Processing file: {file}")
            file_path = os.path.join(segment_dir, file)
            audio = AudioSegment.from_mp3(file_path)
            merged_audio += audio

        merged_audio.export(output_file, format="mp3")
        logging.info(f"Successfully merged file saved as {output_file}")
    except Exception as e:
        logging.error(f"Error in merge_mp3_files: {str(e)}")
        raise

def generate_podcast(script):
    logging.info("Starting podcast generation")
    try:
        # Create necessary directories
        create_directories()
        
        # Create timestamp for this podcast
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Create unique directory for this podcast's segments
        segment_dir = os.path.join("podcast/segments", f"podcast_{timestamp}")
        os.makedirs(segment_dir, exist_ok=True)
        
        logging.info(f"Created directory: {segment_dir}")

        lines = re.findall(
            r"(Host|Learner|Expert):\s*(.*?)(?=(Host|Learner|Expert|$))", script, re.DOTALL
        )
        logging.info(f"Found {len(lines)} dialogue lines")

        for speaker, text, _ in lines:
            text = text.strip()
            logging.info(f"Processing {speaker}'s dialogue")

            if speaker == "Host":
                generate_host(text, segment_dir)
            elif speaker == "Learner":
                generate_learner(text, segment_dir)
            elif speaker == "Expert":
                generate_expert(text, segment_dir)

        # Generate final podcast filename
        final_podcast_path = os.path.join("podcast/final", f"podcast_{timestamp}.mp3")
        
        # Merge all segments into final podcast
        merge_mp3_files(segment_dir, final_podcast_path)
        logging.info("Podcast generation completed successfully")
        
        return final_podcast_path
    except Exception as e:
        logging.error(f"Error in generate_podcast: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        logging.info("Starting podcast generation script")
        script = """
        Host: Welcome to our podcast!
        Expert: Today we'll be discussing AI.
        Learner: I'm excited to learn more!
        """
        
        # Running async function within the main script
        generate_podcast(script)
        
        logging.info("Script completed successfully")
    except Exception as e:
        logging.error(f"Main script error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )