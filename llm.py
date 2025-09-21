# llm.py
import json
import google.generativeai as genai
import os
from questions import DEFAULT_QUESTIONS
import re

# Configure with your API key (use os.getenv('GOOGLE_API_KEY') in production)
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

def generate_persona(answers, text_path=None):
    # Build prompt from answers
    prompt_lines = ["Create a persona summary for a dating bot based on this profile:"]
    for q_id, answer in answers.items():
        if answer:
            q_text = next((q['text'] for q in DEFAULT_QUESTIONS if q['id'] == q_id), q_id)
            prompt_lines.append(f"- {q_text}: {answer}")
    
    # Sample text file messages for style analysis
    text_samples = ""
    if text_path:
        try:
            with open(text_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:20]  # Limit to 20 lines for token efficiency
                text_samples = "\nTexting style samples:\n" + "".join(lines)
        except Exception as e:
            text_samples = f"Error reading text file: {str(e)}"
    
    prompt = "\n".join(prompt_lines) + text_samples + "\nSummarize into a detailed persona description, capturing interests, tone, texting style (e.g., emojis, slang, sentence length), and personality for realistic bot conversations.'"
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    return response.text

def generate_conversation(user_answers, user_persona, other_answers, other_persona, user_name, other_name):
    prompt = (
        f"Generate a realistic dating conversation between two bots.\n"
        f"User bot (named {user_name}) persona: {user_persona}\n"
        f"Other bot (named {other_name}) persona: {other_persona}\n"
        f"User profile: {json.dumps(user_answers)}\n"
        f"Other profile: {json.dumps(other_answers)}\n"
        "Simulate a realistic back-and-forth chat with exactly 20 lines of dialogue (10 messages from each bot, alternating), where each bot responds in their respective style, reflecting their interests and personality. Generally follow the following guidelines: 1) Start with something similar to the pickup lines they gave, 2) Don't have the bots assume any information about the other bot, have them learn about each other, 3) If they don't connect, make that apparent in the conversation. 4) Don't be repetitive. Format as:\n{user_name}: Message\n{other_name}: Message\n{user_name}: Message\n..."
    )
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    return response.text

def calculate_compatibility(user_answers, other_answers, conversation=None):
    prompt = f"Compare user answers: {json.dumps(user_answers)} with other answers: {json.dumps(other_answers)}"
    if conversation:
        prompt += f"\nConversation between the users:\n{conversation}\nEvaluate romantic compatibility based on both answers and conversation dynamics on a scale of 1-100."
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    
    # Extract numerical score (e.g., '15/100' or '15') from response
    match = re.search(r'\b(\d+)(?:/100)?\b', response.text)
    if match:
        score = float(match.group(1))
    else:
        score = 0.0  # Fallback if no score is found
    
    return score

'''def calculate_compatibility(user_answers, other_answers):
    prompt = f"Calculate a realistic compatibility score (0-100) between: {json.dumps(user_answers)} and {json.dumps(other_answers)}. Respond with just the number and make it truly any number in the range 0 to 100."
    print("User Answers: \n", json.dumps(user_answers))
    print("Other Answers: \n", json.dumps(other_answers))

    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    try:
        return int(response.text.strip())
    except ValueError:
        return 50'''