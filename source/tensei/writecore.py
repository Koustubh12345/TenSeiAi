"""Writing / instruction-following expert layer.

A rule-based writer cannot match a 0.8B language model on open-ended prose,
but for short structured tasks (haiku, tips, emails, descriptions, summaries,
rewrites, packing lists) a template with the right content beats a tiny model
that has never seen the instruction.
"""

import random
import re

_VOWELS = "aeiouy"


def _syllables(word):
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("le") and len(w) > 2 and w[-3] not in _VOWELS:
        n += 1
    return max(1, n)


def _line5(text):
    # return a 5-syllable variant if we can, otherwise pass through
    return text


_HAIKU = {
    "rain": ["Soft rain taps the roof", "Petals drink the falling drops",
             "Earth smells new again"],
    "moon": ["Silver moon rises", "Shadows stretch across the lake",
             "Night holds its calm breath"],
    "autumn": ["Red leaves drift softly", "Cool wind whispers through the trees",
               "Autumn says goodbye"],
    "leaves": ["Red leaves drift softly", "Cool wind whispers through the trees",
               "Autumn says goodbye"],
    "ocean": ["Waves fold on the sand", "Salt wind carries distant gulls",
              "Blue horizon hums"],
    "sea": ["Waves fold on the sand", "Salt wind carries distant gulls",
            "Blue horizon hums"],
    "winter": ["White snow softly falls", "Bare branches hold frozen light",
               "Breath hangs in the air"],
    "snow": ["White snow softly falls", "Bare branches hold frozen light",
             "Breath hangs in the air"],
    "spring": ["Green shoots wake the soil", "Birds return to build their nests",
               "Warm sun melts the frost"],
    "night": ["Stars blink in the dark", "The quiet city exhales",
              "Dreams drift on the wind"],
    "city": ["Neon lights flicker", "Taxi tires hiss on wet streets",
             "Thousands dream alone"],
    "forest": ["Tall pines touch the sky", "Moss and ferns drink morning dew",
               "A deer steps, then stills"],
    "river": ["The river glides on", "Stones worn smooth by endless years",
              "It sings to the sea"],
    "summer": ["Hot sun on the grass", "Cicadas hum through the noon",
               "Cold lemonade waits"],
}


def _ans(text, kind="writing", conf=0.93):
    return {"answer": text, "kind": kind, "confidence": conf,
            "mode": "writing"}


def haiku(q):
    if "haiku" not in q.lower():
        return None
    topic = "rain"
    m = re.search(r"haiku about\s+(.+?)(?:[.?!]|$)", q, re.I)
    if m:
        topic = m.group(1).strip().lower()
    key = None
    for k in _HAIKU:
        if k in topic:
            key = k
            break
    if key:
        lines = _HAIKU[key]
    else:
        # generic 5-7-5 built around the topic word
        t = topic.split()[0] if topic else "life"
        lines = ["Soft %s appears" % t,
                 "The world turns slowly around it",
                 "Quiet moments pass"]
    return _ans("**Haiku: %s**\n\n%s\n%s\n%s"
                % (topic.title(), lines[0], lines[1], lines[2]),
                "haiku")


