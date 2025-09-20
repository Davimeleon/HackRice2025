# llm.py
import json
import google.generativeai as genai
import os
from questions import DEFAULT_QUESTIONS

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

def generate_conversation(user_answers, user_persona, other_answers, other_persona):
    prompt = (
        f"Generate a realistic dating conversation between two bots.\n"
        f"User bot persona: {user_persona}\n"
        f"Other bot persona: {other_persona}\n"
        f"User profile: {json.dumps(user_answers)}\n"
        f"Other profile: {json.dumps(other_answers)}\n"
        "Simulate a back-and-forth chat with exactly 20 lines of dialogue (10 messages from each bot, alternating), where each bot responds in their respective style, reflecting their interests and personality. Format as:\nYou: Message\nOther: Message\nYou: Message\n..."
    )
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    return response.text

def calculate_compatibility(user_answers, other_answers):
    prompt = f"Calculate compatibility score (0-100) between: {json.dumps(user_answers)} and {json.dumps(other_answers)}. Respond with just the number."
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    try:
        return int(response.text.strip())
    except ValueError:
        return 50