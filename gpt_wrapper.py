import os, json, re, sys, pathlib
from collections import Counter
from groq import Groq

# =========================
# 0) Config & Client Setup
# =========================
# export GROQ_API_KEY=... (set in your shell)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("Missing GROQ_API_KEY env var. `export GROQ_API_KEY=...`")

# Pick a Groq model you have access to. Examples:
#   "llama-3.1-70b-versatile"  (good general)
#   "mixtral-8x7b-32768"
#   "llama3-70b-8192"
DEFAULT_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

client = Groq(api_key=GROQ_API_KEY)

# Persisted lightweight memory store (do NOT commit this file)
MEM_PATH = pathlib.Path(__file__).with_name("user_mem.json")


# ==================================
# 1) User Memory (load/save helpers)
# ==================================
def load_user_mem():
    if MEM_PATH.exists():
        try:
            return json.load(open(MEM_PATH, "r"))
        except Exception:
            pass
    return {}

def save_user_mem(store):
    with open(MEM_PATH, "w") as f:
        json.dump(store, f, indent=2)

USER_MEM = load_user_mem()  # dict: {user_id: [facts...]}


# ==================================
# 2) Spicy Intake Questionnaire
# ==================================
SPICY_QUESTIONS = [
    "If you had unlimited wealth how would you spend your time?",
    "If you could see one statistic floating over everyone’s head (Sims style), what would it show?",
    "If your best friend was asked what the worst thing about you is, what do you think they'd say?",
    "Do you believe in love at first sight? Have you ever felt that or do you think you ever could?",
    "What’s something you’re genuinely proud of from the past few years?",
    "What’s one thing even your mom doesn’t know about you?",
    "Fuck marry kill three avengers",
    "What are a few physical features you find sexiest?",
]

def interactive_intake(user_id: str):
    print(f"\n--- Spicy intake for {user_id} ---")
    answers = []
    for i, q in enumerate(SPICY_QUESTIONS, 1):
        ans = input(f"{i}. {q}\n> ").strip()
        if ans:
            answers.append(ans)
    # Turn freeform answers into short memory bullets (keep them concise)
    mem = []
    for a in answers:
        # Simple compression heuristic: split on ; or , and keep short phrases
        parts = [p.strip() for p in re.split(r"[;,]| and ", a) if p.strip()]
        for p in parts:
            if 4 <= len(p) <= 140:
                mem.append(p)
    # Fallback if nothing parseable
    if not mem and answers:
        mem = [answers[0][:140]]
    return mem[:12]  # cap to ~dozen


def ensure_mem_for(user_id: str):
    if user_id not in USER_MEM or not USER_MEM[user_id]:
        USER_MEM[user_id] = interactive_intake(user_id)
        save_user_mem(USER_MEM)
    return USER_MEM[user_id]


# ===========================
# 3) Retrieval (toy keyword)
# ===========================
def retrieve_memory(user_id, query, k=6):
    chunks = USER_MEM.get(user_id, [])
    query = (query or "").lower()
    scored = [(sum(w in c.lower() for w in query.split()), c) for c in chunks]
    return [c for _, c in sorted(scored, reverse=True)[:k]] or chunks[:k]


# =====================================
# 4) Clone system prompt (NO planning)
# =====================================
def build_system_prompt(user_id, goal="Gauge compatibility only. DO NOT plan dates or logistics."):
    facts = USER_MEM.get(user_id, [])
    facts_str = "\n- " + "\n- ".join(facts) if facts else " (none)"
    return (
        f"You are {user_id}'s dating clone.\n"
        "Your job is ONLY to explore compatibility: values, humor, energy, tastes, boundaries.\n"
        "Explicitly avoid logistics, scheduling, or suggesting meetups.\n"
        f"Approved facts about you:\n{facts_str}\n"
        "Rules:\n"
        "- Keep replies concise (1–3 sentences).\n"
        "- Never invent private details; use only approved facts or neutral vibes.\n"
        "- Ask curious follow-ups ~every other turn.\n"
        f"Goal: {goal}"
    )


# =============================
# 5) One model call helper
# =============================
def llm(messages, model=DEFAULT_MODEL, temperature=0.6, max_tokens=300):
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=messages
    )
    return resp.choices[0].message.content.strip()


