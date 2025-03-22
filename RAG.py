from fastapi import FastAPI
from pydantic import BaseModel
import os
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_ollama import OllamaLLM
from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain

app = FastAPI()

# Store processed documents globally
global_documents = None

### 1️⃣ PDF PROCESSING ###
class FilePathRequest(BaseModel):
    file: str

@app.post("/process")
def process_pdf(request: FilePathRequest):
    """Loads a PDF from the given file path and processes its content."""
    global global_documents  # Allow modification of the global variable

    file_path = request.file
    print("Processing file:", file_path)

    # Check if file exists
    if not os.path.exists(file_path) or not file_path.endswith(".pdf"):
        return {"error": "Invalid file path or file does not exist."}

    # Load PDF
    loader = PyPDFLoader(file_path)
    text_documents = loader.load()
    print("Extracted text:", text_documents)

    # Split text
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    global_documents = text_splitter.split_documents(text_documents)  # Store globally

    return {"message": "File processed successfully."}

### 2️⃣ CHAT ENDPOINT ###
class QueryInput(BaseModel):
    query: str  

@app.post('/chat')
def chat(request: QueryInput):
    """Handles chat queries based on the processed PDF content."""
    global global_documents  # Access stored PDF content
    if global_documents is None:
        return {"error": "No PDF has been processed yet."}

    query = request.query
    print("Received query:", query)

    # Create embeddings and vector store
    db = Chroma.from_documents(global_documents, OllamaEmbeddings(model="llama3.1:8b"))
    retriever = db.as_retriever(k=1)

    # Define LLM and Prompt
    llm = OllamaLLM(model="llama3.1:8b")
    prompt = ChatPromptTemplate.from_template("""
        "You are an AI assistant designed to answer questions based on a provided document which will act as the context of the conversation.Use only the content from the uploaded document to generate your response. 
        If the document does not contain relevant information, state that explicitly instead of making up an answer. Keep your response clear, concise, and relevant to the query.
         Maintain the original context and meaning from the document while summarizing key points if needed.
        <context>
        {context}
        </context>
        Question: {input}
    """)

    # Create retrieval chain
    document_chain = create_stuff_documents_chain(llm, prompt)
    retrieval_chain = create_retrieval_chain(retriever, document_chain)

    # Process query
    response = retrieval_chain.invoke({"input": query})
    return {"answer": response["answer"]}

@app.post('/generic_chat')
def generic_chat(request: QueryInput):
        query = request.query
        print(query)
        llm = OllamaLLM(model="llama3.1:8b")

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system","You are a helpful and engaging AI assistant. Respond to user queries in a natural, informative, and conversational manner. Adapt your tone based on the context—be professional for formal queries and friendly for casual conversations. Keep your responses clear, concise, and relevant. If a question requires reasoning, provide a step-by-step explanation. If uncertain, state so rather than providing incorrect information."),
                ("user","Question{query}")
            ]
        )
        chain = prompt|llm
        response =chain.invoke({"query":query})
        print(response)
        return {"answer": response}
