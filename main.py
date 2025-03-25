import chainlit as cl
from dotenv import load_dotenv 
import sqlite3
import httpx
import pathlib
from typing import Optional

# Load environment variables
load_dotenv()
API_URL = "http://0.0.0.0:8001"

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Authenticate user
@cl.password_auth_callback
def auth_callback(username: str, password: str) -> Optional[cl.User]:
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
    user_data = cursor.fetchone()
    
    if user_data:
        stored_password = user_data[0]
        print(f"User {username} found in DB with stored password: {stored_password}")
        if stored_password == password:  # Password matches
            conn.close()
            print(f"User {username} logged in successfully.")
            return cl.User(identifier=username, metadata={"role": "USER"})
        else:
            conn.close()
            print("Incorrect password entered!")
            return None
    else:
        # Store new user in database
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            print(f"New user {username} registered successfully.")
            return cl.User(identifier=username, metadata={"role": "USER"})
        except sqlite3.IntegrityError:
            print("Error inserting user into database!")
            conn.close()
            return None

# Set chat profiles
@cl.set_chat_profiles
async def chat_profile(current_user: cl.User):
    return [
        cl.ChatProfile(
            name="Chat with PDFs",
            markdown_description="You can upload any PDF here and interact with it."
        ),
        cl.ChatProfile(
            name="Generic Chat",
            markdown_description="You can talk to the LLM and ask general queries."
        )
    ]

# Handle chat start
@cl.on_chat_start
async def on_chat_start():
    user = cl.user_session.get("user")
    chat_profile = cl.user_session.get("chat_profile")
    
    await cl.Message(content=f"Welcome! {user.identifier}, You can start using the {chat_profile} chat profile").send()
    
    if chat_profile == "Chat with PDFs":
        file = None
        while file is None:
            file = await cl.AskFileMessage(content="Upload your PDF", max_files=1, accept=["application/pdf"]).send()

        pdf_file = file[0]
        directory = pathlib.Path(".files")
        pdf_file_path = [str(file) for file in directory.rglob("*.pdf")]
        
        elements = [
            cl.Pdf(name="pdf1", display="inline", path=pdf_file_path[0], page=1)
        ]
        await cl.Message(content="PDF uploaded successfully", elements=elements).send()

        actions = [
            cl.Action(name="action_button", payload={"value": pdf_file_path}, label="Process the PDF", icon="mouse-pointer-click")
        ]
        await cl.Message(content="", actions=actions).send()

    if chat_profile == "Generic Chat":
        @cl.on_message
        async def on_generic_message(message: cl.Message):
            response = httpx.post(f'{API_URL}/generic_chat', timeout=None, json={"query": message.content})
            data = response.json()
            answer = data.get("answer")
            await cl.Message(answer).send()

# Handle PDF processing
@cl.action_callback("action_button")
async def on_action(action):
    pdf_file_path = action.payload.get("value")[0]
    response = httpx.post(f"{API_URL}/process", json={"file": pdf_file_path}) 
    if response.status_code == 200:
        data = response.json()
        await cl.Message(content="You can start chatting with your PDF").send()
    await action.remove()

@cl.on_message
async def on_message(message: cl.Message):
    response = httpx.post(f'{API_URL}/chat', timeout=None, json={"query": message.content})
    data = response.json()
    answer = data.get("answer")
    await cl.Message(answer).send()
