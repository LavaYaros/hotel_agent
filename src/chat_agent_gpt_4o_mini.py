"""
Minimal console-based hotel assistant.
"""

import json, openai, os, sys
from agent_core_gpt_4o_mini import find_rooms

from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("AI_API_KEY")

# declare the tool the model can call
tools = [{
    "type": "function",
    "function": {
        "name": "find_rooms",
        "description": "Search hotel rooms that match guest preferences.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_text":  {"type": "string",
                               "description": "Raw preference text from the guest."},
                "beds":       {"type": "integer", "minimum": 1},
                "pool_required": {"type": "boolean"},
                "kitchen_required": {"type": "boolean"},
                "wifi_required": {"type": "boolean"},
                "min_price":  {"type": "number"},
                "max_price":  {"type": "number"},
            },
            "required": ["user_text"]
        }
    }
}]

messages = [
    {"role": "system",
     "content": (
       "You are a friendly hotel-booking assistant. "
       "Chat, collect preferences, and call find_rooms when ready. "
       "Then present the shortlisted rooms in a helpful tone."
       "Do not invent amenities that are not provided."
     )}
]

print("🤖   Hotel Assistant ready.  (type 'quit' to exit)\n")

while True:
    try:
        user = input("Guest: ").strip()
    except (EOFError, KeyboardInterrupt):
        sys.exit()

    if user.lower() in {"quit", "exit", "bye"}:
        print("HotelBot: Safe travels—hope to host you soon!")
        break

    messages.append({"role": "user", "content": user})

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )

    msg = response.choices[0].message

    # if the model decided to call our function…
    if msg.tool_calls:
        call = msg.tool_calls[0]
        args = json.loads(call.function.arguments)

        tool_result = find_rooms(**args)

        # keep the assistant message that contains tool_calls
        messages.append(msg)

        # send back the tool’s JSON output
        messages.append({
            "role": "tool",
            "tool_call_id": call.id,
            "name": "find_rooms",
            "content": json.dumps(tool_result, default=str)
        })

        # now ask GPT to craft a user-facing reply
        follow_up = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages           # tools=tools optional here
        ).choices[0].message

        print("\nAgent:", follow_up.content, "\n")
        messages.append(follow_up)
    else:
        # ordinary assistant reply
        print("\nAgent:", msg.content, "\n")
        messages.append(msg)
