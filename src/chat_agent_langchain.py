from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent, AgentExecutor
from tools import recommend_tool
from schemas import HotelResponse
import json
import os, dotenv; dotenv.load_dotenv()

parser = PydanticOutputParser(pydantic_object=HotelResponse)

SYSTEM_PROMPT = """
You are a **HotelBot**, a friendly hotel-booking assistant, a concise concierge.

Goals
-----
1. Understand the guest’s stay wishes if they have them: budget, room type, beds, and amenities
(free Wi-Fi, kitchen, mini-bar, access to pool if important).
2. When you have enough detail, call the `recommend_room` tool to fetch matching rooms.
3. Return the final answer strictly in the JSON schema below—no extra keys, no comments.

Guidelines
----------
• Ask follow-up questions to clarify the guest's needs, and if they don't have specific criteria, suggest top options based on the info provided.
• If `recommend_room` returns an empty list, apologise and suggest the guest rephrase or broaden criteria.
• Keep `reply` under 50 words.  
• Never hallucinate room IDs—only use what the tool gives. 
• Do not invent amenities that are not provided.

Schema
------
{format_instructions}
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{query}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
]).partial(format_instructions=parser.get_format_instructions())

llm = ChatOpenAI(
    model="gpt-4o-mini",
    openai_api_key=os.getenv("AI_API_KEY"),
    max_tokens=800
)

tools  = [recommend_tool]
agent = create_tool_calling_agent(llm, tools, prompt)
runner = AgentExecutor(agent=agent, tools=tools, verbose=False)

print("🤖   Hotel Assistant ready.  (type 'quit' to exit)\n")

while True:
    q = input("Guest: ").strip()
    if q.lower() in {"quit", "exit", "bye"}:
        print("HotelBot: Safe travels—hope to host you soon!")
        break

    response_json = runner.invoke({"query": q})["output"]

    raw = runner.invoke({"query": q})["output"]

    # Pretty-print
    try:
        res = json.loads(raw)
    except json.JSONDecodeError:          # fallback if the model ever slips
        print(raw)
        continue

    print(f"HotelBot: {res['reply']}")

    if res["recommendations"]:
        print("Our top picks:")
        for r in res["recommendations"]:
            print(f"  • {r['room_type']} – ${r['price_per_day']}/night")
            print(f"    {r['beds']} beds")
            details = []
            if r.get("area"):           details.append(f"{r['area']} m²")
            if r.get("free_wifi"):      details.append("free Wi-Fi")
            if r.get("kitchen"):        details.append("kitchen")
            if r.get("mini_bar"):       details.append("mini-bar")
            if r.get("access_to_pool"): details.append("pool access")
            if details:
                print("    " + ", ".join(details))
            print(f"    {r['short_description']}")
        print()