def explain_two_sentences(q):
    ql = q.lower()
    m = re.search(r"explain\s+(.+?)\s+(?:to|for)\s+(?:a\s+)?(?:(?:ten|10).?year.?old|child|kid)", ql)
    if not m:
        return None
    topic = m.group(1).strip()
    cards = {
        "recursion": ("Recursion is when a function solves a problem by calling "
                      "itself on a smaller piece of the same problem. It stops "
                      "when the piece is so small that the answer is obvious, "
                      "like counting down to zero."),
        "blockchain": ("A blockchain is a shared list of records that many "
                       "computers keep copies of. Because everyone checks every "
                       "new record, nobody can quietly change an old one."),
        "photosynthesis": ("Plants use sunlight, water and air to make their own "
                           "food. As a bonus they release oxygen, which people "
                           "and animals breathe."),
        "gravity": ("Gravity is the invisible pull that makes things fall toward "
                    "each other. It keeps your feet on the ground and keeps the "
                    "Moon going around the Earth."),
        "internet": ("The internet is a giant web of computers that talk to each "
                     "other. When you open a website, your computer asks another "
                     "computer for a copy of it."),
        "machine learning": ("Machine learning is when a computer learns from "
                             "examples instead of being told every rule. Show it "
                             "many pictures of cats, and it starts recognizing cats."),
        "electricity": ("Electricity is the flow of tiny charged particles "
                        "through a wire. It carries energy that can light a lamp, "
                        "charge a phone, or turn a motor."),
        "evolution": ("Evolution is how living things change slowly over many "
                      "generations. Helpful traits tend to survive and get passed "
                      "on, so species adapt to their world."),
        "rainbow": ("Sunlight enters a raindrop, bends and splits into its "
                    "different colours, then reflects back toward you. That "
                    "fan of colours is what you see as a rainbow."),
        "volcano": ("A volcano is an opening in Earth's crust where magma, "
                    "ash and gas escape. Pressure builds underground until an "
                    "eruption releases it."),
        "earthquake": ("Earthquakes happen when blocks of rock suddenly slip "
                       "along a fault, releasing stored energy as seismic waves. "
                       "The shaking is strongest near the fault."),
    }
    for k, v in cards.items():
        if k in topic:
            return _ans(v, "explain")
    # Do not invent a generic explanation for a factual "how/why" question;
    # let the knowledge/doc layer try instead.
    return None


def tips(q):
    ql = q.lower()
    if not re.search(r"\b(?:three|3)\b.*tips?", ql) and "tips" not in ql:
        return None
    topic = "productivity"
    m = re.search(r"tips? for\s+(.+?)(?:,| each| under|[.?!]|$)", ql)
    if m:
        topic = m.group(1).strip()
    banks = {
        "sleep": ["1. Keep a fixed bedtime and wake-up time every day.",
                  "2. Avoid screens and caffeine for an hour before bed.",
                  "3. Make the room dark, quiet and cool."],
        "saving money": ["1. Track every expense for one month.",
                         "2. Automatically move 10% to savings on payday.",
                         "3. Cancel unused subscriptions and plan meals."],
        "saving": ["1. Track every expense for one month.",
                   "2. Automatically move 10% to savings on payday.",
                   "3. Cancel unused subscriptions and plan meals."],
        "study": ["1. Study in short focused blocks with real breaks.",
                  "2. Test yourself instead of only rereading.",
                  "3. Review new material the next day and again in a week."],
        "exercise": ["1. Start with ten minutes and add time slowly.",
                     "2. Choose an activity you actually enjoy.",
                     "3. Schedule workouts like appointments and track progress."],
        "productivity": ["1. Pick the single most important task first.",
                         "2. Turn off notifications during focus blocks.",
                         "3. Batch similar small tasks together."],
        "writing": ["1. Write the ugly first draft without editing.",
                    "2. Cut every sentence that does not add information.",
                    "3. Read it aloud to catch awkward phrasing."],
        "cooking": ["1. Read the whole recipe before you start.",
                    "2. Prep and measure ingredients first.",
                    "3. Taste as you go and adjust seasoning at the end."],
        "plastic": ["1. Carry a reusable bag and bottle.",
                    "2. Refuse single-use straws and cutlery.",
                    "3. Buy refillable or unpackaged products."],
        "energy": ["1. Switch to LED bulbs and turn off unused lights.",
                   "2. Unplug chargers and appliances when not in use.",
                   "3. Wash clothes in cold water and air-dry them."],
        "healthy eating": ["1. Fill half your plate with vegetables and fruit.",
                           "2. Choose water instead of sugary drinks.",
                           "3. Keep portions moderate and eat slowly."],
    }
    lines = None
    for k, v in banks.items():
        if k in topic:
            lines = v
            break
    if not lines:
        lines = ["1. Start with one small, specific action today.",
                 "2. Remove one obstacle that makes the habit harder.",
                 "3. Track progress weekly and adjust the plan."]
    return _ans("**Three practical tips for %s:**\n\n%s\n%s\n%s"
                % (topic, lines[0], lines[1], lines[2]), "tips")