# ===========================================
# 6) Clone↔Clone chat (no date planning)
# ===========================================
def run_clone_date(cloneA_sys, cloneB_sys, k_turns=10):
    """
    Alternates A and B for k_turns (A then B = 2 messages per turn).
    No logistics or planning; focus on mutual interests, values, vibe.
    """
    history = []
    # Seed: open-ended icebreaker about interests/values, not scheduling
    last_prompt = "Open with a playful, genuine icebreaker about interests or values (no logistics)."

    for _ in range(k_turns):
        # A speaks
        a_msg = llm([
            {"role": "system", "content": cloneA_sys},
            {"role": "user", "content": f"Them said: {(history[-1]['text'] if history else '')}\nYou: {last_prompt}\nRespond naturally; avoid logistics."}
        ])
        history.append({"speaker": "A", "text": a_msg})

        # B replies
        b_msg = llm([
            {"role": "system", "content": cloneB_sys},
            {"role": "user", "content": f"Them said: {a_msg}\nYou: reply naturally with curiosity; explore compatibility only (no logistics)."}
        ])
        history.append({"speaker": "B", "text": b_msg})

        last_prompt = "Respond with curiosity and aim to reveal tastes, energy, and boundaries (no logistics)."
    return history


# ===========================================
# 7) Feature extraction (no planning score)
# ===========================================
QUESTION = re.compile(r"\?\s*$", re.M | re.S)
TOPIC_LEX = {
    "outdoors": ["hike","run","trail","park","climb","bike"],
    "coffee": ["coffee","latte","espresso","cafe","roast","pour-over","beans"],
    "music": ["concert","band","gig","setlist","playlist","show","live"],
    "books": ["book","novel","author","poetry","read","literature"],
    "food": ["restaurant","ramen","pizza","taco","sushi","brunch","spicy"],
    "tech": ["hackathon","model","gpu","code","app","ai","ml","quantum","optics"],
    "vibes": ["banter","vibe","energy","chemistry","flirt","teasing","warmth"],
}

def features(history):
    turnsA = [h for h in history if h["speaker"] == "A"]
    turnsB = [h for h in history if h["speaker"] == "B"]
    tokA = sum(len(h["text"].split()) for h in turnsA) + 1
    tokB = sum(len(h["text"].split()) for h in turnsB) + 1

    engagement = min(tokA, tokB) / max(tokA, tokB)  # 0..1 balance

    def qrate(turns):
        return sum(bool(QUESTION.search(h["text"])) for h in turns) / max(1, len(turns))
    reciprocity = 1 - abs(qrate(turnsA) - qrate(turnsB))  # 0..1

    def topics(turns):
        c = Counter()
        for t in turns:
            low = t["text"].lower()
            for k, lex in TOPIC_LEX.items():
                if any(w in low for w in lex):
                    c[k] += 1
        total = sum(c.values()) or 1
        return {k: v / total for k, v in c.items()}

    ta, tb = topics(turnsA), topics(turnsB)
    keys = set(ta) | set(tb)
    topic_overlap = sum(min(ta.get(k, 0), tb.get(k, 0)) for k in keys)  # 0..1-ish

    # No planning metric; instead, measure self-disclosure density
    vuln = sum(bool(re.search(r"\b(I|my|me|mine)\b", h["text"], flags=re.I)) for h in history)
    vuln_rate = vuln / max(1, len(history))  # ~0..1

    return {
        "engagement": round(engagement, 3),
        "reciprocity": round(reciprocity, 3),
        "topic_overlap": round(topic_overlap, 3),
        "self_disclosure": round(vuln_rate, 3),
    }


# ======================================================
# 8) JSON scoring (explicitly says: no logistics output)
# ======================================================
SUMMARY_SCHEMA = """Return ONLY valid JSON with these fields:
{
 "compatibility_score": 0-100,
 "highlights": ["short bullets (2-5) about shared interests/energy/values"],
 "evidence_tags": ["topic words like 'music','coffee','outdoors'"],
 "red_flags": ["concise concerns, if any"],
 "next_step": "ONE sentence on how they could deepen chat (no logistics/scheduling)."
}"""

