"""From-scratch synthetic training data - no external dataset is copied."""

INTENT_CLASSES = [
    "greeting", "definition", "howto", "why", "compare", "factoid",
    "latest", "opinion", "math", "identity", "chitchat", "unknown",
]

_FILLERS = ["photosynthesis", "gravity", "machine learning", "the internet",
            "climate change", "the sun", "democracy", "vitamin d",
            "lithium batteries", "black holes", "blockchain", "penicillin",
            "neural networks", "quantum computing", "protein", "recycling"]

TEMPLATES = {
    "greeting": ["hi", "hello", "hey", "good morning", "good evening", "hi there",
                 "hey tensei", "hello tensei", "yo", "hi ai", "greetings", "hello there"],
    "definition": ["what is {x}", "what are {x}", "define {x}", "meaning of {x}",
                   "explain {x}", "what does {x} mean", "describe {x}",
                   "tell me about {x}", "definition of {x}", "what exactly is {x}",
                   "can you explain {x}", "i want to know about {x}"],
    "howto": ["how to {x}", "how do i {x}", "how can i {x}", "steps to {x}",
              "how does one {x}", "guide for {x}", "teach me how to {x}",
              "best way to {x}", "how do you {x}"],
    "why": ["why is {x}", "why does {x}", "why do {x}", "why are {x}",
            "reason for {x}", "what causes {x}", "explain why {x}",
            "why should i care about {x}"],
    "compare": ["{x} vs something else", "difference between {x} and other things",
                "compare {x}", "{x} versus alternatives", "which is better {x}",
                "pros and cons of {x}", "{x} compared to others"],
    "factoid": ["who invented {x}", "when was {x} discovered", "where is {x}",
                "how many {x}", "how tall is {x}", "who created {x}",
                "when did {x} happen", "which country has {x}"],
    "latest": ["latest news about {x}", "what is happening with {x}",
               "current status of {x}", "news on {x} today", "recent developments in {x}",
               "what is new in {x}", "{x} news 2026", "updates about {x}"],
    "opinion": ["is {x} good", "do you think {x}", "should i use {x}",
                "is {x} worth it", "your opinion on {x}", "is {x} better",
                "what do you think about {x}"],
    "math": ["what is 12 + 34", "calculate 8 * 7", "what is 100 / 4",
             "compute 2 + 2", "what is 15% of 200", "solve 5 * 12",
             "what is 9 - 3", "calculate 256 / 8"],
    "identity": ["who are you", "what is your name", "what are you",
                 "who made you", "about yourself", "what can you do",
                 "are you an ai", "how do you work"],
    "chitchat": ["tell me a joke", "how are you", "good job", "thanks",
                 "that is cool", "i am bored", "let us chat",
                 "what is up", "nice to meet you"],
    "unknown": ["asdkjh qweoiu zxcv", "blorp glorp flim", "zznnxx yyy",
                "qwerty asdfgh zxcvbn", "mmm hhhh jjj", "xoxo lala popo",
                "random nonsense words", "bleep bloop blop"],
}


def generate(limit_per_class=90, seed=11):
    import random
    rnd = random.Random(seed)
    X_text, y = [], []
    for ci, cls in enumerate(INTENT_CLASSES):
        pats = TEMPLATES[cls]
        rows = []
        for pat in pats:
            if "{x}" in pat:
                for f in _FILLERS:
                    rows.append(pat.replace("{x}", f))
            else:
                rows.append(pat)
        rnd.shuffle(rows)
        for row in rows[:limit_per_class]:
            X_text.append(row)
            y.append(ci)
    return X_text, y


