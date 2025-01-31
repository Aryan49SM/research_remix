import os
from langchain_core.messages import AIMessage
from langchain_community.document_loaders import TextLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from operator import itemgetter
from PyPDF2 import PdfReader
from template import discuss_prompt_template
from datetime import datetime
import re
import logging
import google.generativeai as genai

async def process_script_async(pdf_path: str, chains: dict, llm) -> str:
    """
    Asynchronous version of generate_script for FastAPI
    """
    try:
        return generate_script(pdf_path, chains, llm)
    except Exception as e:
        logging.error(f"Error in async script processing: {str(e)}")
        raise

def initialize_gemini_embeddings():
    """Initialize Gemini model for embeddings"""
    try:
        GOOGLE_API_KEY = os.getenv('GEMINI_API_KEY')
        if not GOOGLE_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        genai.configure(api_key=GOOGLE_API_KEY)
        # Initialize Gemini model
        model = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=GOOGLE_API_KEY,
            temperature=0.7
        )
        logging.info("Gemini model initialized successfully")
        return model
    except Exception as e:
        logging.error(f"Error initializing Gemini model: {str(e)}")
        raise

def initialize_discussion_chain(txt_file, llm):
    # Load and chunk documents
    loader = TextLoader(txt_file, encoding='UTF-8')
    docs = loader.load()
    logging.info("Document loaded successfully")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    logging.info(f"Document split into {len(splits)} chunks")

    # Initialize embeddings and vector store
    GOOGLE_API_KEY = os.getenv('GEMINI_API_KEY')
    embeddings_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GOOGLE_API_KEY)
    vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings_model)
    logging.info("Vector store created successfully")

    retriever = vectorstore.as_retriever()

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    discuss_rag_chain = (
        {
            "additional_context": itemgetter("section_plan") | retriever | format_docs,
            "section_plan": itemgetter("section_plan"),
            "previous_dialogue": itemgetter("previous_dialogue"),
        }
        | discuss_prompt_template
        | llm
        | StrOutputParser()
    )
    return discuss_rag_chain

def create_folder_and_save_txt(output_path: str, text: str) -> str:
    """Create a folder named 'text_papers' and save txt file into it."""
    folder_name = "text_papers"

    # Create folder if it doesn't already exist
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    # Construct the full file path
    file_path = os.path.join(folder_name, output_path)

    # Save the text to the file
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(text)

    return file_path

def parse_pdf(pdf_path: str, output_path: str) -> str:
    pdf_reader = PdfReader(pdf_path)

    # Extract text from the PDF
    extracted_text = []
    collecting = True

    for page in pdf_reader.pages:
        text = page.extract_text()
        if text and collecting:
            extracted_text.append(text)

            # Check for the end condition, the section after "Conclusion"
            if "Conclusion" in text:
                conclusion_start = text.index("Conclusion")
                extracted_text.append(text[conclusion_start:])
                collecting = False  # Stop collecting after the section following Conclusion

    # Join all collected text
    final_text_to_section_after_conclusion = "\n".join(extracted_text)

    # Save to .txt file in the 'text_papers' folder
    saved_file_path = create_folder_and_save_txt(output_path, final_text_to_section_after_conclusion)

    return saved_file_path

def get_head(pdf_path: str) -> str:
    # Load the PDF file
    pdf_reader = PdfReader(pdf_path)

    # Extract content from the beginning of the PDF until the section "Introduction"
    extracted_text = []
    collecting = True

    for page in pdf_reader.pages:
        text = page.extract_text()
        if text and collecting:
            # Stop collecting once "Introduction" is found
            if "Introduction" in text:
                introduction_index = text.index("Introduction")
                extracted_text.append(text[:introduction_index])  # Only collect content before "Introduction"
                break
            else:
                extracted_text.append(text)

    # Join the collected text and return as a single string
    return "\n".join(extracted_text)

def generate_script(pdf_path: str, chains: dict, llm) -> str:
    start_time = datetime.now()

    # Step 1: Parse the PDF file
    txt_file = f"text_paper_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
    txt_file = parse_pdf(pdf_path, txt_file)

    with open(txt_file, "r", encoding="utf-8") as file:
        paper = file.read()

    # Step 2: Generate the plan
    plan = chains["plan_script_chain"].invoke({"paper": paper})
    print("Plan generated")

    # Step 3: Generate the actual script for the podcast by looping over the sections of the plan
    script = ""

    # Generate the initial dialogue
    initial_dialogue = chains["initial_dialogue_chain"].invoke({"paper_head": get_head(pdf_path)})

    script += initial_dialogue
    actual_script = initial_dialogue

    # Initialize discussion chain
    discuss_rag_chain = initialize_discussion_chain(txt_file, llm)

    for section in plan:
        section_script = discuss_rag_chain.invoke({"section_plan": section, "previous_dialogue": actual_script})
        script += section_script
        actual_script = section_script

    # Enhance the script
    enhanced_script = chains["enhance_chain"].invoke({"draft_script": script})

    end_time = datetime.now()
    print(f"Time taken: {end_time - start_time}")
    print("Final script generated")

    return enhanced_script

def parse_script_plan(ai_message: AIMessage) -> list:
    # Initialize the sections list
    sections = []
    current_section = []

    # Split the text by line and skip the first line as the title
    lines = ai_message.content.strip().splitlines()
    lines = lines[1:]  # Skip the first line (title)

    # Regex patterns for any level of headers and bullet points
    header_pattern = re.compile(r"^#+\s")  # Match headers with any number of #
    bullet_pattern = re.compile(r"^- ")  # Match lines starting with a bullet point "- "

    # Parse each line, starting with the first header after the title
    for line in lines:
        if header_pattern.match(line):
            # Append the previous section (if any) to sections when a new header is found
            if current_section:
                sections.append(" ".join(current_section))
                current_section = []
            # Start a new section with the header
            current_section.append(line.strip())
        elif bullet_pattern.match(line):
            # Append bullet points to the current section
            current_section.append(line.strip())

    # Append the last section if exists
    if current_section:
        sections.append(" ".join(current_section))

    return sections