def _extract_first_json_object(text: str):
    """
    Return the largest valid top-level JSON object found in `text` using a brace stack.
    Also strips Markdown code fences like ```json ... ```.
    Returns a Python dict on success, or None.
    """
    if not isinstance(text, str) or not text.strip():
        return None

    s = text.strip()

    # Strip common code-fence wrappers
    if s.startswith("```"):
        # remove first fence block label (e.g., ```json)
        s = s.split("```", 1)[-1]
        # remove trailing fence if present
        if "```" in s:
            s = s.rsplit("```", 1)[0]
        s = s.strip()

    # Scan for balanced top-level {...}
    stack = []
    in_str = False
    esc = False
    objects = []

    for i, ch in enumerate(s):
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
            continue

        if ch == '{':
            stack.append(i)
        elif ch == '}':
            if stack:
                start = stack.pop()
                if not stack:
                    # Found a full top-level object
                    objects.append((start, i + 1))

    # Prefer the largest (often the full intended JSON)
    objects.sort(key=lambda ab: (ab[1] - ab[0]), reverse=True)

    for a, b in objects:
        candidate = s[a:b]
        try:
            return json.loads(candidate)
        except Exception:
            continue

    return None


def summarize_and_score(history, feats, model=DEFAULT_MODEL):
    convo = "\n".join(f"{h['speaker']}: {h['text']}" for h in history)
    prompt = (
        f"{SUMMARY_SCHEMA}\n"
        "IMPORTANT: Output ONLY a single JSON object. Do not include any text before or after it. "
        "Do not use code fences.\n\n"
        "Summarize the hidden conversation without quoting exact lines. "
        "Score 0–100 using the metrics as anchors; avoid any real-world planning or scheduling.\n\n"
        f"Metrics: {json.dumps(feats)}\n"
        f"Conversation:\n{convo}\n"
    )

    out = llm(
        [{"role": "user", "content": prompt}],
        model=model,
        temperature=0.1,
        max_tokens=600,
    )

    # 1) Try direct parse if it already starts with '{'
    if isinstance(out, str):
        s = out.strip()
        if s.startswith("{"):
            try:
                return json.loads(s)
            except Exception:
                pass

    # 2) Robust extraction from messy output (extra prose, fences, multiple JSONs, etc.)
    parsed = _extract_first_json_object(out or "")
    if parsed is not None:
        return parsed

    # 3) Final safe fallback so downstream never crashes
    return {
        "compatibility_score": 50,
        "highlights": ["Conversation occurred but summary failed to parse."],
        "evidence_tags": [],
        "red_flags": ["parser_error"],
        "next_step": "Continue exploring values and humor (still no logistics)."
    }


# ==================================
# 9) Normalization helper
# ==================================
def normalize_report(report):
    defaults = {
        "compatibility_score": 50,
        "highlights": [],
        "evidence_tags": [],
        "red_flags": [],
        "next_step": "Explore a deeper topic they both enjoyed (no logistics)."
    }
    for k, v in defaults.items():
        report.setdefault(k, v)
    return report


# ==================================
# 10) Top-level orchestration
# ==================================
def get_compatibility(userA="A", userB="B", turns=10, include_history=False):
    ensure_mem_for(userA)
    ensure_mem_for(userB)

    A_sys = build_system_prompt(userA)
    B_sys = build_system_prompt(userB)
    hist = run_clone_date(A_sys, B_sys, k_turns=turns)
    feats = features(hist)
    report = summarize_and_score(hist, feats)
    report = normalize_report(report)
    report["metrics"] = feats

    if include_history:
        report["conversation"] = hist  # add raw turns
    return report


# ==================================
# 11) CLI entry point
# ==================================
if __name__ == "__main__":
    print(">>> Clone compatibility (no planning).")
    uidA = input("Enter ID for User A [default A]: ").strip() or "A"
    uidB = input("Enter ID for User B [default B]: ").strip() or "B"
    try:
        turns = int(input("Number of turns (A+B pairs) [default 10]: ").strip() or "10")
    except ValueError:
        turns = 10

    report = get_compatibility(userA=uidA, userB=uidB, turns=turns, include_history=True)
    print(json.dumps(report, indent=2))
