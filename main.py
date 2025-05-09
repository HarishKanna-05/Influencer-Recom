from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent, Browser, BrowserConfig
from pydantic import SecretStr
import os
from dotenv import load_dotenv
load_dotenv()

import asyncio

api_key = os.getenv("GEMINI_API_KEY")

browser = Browser(
    config=BrowserConfig(
        chrome_instance_path='C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', 
    )
)
initial_actions = [
	{'open_tab': {'url': 'https://www.google.com'}},
	{'scroll_down': {'amount': 1000}},
]
llm = ChatGoogleGenerativeAI(model='gemini-2.5-pro-exp-03-25',api_key=SecretStr(os.getenv('GEMINI_API_KEY')))
planner_llm = ChatGoogleGenerativeAI(model='gemini-2.5-pro-exp-03-25',api_key=SecretStr(os.getenv('GEMINI_API_KEY')))

async def main():
    agent = Agent(
        task="analyse this website https://www.rajalakshmi.org and give me what kind of product the are selling theme of the company and the target audience ",
        initial_actions=initial_actions, 
        llm=llm,
        planner_llm=planner_llm,           # Separate model for planning
        use_vision_for_planner=False,      # Disable vision for planner
        planner_interval=4,                 # Plan every 4 steps
        browser=browser,
        save_conversation_path="logs/conversation"
    )
    result = await agent.run()
    print(result)
    await browser.close()
    history = await agent.run()
    history.extracted_content()

asyncio.run(main())