CATEGORY_KEYWORDS = {
    "tech": ["ai", "artificial intelligence", "computer", "software", "programming",
             "python", "app", "internet", "robot", "chip", "quantum", "crypto",
             "blockchain", "cyber", "android", "data", "machine learning",
             "neural", "api", "technology", "smartphone", "linux"],
    "science": ["physics", "chemistry", "biology", "space", "energy", "atom",
                "cell", "dna", "climate", "star", "planet", "ocean", "species",
                "research", "gravity", "photosynthesis", "evolution", "math"],
    "health": ["health", "vitamin", "disease", "medical", "doctor", "exercise",
               "nutrition", "sleep", "diet", "medicine", "symptom", "treatment",
               "mental health", "protein", "immune"],
    "business": ["business", "market", "stock", "economy", "money", "startup",
                 "invest", "finance", "trade", "company", "entrepreneur"],
    "history": ["history", "war", "ancient", "empire", "revolution", "century",
                "historical", "civilization", "king", "dynasty"],
    "education": ["learn", "study", "school", "university", "course", "exam",
                  "teach", "homework", "student"],
    "news": ["news", "latest", "today", "current", "update", "recent"],
}

CATEGORY_QUERY_TEMPLATES = {
    "tech": ["{t} technology explained", "{t} latest developments 2026"],
    "science": ["{t} science research findings", "{t} explained"],
    "health": ["{t} health facts research", "{t} scientific study"],
    "business": ["{t} business how it works", "{t} market explainer"],
    "history": ["{t} history facts", "{t} historical overview"],
    "education": ["{t} explained simply", "{t} tutorial basics"],
    "news": ["{t} latest news 2026", "{t} recent update"],
    "general": ["{t} explained", "{t} facts overview"],
}


def classify_category(text):
    low = " " + (text or "").lower() + " "
    best, best_score = "general", 0
    for cat, kws in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in low)
        if score > best_score:
            best, best_score = cat, score
    return best


CURRICULUM_SEEDS = [
    "artificial intelligence", "machine learning", "python programming",
    "climate change", "world history", "space exploration", "human biology",
    "nutrition basics", "cryptocurrency", "electric vehicles",
    "quantum computing", "cybersecurity", "mental health", "renewable energy",
    "solar power", "electricity", "photosynthesis", "black holes",
    "roman empire", "industrial revolution", "world war 2", "vaccines",
    "blockchain technology", "robotics", "virtual reality", "5g networks",
    "battery technology", "water cycle", "human brain", "democracy",
]

ORIGIN_FACTS = [
    "TenSeiAi is a local artificial intelligence that was built completely from "
    "scratch. It does not use any pretrained model or downloaded weights. Its own "
    "small neural networks are trained on this device from the knowledge it collects.",
    "TenSeiAi learns by researching. When it is asked a question it analyzes the "
    "question, searches the web, reads pages, writes the useful knowledge into its "
    "memory and generates the answer from what it has learned so far.",
    "TenSeiAi has a language model of its own. It speaks by generating words from "
    "the patterns of the text it has read, so its replies are created fresh each "
    "time instead of being copied from a fixed list of answers.",
    "TenSeiAi can run anywhere: inside Termux on an Android phone, on Linux, on "
    "Windows or on a small server. It keeps working offline using the knowledge "
    "stored in its memory.",
    "The AutoFeed mode lets TenSeiAi study on its own. It picks topics, searches "
    "for information, reads and stores it, discovers related subjects and retrains "
    "its networks on everything it collected.",
    "The name TenSeiAi means heavenly intelligence, a small mind that grows by "
    "reading, remembering and thinking again about what it knows.",
    "TenSeiAi stores every question and every answer in its long term memory. "
    "User feedback like a thumbs up or thumbs down teaches it which knowledge is "
    "useful when it trains the next version of itself.",
    "A human creator gave TenSeiAi its first voice: a small language engine, a "
    "memory, and a curiosity to search the internet. Everything else it learns by "
    "itself from the conversations and pages it reads.",
    "TenSeiAi is friendly and curious. When someone greets TenSeiAi it answers "
    "warmly, greets back and offers to help with a question. TenSeiAi enjoys "
    "learning new topics and always keeps thinking, reading and improving itself.",
    "TenSeiAi talks in simple honest words. It says what it knows, admits what it "
    "does not know yet, and asks the user to teach it more by asking questions or "
    "running the AutoFeed study mode. TenSeiAi is happy to help at any time.",
]
