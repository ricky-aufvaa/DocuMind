import chainlit as cl


from dotenv import load_dotenv 
#loading the enviroment variables
load_dotenv()

import chainlit as cl
from chainlit.input_widget import Select


# @cl.set_chat_profiles
# async def chat_profiles():
#     return [
#         cl.ChatProfile(
#             name = "Chat with PDFs",
#             markdown_description = "You can upload any pdf here and interact with it."
#         ),
#         cl.ChatProfile(
#             name = "Generic Chat",
#             markdown_description = "You can talk to the llm and ask general queries."
#         )
#     ]
# @cl.on_chat_start
# async def on_chat_start():
#     chat_profile = cl.user_session.get("chat_profile")
#     if chat_profile == "Chat with PDFs":
#         await cl.Message(content=f"Upload your PDF").send()
#     else:
#         await cl.Message(f"Be ready to ask anything").send()

# @cl.on_message
# async def hello():
#     await cl.Message(content="hello").send()

from typing import Optional
import httpx

import chainlit as cl
API_URL = "http://0.0.0.0:8001"

@cl.set_chat_profiles
async def chat_profile(current_user: cl.User):
    if current_user.metadata["role"] != "ADMIN":
        return None
    return [
    cl.ChatProfile(
        name = "Chat with PDFs",
        markdown_description = "You can upload any pdf here and interact with it."
    ),
    cl.ChatProfile(
        name = "Generic Chat",
        markdown_description = "You can talk to the llm and ask general queries."
    )
    ]


@cl.password_auth_callback
def auth_callback(username: str, password: str) -> Optional[cl.User]:
    if (password) ==  ("admin"):
        return cl.User(identifier=username, metadata={"role": "ADMIN"})
    else:
        return None


@cl.action_callback("action_button")
async def on_action(action):
    pdf_file_path = action.payload.get("value")
    pdf_file_path = pdf_file_path[0]
    response =httpx.post(f"{API_URL}/process",json={"file":pdf_file_path}) 
    print(response)
    if response.status_code==200:
        data = response.json()
        answer = data.get("message")
        print(answer)
        await cl.Message(content=f"You can start chatting with your PDF").send()
    # await cl.Message(content=f"Executed {action.name}").send()
    # Optionally remove the action button from the chatbot user interface
    await action.remove()
import glob 
import pathlib
@cl.on_chat_start
async def on_chat_start():
    file = None
    user = cl.user_session.get("user")
    chat_profile = cl.user_session.get("chat_profile")
    await cl.Message(
        content=f"Welcome! {user.identifier}, You can start using the {chat_profile} chat profile"
    ).send()
    if chat_profile =="Chat with PDFs":
        print(chat_profile)
        while file ==None:
            file = await cl.AskFileMessage(content= "Upload you PDF",max_files=1,accept=["application/pdf"]).send()

        pdf_file = file[0]
        directory= pathlib.Path(".files")
        pdf_file_path =[str(file) for file in directory.rglob("*.pdf")]
        print(pdf_file_path)
        # pdf_file_path = ".files/"
        await cl.Message(content= f"{pdf_file.name} uploaded").send()
        actions = [
            cl.Action(name = "action_button",payload ={"value":pdf_file_path},label = "Process the PDF")
        ]
        await cl.Message(content="",actions=actions).send()
        @cl.on_message
        async def on_message(message:cl.Message):
            response = httpx.post(f'{API_URL}/chat',timeout=None,json={"query":message.content})
            data = response.json()
            answer = data.get("answer")
            await cl.Message(answer).send()
    if chat_profile =="Generic Chat":
        print(chat_profile)
        @cl.on_message
        async def on_generic_message(message:cl.Message):
            response = httpx.post(f'{API_URL}/generic_chat',timeout=None,json={"query":message.content})
            data = response.json()
            answer = data.get("answer")
            await cl.Message(answer).send()