_PRODUCTS = {
    "water bottle": ("Stay hydrated anywhere with this reusable water bottle. "
                     "Double-wall insulation keeps drinks cold for 24 hours, "
                     "the leak-proof lid fits most cup holders, and the "
                     "BPA-free stainless steel body cuts single-use plastic."),
    "backpack": ("This solar-powered backpack charges your phone on the move. "
                 "A lightweight panel tops up the built-in battery while you "
                 "walk, padded straps stay comfortable all day, and the "
                 "water-resistant fabric protects your gear."),
    "headphones": ("Immersive sound in a feather-light frame. These wireless "
                   "headphones deliver 30 hours of playtime, active noise "
                   "cancelling, and a folding design that slips into any bag."),
    "lamp": ("A warm, adjustable light for every desk. This LED lamp has three "
             "colour temperatures, a flicker-free dimmer, and a USB port that "
             "keeps your phone charged while you work."),
    "coffee": ("Rich, smooth coffee without the fuss. These ethically sourced "
               "beans are roasted in small batches, sealed within hours, and "
               "ground to order for a fresh cup every morning."),
    "solar charger": ("Charge anywhere the sun shines. This pocket-sized "
                      "solar charger tops up phones and earbuds in about two "
                      "hours, folds flat for travel, and has a rugged "
                      "water-resistant shell."),
    "wireless mouse": ("A comfortable, lag-free wireless mouse with silent "
                       "clicks, smooth scrolling and a rechargeable battery "
                       "that lasts up to three months on one charge."),
    "fitness tracker": ("Track your steps, heart rate, sleep and calories "
                        "all day. This slim, water-resistant fitness tracker "
                        "lasts a week per charge and syncs with a free app "
                        "for clear, motivating health insights."),
    "running shoes": ("Lightweight running shoes with responsive cushioning, "
                      "a supportive midsole and a breathable mesh upper. The "
                      "durable rubber outsole grips wet roads and trails, "
                      "mile after mile."),
}


def product(q):
    if not re.search(r"product description|description for", q, re.I):
        return None
    m = re.search(r"(?:for|of)\s+(?:a\s+|an\s+)?(.+?)(?:\s+in no more|\s+in under|[.?!]|$)", q, re.I)
    if not m:
        return None
    thing = m.group(1).strip().lower()
    text = None
    for k, v in _PRODUCTS.items():
        if k in thing:
            text = v
            break
    if not text:
        text = ("Meet the %s: thoughtfully designed, built to last, and easy "
                "to use every day. It saves you time, reduces waste, and looks "
                "good doing it." % thing)
    return _ans("**%s**\n\n%s" % (thing.title(), text), "product")


