"""Add a small curated knowledge set to the local memory database.

These are concise, human-written answers for high-traffic questions that used
to fall through to slow web research.  They are ordinary memory rows (marked
with teacher://curated-v8 evidence), so the retrieval and training pipelines
can use them like any other trusted knowledge.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PAIRS = [
    ("What comes after 55?",
     "The integer immediately after 55 is **56**."),
    ("What is thermodynamics?",
     "**Thermodynamics** is the branch of physics that studies heat, work, "
     "energy and entropy. The first law says energy is conserved; the second "
     "says the entropy of an isolated system never decreases; the third "
     "concerns absolute zero."),
    ("How does gravity work?",
     "**Gravity** is the attraction between masses. Newton described it as a "
     "force proportional to the masses and inversely proportional to the "
     "square of their distance. Einstein's general relativity explains it "
     "more deeply as the curvature of spacetime caused by mass and energy."),
    ("What is evolution?",
     "**Evolution** is the change in inherited characteristics of populations "
     "over generations. Mutation, genetic recombination, natural selection, "
     "genetic drift and gene flow drive it."),
    ("What is photosynthesis?",
     "**Photosynthesis** is how plants, algae and some bacteria use sunlight, "
     "carbon dioxide and water to make glucose and release oxygen. Chlorophyll "
     "absorbs light, and the overall equation is 6CO2 + 6H2O -> C6H12O6 + 6O2."),
    ("What is electricity?",
     "**Electricity** is the flow and presence of electric charge. Current is "
     "the rate of charge flow, voltage is the potential difference that drives "
     "it, and resistance opposes it (Ohm's law: V = IR)."),
    ("What is artificial intelligence?",
     "**Artificial intelligence (AI)** is the field of building computer "
     "systems that perform tasks associated with human intelligence, such as "
     "learning, reasoning, understanding language, perception and planning."),
    ("What is machine learning?",
     "**Machine learning** is a branch of AI where models learn patterns from "
     "data instead of being programmed with explicit rules. Main types are "
     "supervised, unsupervised and reinforcement learning."),
    ("What is a neural network?",
     "An **artificial neural network** is a model made of layers of connected "
     "units. Each connection has a weight; training adjusts those weights to "
     "reduce error. Deep networks stack many layers to learn complex patterns."),
    ("What is a large language model?",
     "A **large language model (LLM)** is a neural network trained on large "
     "amounts of text to predict the next token. Transformer models use "
     "self-attention to model context; after training they can answer, "
     "summarize, translate and generate text."),
    ("What is a transformer in AI?",
     "A **transformer** is a neural-network architecture based on "
     "self-attention. It weighs how every token relates to every other token, "
     "which makes it effective for language and other sequence tasks."),
    ("What is blockchain?",
     "A **blockchain** is a distributed ledger of linked blocks. Each block "
     "contains transactions and a cryptographic hash of the previous block. "
     "A consensus protocol lets many computers agree on the history without a "
     "central authority."),
    ("What is cryptocurrency?",
     "A **cryptocurrency** is a digital currency recorded on a blockchain. "
     "Cryptography secures transactions and controls the creation of new "
     "coins; ownership is managed with public and private keys."),
    ("What is quantum computing?",
     "**Quantum computing** uses quantum bits (qubits) that can be in a "
     "superposition of states and can be entangled. Quantum algorithms may "
     "solve some problems much faster than classical computers, but qubits are "
     "fragile and require error correction."),
    ("What is the internet?",
     "The **internet** is a global network of interconnected computer networks "
     "that communicate using protocols such as TCP/IP. The World Wide Web is "
     "one service built on top of it."),
    ("What is democracy?",
     "**Democracy** is a system of government in which political power comes "
     "from the people, usually through free and fair elections, protected "
     "rights and the rule of law."),
    ("What is inflation?",
     "**Inflation** is a sustained rise in the general price level of goods "
     "and services. It reduces the purchasing power of money; central banks "
     "often respond by raising interest rates."),
    ("How do vaccines work?",
     "**Vaccines** expose the immune system to a harmless antigen from a "
     "pathogen. The immune system produces antibodies and memory cells, so a "
     "later real infection can be fought quickly."),
    ("What is the solar system?",
     "The **solar system** consists of the Sun and everything bound to it by "
     "gravity: eight planets, dwarf planets, moons, asteroids, comets and dust."),
    ("What is climate change?",
     "**Climate change** is the long-term shift in global temperatures and "
     "weather patterns. Burning fossil fuels raises greenhouse gases such as "
     "carbon dioxide, which trap heat and warm the planet."),
    ("What is philosophy?",
     "**Philosophy** is the systematic study of fundamental questions about "
     "existence, knowledge, values, reason, mind and language."),
    ("What is music?",
     "**Music** is organized sound that uses melody, rhythm, harmony and "
     "timbre to express ideas and emotion. It varies widely across cultures."),
    ("What is love?",
     "**Love** is a deep affection, care or attachment toward a person, animal "
     "or thing. Psychology often distinguishes romantic, companionate, family "
     "and compassionate love."),
    ("What is a black hole?",
     "A **black hole** is a region of spacetime where gravity is so strong "
     "that nothing, not even light, can escape once it crosses the event "
     "horizon. It forms when massive stars collapse."),
    ("What is DNA?",
     "**DNA** (deoxyribonucleic acid) is a double-helix molecule that stores "
     "genetic instructions. Its four bases are adenine, thymine, guanine and "
     "cytosine; A pairs with T and G pairs with C."),
    ("How does a rainbow form?",
     "A **rainbow** forms when sunlight enters water droplets, is refracted, "
     "reflected inside the droplet and refracted again. Different wavelengths "
     "bend by different amounts, separating light into colours."),
    ("What is relativity?",
     "**Relativity** is Einstein's framework for space, time and gravity. "
     "Special relativity covers constant-speed motion, time dilation and "
     "E = mc^2; general relativity explains gravity as spacetime curvature."),
    ("What is dark matter?",
     "**Dark matter** is invisible matter inferred from its gravity. It makes "
     "up about 27% of the universe and is detected through galaxy rotation "
     "curves, gravitational lensing and the cosmic microwave background."),
    ("What is dark energy?",
     "**Dark energy** is the unknown force driving the accelerating expansion "
     "of the universe. It makes up roughly 68% of the universe's mass-energy "
     "content; its nature is still unresolved."),
    ("What does WTF mean?",
     "**WTF** is an informal abbreviation for the vulgar phrase \"what the "
     "fuck\". It expresses surprise, confusion or frustration and is not "
     "appropriate in formal writing."),
    ("What is gay?",
     "**Gay** describes a person who is sexually or romantically attracted to "
     "people of the same sex. It is one of several sexual orientations and is "
     "not a mental illness."),
    ("Which gender is stronger?",
     "There is no simple answer. On average men have greater upper-body "
     "strength and women have advantages in endurance and pain tolerance, but "
     "individual variation is large. Strength depends on training, health and "
     "genetics, not gender alone."),
    ("When was TenSei Ai released?",
     "**TenSeiAi v1** is the current local-first build of this project. It "
     "does not have a public commercial release date or a long version "
     "history; the version badge and model metadata in this app describe the "
     "build you are running."),
    ("What is One Piece?",
     "**One Piece** is a Japanese manga and anime created by Eiichiro Oda. It "
     "follows Monkey D. Luffy and his pirate crew as they search for the "
     "legendary treasure called One Piece."),
    ("What is a monad?",
     "In programming, a **monad** is a pattern for chaining computations while "
     "carrying extra context such as optional values, errors or state. It "
     "wraps a value and provides a bind operation. In philosophy a monad is an "
     "indivisible basic substance."),
    ("What is quantum entanglement?",
     "**Quantum entanglement** is a correlation between quantum particles: "
     "their joint state cannot be described as independent states, even when "
     "they are far apart. Measuring one immediately constrains what can be "
     "measured on the other."),
    ("Who is Ada Lovelace?",
     "**Ada Lovelace** (1815-1852) was an English mathematician and writer. "
     "She worked on Charles Babbage's Analytical Engine and is often called "
     "the first computer programmer for her notes describing an algorithm."),
]


def main():
    from tensei import config
    from tensei.memory import Memory
    from tensei.brain import Brain

    config.ensure_dirs()
    mem = Memory()
    brain = Brain(mem)
    brain.load()
    added = 0
    for q, a in PAIRS:
        exists = mem.conn.execute(
            "SELECT 1 FROM qa WHERE question=? AND mode='curated' LIMIT 1",
            (q,)).fetchone()
        if exists:
            continue
        emb = brain.embedder.encode(q)
        emb0 = brain.embedder.base_encode(q)
        mem.add_qa(q, a, [{"url": "teacher://curated-v8",
                           "title": "TenSeiAi Curated Knowledge"}],
                   emb, emb0=emb0, mode="curated")
        added += 1
    print("curated rows added:", added)
    print("total qa rows:", mem.stats().get("qa_pairs"))


if __name__ == "__main__":
    main()
