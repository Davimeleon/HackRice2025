import os

from groq import Groq

client = Groq(
    api_key=os.environ.get("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"),
)

prompt = input("Ask away\n")

chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": prompt,
        }
    ],
    model="openai/gpt-oss-120b",
)

print(chat_completion.choices[0].message.content)