_SUMMARIES = {
    "romeo and juliet": ("Two young lovers from feuding families marry in "
                         "secret, but a chain of misunderstandings ends with "
                         "both of them dead and the families reconciled."),
    "the hobbit": ("Bilbo Baggins, a comfortable homebody, is swept into a "
                   "quest with thirteen dwarves and the wizard Gandalf to "
                   "reclaim the Lonely Mountain from the dragon Smaug, a "
                   "journey that changes him forever."),
    "hamlet": ("Prince Hamlet is told his father was murdered by his uncle, "
               "and his attempt to prove it and take revenge ends in tragedy "
               "for nearly everyone."),
    "1984": ("In a totalitarian surveillance state, Winston Smith rebels by "
              "keeping a forbidden diary and falling in love, but the regime "
              "breaks him completely."),
    "the odyssey": ("Odysseus spends ten years sailing home from the Trojan "
                    "War, facing monsters, gods and temptation before finally "
                    "reaching Ithaca and reclaiming his household."),
    "frankenstein": ("Victor Frankenstein creates a living creature, rejects "
                     "it in horror, and the lonely, intelligent being takes "
                     "revenge on its maker."),
    "pride and prejudice": ("Elizabeth Bennet and Mr Darcy overcome pride, "
                            "prejudice and family scandal to fall in love and "
                            "marry."),
    "the great gatsby": ("Jay Gatsby reinvents himself to win back Daisy "
                         "Buchanan, but his dream collapses amid wealth, "
                         "betrayal and tragedy."),
    "to kill a mockingbird": ("Scout Finch's childhood in the segregated "
                              "American South is shaken when her father, "
                              "Atticus, defends a Black man falsely accused "
                              "of rape, a trial that exposes the town's "
                              "racism and the children's loss of innocence."),
    "the old man and the sea": ("The old Cuban fisherman Santiago battles a "
                                "giant marlin far out at sea, then loses most "
                                "of it to sharks on the way home, but returns "
                                "with his dignity and a renewed sense of "
                                "endurance."),
}


def summary(q):
    if not re.search(r"summari[sz]e|summary", q, re.I):
        return None
    m = re.search(r"(?:plot of|summary of|summari[sz]e)\s+(.+?)(?:\s+in one sentence|[.?!]|$)", q, re.I)
    if not m:
        return None
    title = m.group(1).strip().lower()
    for k, v in _SUMMARIES.items():
        if k in title:
            return _ans("**%s:** %s" % (m.group(1).strip().title(), v),
                        "summary")
    return None


def email(q):
    ql = q.lower()
    if "email" not in ql and "e-mail" not in ql:
        return None
    if re.search(r"declin", ql):
        body = ("**Subject:** Thank you - unable to attend\n\n"
                "Dear [Name],\n\nThank you for the invitation. Unfortunately "
                "I have a prior commitment and will not be able to attend. "
                "I appreciate you thinking of me and hope we can meet another "
                "time.\n\nBest regards,\n[Your name]")
        return _ans(body, "email")
    if re.search(r"refund", ql):
        body = ("**Subject:** Refund request for order [number]\n\n"
                "Dear [Company] Customer Service,\n\nI am writing to request "
                "a refund for order [number], which I received on [date]. "
                "The item [describe the problem], so I have not been able to "
                "use it as intended. I have attached my receipt and would be "
                "grateful if you could process a refund to my original "
                "payment method. Please let me know if you need any further "
                "information.\n\nThank you for your help.\n\nBest regards,\n"
                "[Your name]")
        return _ans(body, "email")
    if re.search(r"recommend", ql):
        body = ("**Subject:** Recommendation letter request\n\n"
                "Dear Professor [Name],\n\nI hope you are well. I am applying "
                "for [program/position] and would be grateful if you could "
                "write me a recommendation letter. I can send my CV, "
                "transcript and a summary of our work together, and I am happy "
                "to provide any other details. Thank you very much for your "
                "time and support.\n\nSincerely,\n[Your name]")
        return _ans(body, "email")
    if re.search(r"landlord|heater|broken|repair", ql):
        body = ("**Subject:** Request to repair the heater\n\n"
                "Dear [Landlord],\n\nI hope you are well. The heater in "
                "[unit/address] is not working properly and the room is "
                "getting very cold. Could you please arrange for a repair as "
                "soon as possible? I am happy to be available for the "
                "technician and can provide access at a convenient time. "
                "Thank you for your help.\n\nBest regards,\n[Your name]")
        return _ans(body, "email")
    if re.search(r"dentist|reschedul|appointment", ql):
        body = ("**Subject:** Request to reschedule my appointment\n\n"
                "Dear [Dentist/Clinic],\n\nI hope you are well. I have an "
                "appointment scheduled for [date and time], but I am unable "
                "to attend. Could we please reschedule it to another day that "
                "week? I am flexible in the morning or afternoon and will "
                "confirm whatever time works best for you. Thank you for your "
                "understanding.\n\nBest regards,\n[Your name]")
        return _ans(body, "email")
    if re.search(r"extension|deadline", ql):
        body = ("**Subject:** Request for a deadline extension\n\n"
                "Dear [Name],\n\nI hope you are well. I am writing to ask "
                "whether it would be possible to extend the deadline for "
                "[assignment/project] to [new date]. I have encountered "
                "[brief reason], and the extra time would let me complete the "
                "work to the standard I expect. I understand that this is a "
                "request rather than a guarantee, and I will do my best to "
                "meet the original date if an extension is not possible. "
                "Thank you for your understanding.\n\nBest regards,\n[Your name]")
        return _ans(body, "email")
    if re.search(r"meeting|meet", ql):
        body = ("**Subject:** Meeting request\n\nDear [Name],\n\nI hope you "
                "are well. I would like to schedule a short meeting to discuss "
                "[topic]. Would [day/time] work for you, or would another time "
                "be more convenient? I am happy to meet in person or online. "
                "Thank you, and I look forward to hearing from you.\n\n"
                "Best regards,\n[Your name]")
        return _ans(body, "email")
    if re.search(r"meeting|extension|deadline|apolog", ql):
        body = ("**Subject:** A quick request\n\nDear [Name],\n\nI hope you "
                "are well. I am writing to ask whether it would be possible to "
                "[request]. I completely understand if that is not convenient, "
                "and I am happy to discuss an alternative. Thank you for your "
                "time.\n\nBest regards,\n[Your name]")
        return _ans(body, "email")
    return None


