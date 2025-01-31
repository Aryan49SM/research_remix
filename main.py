from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os
from datetime import datetime
import logging
from paper_to_podcast import process_paper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('podcast_generator.log'),
        logging.StreamHandler()
    ]
)

# Initialize FastAPI app
app = FastAPI(
    title="Research Paper to Podcast API",
    description="API for converting research papers to podcasts",
    version="1.0.0"
)

# Mount the podcast directory to serve files
app.mount("/podcast", StaticFiles(directory="podcast"), name="podcast")

# Update the PodcastResponse model
class PodcastResponse(BaseModel):
    podcast_file: str
    segments_dir: str
    message: str
    duration: float

# Update the root endpoint HTML to include download links
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head>
            <title>Research Paper to Podcast Converter</title>
            <style>
                /* ... (previous styles remain the same) ... */
                .file-list {
                    margin-top: 20px;
                    padding: 10px;
                    background-color: #fff;
                    border-radius: 4px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Welcome to Research Paper to Podcast Converter</h1>
                
                <div class="upload-form">
                    <h2>Upload PDF</h2>
                    <form action="/generate-podcast/" method="post" enctype="multipart/form-data">
                        <p>Select a PDF file to convert:</p>
                        <input type="file" name="file" accept=".pdf" required>
                        <br><br>
                        <button type="submit" class="submit-btn">Generate Podcast</button>
                    </form>
                </div>

                <h2>API Documentation</h2>
                <ul>
                    <li><a href="/docs">Interactive API documentation</a></li>
                </ul>
            </div>
        </body>
    </html>
    """

@app.post("/generate-podcast/", response_model=PodcastResponse)
async def create_podcast(file: UploadFile = File(...)):
    try:
        start_time = datetime.now()
        
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are accepted")

        os.makedirs("temp", exist_ok=True)
        
        file_path = f"temp/{file.filename}"
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Process the paper and generate podcast
        output_file = process_paper(file_path)
        
        # Get the segments directory (it will be the same timestamp as the final podcast)
        timestamp = os.path.basename(output_file).replace("podcast_", "").replace(".mp3", "")
        segments_dir = f"podcast/segments/podcast_{timestamp}"
        
        duration = (datetime.now() - start_time).total_seconds()

        return PodcastResponse(
            podcast_file=output_file,
            segments_dir=segments_dir,
            message="Podcast generated successfully",
            duration=duration
        )

    except Exception as e:
        logging.error(f"Error in podcast generation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
# Add endpoint to get the final podcast file
@app.get("/download-podcast/{filename}")
async def download_podcast(filename: str):
    file_path = os.path.join("podcast/final", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/mpeg", filename=filename)
    raise HTTPException(status_code=404, detail="Podcast file not found")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