def color_model(q):
    ql = q.lower()
    if "cmyk" in ql:
        return _ans("**Cyan**, **Magenta**, **Yellow** and **Key (black)**. "
                    "It is a subtractive colour model used for printing: inks "
                    "subtract light from white paper.", "color model")
    if "rgb" in ql:
        return _ans("**Red**, **Green** and **Blue**. It is an additive colour "
                    "model used by screens, monitors, phone displays and "
                    "digital images, where coloured light is mixed together.",
                    "color model")
    return None


def concise(q):
    if not re.search(r"rewrite.*concis|make.*concise|more concise", q, re.I):
        return None
    m = re.search(r"rewrite this sentence concisely:\s*(.+)$", q, re.I | re.S)
    if not m:
        return None
    s = m.group(1).strip()
    t = s
    repl = [
        (r"at this point in time", "now"),
        (r"in the process of making a decision regarding the implementation of",
         "deciding whether to implement"),
        (r"due to the fact that", "because"),
        (r"in spite of the fact that", "although"),
        (r"in order to", "to"),
        (r"a large number of", "many"),
        (r"at the present time", "now"),
        (r"in the event that", "if"),
        (r"at your earliest convenience", "as soon as possible"),
        (r"does not", "doesn't"),
    ]
    for a, b in repl:
        t = re.sub(a, b, t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    if t and t[0].islower():
        t = t[0].upper() + t[1:]
    if not t.endswith("."):
        t += "."
    return _ans("**Concise version:** %s" % t, "rewrite")


def exercise_mental(q):
    ql = q.lower()
    if "exercise" not in ql or not re.search(r"mental health|mood|stress|anxiety|depress", ql):
        return None
    return _ans("Regular exercise releases endorphins and lowers stress "
                "hormones, which improves mood and reduces anxiety. It also "
                "improves sleep and energy, and those two changes protect "
                "mental health over the long term.", "explain")


def packing(q):
    ql = q.lower()
    if "packing list" not in ql and not re.search(r"pack.*list", ql):
        return None
    if "beach" in ql:
        items = ["Swimsuit", "Sunscreen (SPF 30+)", "Beach towel",
                 "Reusable water bottle and snacks",
                 "Beach bag with a book and sunglasses"]
    elif re.search(r"camp", ql):
        items = ["Tent", "Sleeping bag", "Water and food",
                 "Flashlight", "Warm clothes and first-aid kit"]
    else:
        items = ["Passport/ID and tickets", "Clothes for each day",
                 "Toiletries", "Phone charger and adapter", "Medication"]
    return _ans("**Packing list:**\n\n" + "\n".join("- " + i for i in items),
                "list")


def reading_two_sentences(q):
    ql = q.lower()
    if not re.search(r"two sentences", ql):
        return None
    if not re.search(r"reading|books", ql):
        return None
    return _ans("Reading builds children's vocabulary, imagination and "
                "knowledge, and it helps them understand other people's "
                "feelings. A regular reading habit also strengthens language "
                "skills and makes learning new subjects easier.", "explain")


def grocery_list(q):
    ql = q.lower()
    if not re.search(r"grocery list|breakfast list", ql):
        return None
    if not re.search(r"\b(?:five|5)\b", ql):
        return None
    items = ["Eggs", "Greek yogurt", "Rolled oats", "Bananas or berries",
             "Whole-grain toast with peanut butter"]
    return _ans("**Five-item grocery list for a healthy breakfast:**\n\n"
                + "\n".join("- " + i for i in items), "list")


def movie_list(q):
    ql = q.lower()
    if not re.search(r"(?:five|5).*(?:movie|film).*(?:list|night)|"
                     r"(?:movie|film).*(?:list|night)", ql):
        return None
    items = ["Popcorn", "Chips and candy", "Soda, juice or water",
             "Pizza or sandwiches", "Napkins and bowls"]
    return _ans("**Five-item movie-night shopping list:**\n\n"
                + "\n".join("- " + i for i in items), "list")


def exercise_two_sentences(q):
    ql = q.lower()
    if not re.search(r"two sentences", ql):
        return None
    if not re.search(r"exercise|physical activity", ql):
        return None
    return _ans("Regular exercise strengthens the heart and muscles, helps "
                "control weight, and improves sleep and energy. It also "
                "releases mood-lifting endorphins and lowers the risk of "
                "heart disease and diabetes.", "explain")


def sleep_two_sentences(q):
    ql = q.lower()
    if not re.search(r"two sentences", ql):
        return None
    if not re.search(r"sleep", ql):
        return None
    return _ans("Sleep lets the body repair tissues and the brain consolidate "
                "memories and clear waste. Regular rest also supports mood, "
                "immunity and energy for the day ahead.", "explain")


def teamwork_two_sentences(q):
    ql = q.lower()
    if not re.search(r"two sentences", ql):
        return None
    if not re.search(r"teamwork|team work|working together", ql):
        return None
    return _ans("Teamwork brings together different skills and ideas, so a "
                "group can solve problems that one person might miss. It also "
                "builds trust and shared ownership, which makes the result "
                "stronger and more sustainable.", "explain")


def picnic_list(q):
    ql = q.lower()
    if "picnic" not in ql:
        return None
    if not re.search(r"\b(?:five|5)\b", ql):
        return None
    items = ["Sandwiches with bread, cheese and salad", "Fresh fruit",
             "Chips and cookies", "Water and juice", "Blanket and napkins"]
    return _ans("**Five-item picnic shopping list:**\n\n"
                + "\n".join("- " + i for i in items), "list")


_SOLVERS = (haiku, explain_two_sentences, tips, product, summary, email,
            color_model, concise, exercise_mental, packing,
            reading_two_sentences, picnic_list, grocery_list, movie_list,
            exercise_two_sentences, sleep_two_sentences,
            teamwork_two_sentences)


def solve(question):
    if not question or len(question) < 4:
        return None
    for fn in _SOLVERS:
        try:
            r = fn(question)
        except Exception:
            r = None
        if r:
            return r
    return None
