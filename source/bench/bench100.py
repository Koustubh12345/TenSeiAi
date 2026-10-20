"""
100-Question Multi-Domain Benchmark for TenSeiAi.
Covers 5 core domains (20 questions each, mixed difficulty from basic to advanced):
1. Coding & Computer Science
2. Science & Physics
3. Biology & Animals
4. Geography & World Knowledge
5. Mathematics & Logic
"""

import sys
import os
import json
import time
import shutil
import tempfile
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

QUESTIONS = [
    # --- 1. Coding & Computer Science (20) ---
    {
        "id": "code_01",
        "domain": "Coding",
        "difficulty": "Hard",
        "q": "Write a complete Python program that implements a password manager using AES-256 encryption. Include secure key derivation, password storage and retrieval, input validation, error handling, and example usage. Explain the security considerations and verify that the code is correct.",
        "must_have": ["AES256", "PasswordManager", "PBKDF2", "HMAC"]
    },
    {
        "id": "code_02",
        "domain": "Coding",
        "difficulty": "Medium",
        "q": "Write a complete Python program that finds all prime numbers up to a given integer n using the Sieve of Eratosthenes. Explain the algorithm step by step, analyze its time and space complexity using Big O notation, handle invalid inputs, and provide example outputs.",
        "must_have": ["is_prime", "O(n", "log"]
    },
    {
        "id": "code_03",
        "domain": "Coding",
        "difficulty": "Hard",
        "q": "Write a complete, executable Java program to find the k-th largest element in an unsorted integer array without sorting the entire array. Use an efficient algorithm such as a min-heap with a PriorityQueue. Handle duplicate elements, invalid values of k, and empty arrays. Include example inputs and outputs, explain the algorithm step by step, analyze time and space complexity using Big O notation, and ensure the code compiles and produces correct results.",
        "must_have": ["PriorityQueue", "k", "Heap", "O(N"]
    },
    {
        "id": "code_04",
        "domain": "Coding",
        "difficulty": "Medium",
        "q": "Implement an LRU Cache in Python with O(1) get and put time complexity. Explain the design and data structures used.",
        "must_have": ["LRUCache", "capacity", "head", "tail"]
    },
    {
        "id": "code_05",
        "domain": "Coding",
        "difficulty": "Hard",
        "q": "Write a Python implementation of Dijkstra's algorithm to find the shortest path in a weighted graph. Include time complexity analysis.",
        "must_have": ["dijkstra", "heapq", "distances"]
    },
    {
        "id": "code_06",
        "domain": "Coding",
        "difficulty": "Easy",
        "q": "What is Big O notation?",
        "must_have": ["complexity", "algorithm", "asymptotic"]
    },
    {
        "id": "code_07",
        "domain": "Coding",
        "difficulty": "Medium",
        "q": "Explain how a Binary Search Tree (BST) works, including its search, insert, and delete operations and average vs worst-case time complexity.",
        "must_have": ["left", "right", "O(log n)", "O(n)"]
    },
    {
        "id": "code_08",
        "domain": "Coding",
        "difficulty": "Medium",
        "q": "Explain the difference between Quick Sort and Merge Sort. Which one is stable and what are their worst-case time complexities?",
        "must_have": ["Quick Sort", "Merge Sort", "stable", "O(n log n)"]
    },
    {
        "id": "code_09",
        "domain": "Coding",
        "difficulty": "Easy",
        "q": "Write a Python function to check whether a string is a palindrome.",
        "must_have": ["def ", "return", "[::-1]"]
    },
    {
        "id": "code_10",
        "domain": "Coding",
        "difficulty": "Easy",
        "q": "Write a Python function that computes the nth Fibonacci number using dynamic programming.",
        "must_have": ["fib", "return"]
    },
    {
        "id": "code_11",
        "domain": "Coding",
        "difficulty": "Medium",
        "q": "Explain how hash tables handle collisions using separate chaining versus open addressing.",
        "must_have": ["collision", "chaining", "open addressing"]
    },
    {
        "id": "code_12",
        "domain": "Coding",
        "difficulty": "Easy",
        "q": "Write a complete Python script to reverse a singly linked list.",
        "must_have": ["prev", "curr", "next"]
    },
    {
        "id": "code_13",
        "domain": "Coding",
        "difficulty": "Medium",
        "q": "Explain the difference between a process and a thread in operating systems.",
        "must_have": ["memory", "thread", "process", "address space"]
    },
    {
        "id": "code_14",
        "domain": "Coding",
        "difficulty": "Medium",
        "q": "Explain ACID properties in relational database transactions.",
        "must_have": ["Atomicity", "Consistency", "Isolation", "Durability"]
    },
    {
        "id": "code_15",
        "domain": "Coding",
        "difficulty": "Medium",
        "q": "Explain how the TCP three-way handshake establishes a connection.",
        "must_have": ["SYN", "ACK"]
    },
    {
        "id": "code_16",
        "domain": "Coding",
        "difficulty": "Medium",
        "q": "Write a SQL query to find the second highest salary from an Employee table.",
        "must_have": ["SELECT", "FROM", "LIMIT", "OFFSET"]
    },
    {
        "id": "code_17",
        "domain": "Coding",
        "difficulty": "Easy",
        "q": "Write a complete Dockerfile to containerize a Python Flask web application.",
        "must_have": ["FROM python", "WORKDIR", "COPY", "RUN", "CMD"]
    },
    {
        "id": "code_18",
        "domain": "Coding",
        "difficulty": "Medium",
        "q": "Explain the difference between asynchronous programming, multithreading, and multiprocessing in Python.",
        "must_have": ["GIL", "event loop", "asyncio", "process"]
    },
    {
        "id": "code_19",
        "domain": "Coding",
        "difficulty": "Hard",
        "q": "Explain how RSA asymmetric cryptography works, including public and private key generation and modular exponentiation.",
        "must_have": ["prime", "modular", "public key", "private key"]
    },
    {
        "id": "code_20",
        "domain": "Coding",
        "difficulty": "Medium",
        "q": "Write a Python solution for the Two Sum problem that runs in O(n) time using a hash map.",
        "must_have": ["dict", "target - num", "return"]
    },

    # --- 2. Science & Physics (20) ---
    {
        "id": "sci_01",
        "domain": "Science",
        "difficulty": "Medium",
        "q": "Why is the sky blue during the day and red during sunsets?",
        "must_have": ["Rayleigh", "scattering", "wavelength"]
    },
    {
        "id": "sci_02",
        "domain": "Science",
        "difficulty": "Easy",
        "q": "What are Newton's three laws of motion?",
        "must_have": ["inertia", "F = ma", "action", "reaction"]
    },
    {
        "id": "sci_03",
        "domain": "Science",
        "difficulty": "Hard",
        "q": "Explain Einstein's theory of General Relativity and how mass curves spacetime.",
        "must_have": ["spacetime", "curvature", "gravity", "mass"]
    },
    {
        "id": "sci_04",
        "domain": "Science",
        "difficulty": "Medium",
        "q": "What is the difference between nuclear fission and nuclear fusion?",
        "must_have": ["fission", "fusion", "splitting", "combining"]
    },
    {
        "id": "sci_05",
        "domain": "Science",
        "difficulty": "Medium",
        "q": "Explain the first and second laws of thermodynamics.",
        "must_have": ["energy", "conservation", "entropy"]
    },
    {
        "id": "sci_06",
        "domain": "Science",
        "difficulty": "Medium",
        "q": "What causes ocean tides on Earth?",
        "must_have": ["Moon", "gravitational", "tide", "Sun"]
    },
    {
        "id": "sci_07",
        "domain": "Science",
        "difficulty": "Easy",
        "q": "What is the speed of light in a vacuum?",
        "must_have": ["299,792,458", "300,000", "m/s"]
    },
    {
        "id": "sci_08",
        "domain": "Science",
        "difficulty": "Easy",
        "q": "What is absolute zero in Celsius and Kelvin?",
        "must_have": ["-273.15", "0 K"]
    },
    {
        "id": "sci_09",
        "domain": "Science",
        "difficulty": "Medium",
        "q": "How does electromagnetism work and what are Maxwell's equations?",
        "must_have": ["electric", "magnetic", "Maxwell"]
    },
    {
        "id": "sci_10",
        "domain": "Science",
        "difficulty": "Medium",
        "q": "What is Bernoulli's principle and how does it explain aerodynamic lift in airplanes?",
        "must_have": ["pressure", "velocity", "wing", "lift"]
    },
    {
        "id": "sci_11",
        "domain": "Science",
        "difficulty": "Easy",
        "q": "What is the Doppler effect?",
        "must_have": ["frequency", "wavelength", "motion", "observer"]
    },
    {
        "id": "sci_12",
        "domain": "Science",
        "difficulty": "Hard",
        "q": "What is dark matter and dark energy in modern cosmology?",
        "must_have": ["dark matter", "dark energy", "expansion", "universe"]
    },
    {
        "id": "sci_13",
        "domain": "Science",
        "difficulty": "Easy",
        "q": "What are the chemical symbols and atomic numbers of Gold, Iron, and Oxygen?",
        "must_have": ["Au", "79", "Fe", "26", "O", "8"]
    },
    {
        "id": "sci_14",
        "domain": "Science",
        "difficulty": "Medium",
        "q": "How does a laser work and what does the acronym LASER stand for?",
        "must_have": ["Light Amplification", "Stimulated Emission", "Radiation"]
    },
    {
        "id": "sci_15",
        "domain": "Science",
        "difficulty": "Hard",
        "q": "What is Heisenberg's uncertainty principle in quantum mechanics?",
        "must_have": ["position", "momentum", "uncertainty"]
    },
    {
        "id": "sci_16",
        "domain": "Science",
        "difficulty": "Medium",
        "q": "What causes earthquakes and how does plate tectonics work?",
        "must_have": ["tectonic", "fault", "seismic", "lithosphere"]
    },
    {
        "id": "sci_17",
        "domain": "Science",
        "difficulty": "Medium",
        "q": "What is the greenhouse effect and which gases are the primary contributors?",
        "must_have": ["greenhouse", "carbon dioxide", "methane", "infrared"]
    },
    {
        "id": "sci_18",
        "domain": "Science",
        "difficulty": "Medium",
        "q": "How does radioactive decay and half-life work?",
        "must_have": ["half-life", "decay", "nucleus", "isotope"]
    },
    {
        "id": "sci_19",
        "domain": "Science",
        "difficulty": "Easy",
        "q": "What is the difference between kinetic energy and potential energy?",
        "must_have": ["kinetic", "motion", "potential", "stored"]
    },
    {
        "id": "sci_20",
        "domain": "Science",
        "difficulty": "Easy",
        "q": "What is Archimedes' principle of buoyancy?",
        "must_have": ["displaced", "fluid", "buoyant", "weight"]
    },

    # --- 3. Biology & Animals (20) ---
    {
        "id": "bio_01",
        "domain": "Biology",
        "difficulty": "Medium",
        "q": "What is the structure of DNA and what are the four nitrogenous bases?",
        "must_have": ["double helix", "Adenine", "Thymine", "Guanine", "Cytosine"]
    },
    {
        "id": "bio_02",
        "domain": "Biology",
        "difficulty": "Medium",
        "q": "Explain photosynthesis and write its chemical equation.",
        "must_have": ["chlorophyll", "glucose", "oxygen", "carbon dioxide"]
    },
    {
        "id": "bio_03",
        "domain": "Biology",
        "difficulty": "Easy",
        "q": "What is the powerhouse of the cell and what molecule does it produce?",
        "must_have": ["mitochondria", "ATP"]
    },
    {
        "id": "bio_04",
        "domain": "Biology",
        "difficulty": "Easy",
        "q": "What is the largest animal to ever live on Earth?",
        "must_have": ["blue whale"]
    },
    {
        "id": "bio_05",
        "domain": "Biology",
        "difficulty": "Medium",
        "q": "How do vaccines stimulate the human immune system?",
        "must_have": ["antigen", "antibody", "memory", "immune"]
    },
    {
        "id": "bio_06",
        "domain": "Biology",
        "difficulty": "Medium",
        "q": "What is the difference between mitosis and meiosis?",
        "must_have": ["mitosis", "meiosis", "daughter", "gamete"]
    },
    {
        "id": "bio_07",
        "domain": "Biology",
        "difficulty": "Easy",
        "q": "What is the fastest land animal and what speed can it reach?",
        "must_have": ["cheetah", "mph", "km/h"]
    },
    {
        "id": "bio_08",
        "domain": "Biology",
        "difficulty": "Medium",
        "q": "Why and how do chameleons change their color?",
        "must_have": ["chromatophore", "crystal", "temperature", "communication"]
    },
    {
        "id": "bio_09",
        "domain": "Biology",
        "difficulty": "Medium",
        "q": "How does cellular respiration generate energy in living organisms?",
        "must_have": ["glycolysis", "Krebs", "ATP", "mitochondria"]
    },
    {
        "id": "bio_10",
        "domain": "Biology",
        "difficulty": "Easy",
        "q": "What are the defining characteristics of mammals?",
        "must_have": ["hair", "milk", "mammary", "warm-blooded"]
    },
    {
        "id": "bio_11",
        "domain": "Biology",
        "difficulty": "Hard",
        "q": "How do deep sea creatures survive extreme hydrostatic pressure and lack of sunlight?",
        "must_have": ["pressure", "piezolyte", "chemosynthesis", "membrane"]
    },
    {
        "id": "bio_12",
        "domain": "Biology",
        "difficulty": "Hard",
        "q": "What is CRISPR-Cas9 and how is it used in gene editing?",
        "must_have": ["CRISPR", "Cas9", "guide RNA", "cut", "DNA"]
    },
    {
        "id": "bio_13",
        "domain": "Biology",
        "difficulty": "Medium",
        "q": "What are the primary differences between bacteria and viruses?",
        "must_have": ["bacteria", "virus", "cellular", "host", "antibiotics"]
    },
    {
        "id": "bio_14",
        "domain": "Biology",
        "difficulty": "Easy",
        "q": "Which bird is the only bird capable of flying backwards?",
        "must_have": ["hummingbird"]
    },
    {
        "id": "bio_15",
        "domain": "Biology",
        "difficulty": "Medium",
        "q": "Explain Darwin's theory of natural selection and survival of the fittest.",
        "must_have": ["natural selection", "adaptation", "reproductive", "variation"]
    },
    {
        "id": "bio_16",
        "domain": "Biology",
        "difficulty": "Medium",
        "q": "What are enzymes and how do they catalyze biological chemical reactions?",
        "must_have": ["enzyme", "activation energy", "catalyst", "substrate"]
    },
    {
        "id": "bio_17",
        "domain": "Biology",
        "difficulty": "Hard",
        "q": "How do neurons transmit electrical signals through action potentials?",
        "must_have": ["sodium", "potassium", "depolarization", "axon", "action potential"]
    },
    {
        "id": "bio_18",
        "domain": "Biology",
        "difficulty": "Medium",
        "q": "How do migratory birds navigate over thousands of miles during migration?",
        "must_have": ["magnetic", "geomagnetic", "stars", "sun"]
    },
    {
        "id": "bio_19",
        "domain": "Biology",
        "difficulty": "Easy",
        "q": "What are trophic levels in an ecological food chain?",
        "must_have": ["producer", "consumer", "trophic", "energy"]
    },
    {
        "id": "bio_20",
        "domain": "Biology",
        "difficulty": "Easy",
        "q": "How many hearts does an octopus have and what color is its blood?",
        "must_have": ["three", "3", "blue", "hemocyanin"]
    },

    # --- 4. Geography & World Knowledge (20) ---
    {
        "id": "geo_01",
        "domain": "Geography",
        "difficulty": "Easy",
        "q": "How many sovereign countries are in the world today according to the United Nations?",
        "must_have": ["195", "193"]
    },
    {
        "id": "geo_02",
        "domain": "Geography",
        "difficulty": "Easy",
        "q": "What is the capital city of Australia?",
        "must_have": ["Canberra"]
    },
    {
        "id": "geo_03",
        "domain": "Geography",
        "difficulty": "Easy",
        "q": "What is the longest river in the world?",
        "must_have": ["Nile"]
    },
    {
        "id": "geo_04",
        "domain": "Geography",
        "difficulty": "Easy",
        "q": "What is the highest mountain peak above sea level on Earth?",
        "must_have": ["Everest", "8,848"]
    },
    {
        "id": "geo_05",
        "domain": "Geography",
        "difficulty": "Easy",
        "q": "Which country has the largest total land area in the world?",
        "must_have": ["Russia"]
    },
    {
        "id": "geo_06",
        "domain": "Geography",
        "difficulty": "Easy",
        "q": "Which ocean is the largest and deepest on Earth?",
        "must_have": ["Pacific"]
    },
    {
        "id": "geo_07",
        "domain": "Geography",
        "difficulty": "Easy",
        "q": "What is the capital city of Canada?",
        "must_have": ["Ottawa"]
    },
    {
        "id": "geo_08",
        "domain": "Geography",
        "difficulty": "Easy",
        "q": "What is the smallest independent country in the world by both area and population?",
        "must_have": ["Vatican"]
    },
    {
        "id": "geo_09",
        "domain": "Geography",
        "difficulty": "Easy",
        "q": "What is the largest hot desert in the world?",
        "must_have": ["Sahara"]
    },
    {
        "id": "geo_10",
        "domain": "Geography",
        "difficulty": "Easy",
        "q": "What is the capital city of Japan?",
        "must_have": ["Tokyo"]
    },
    {
        "id": "geo_11",
        "domain": "Geography",
        "difficulty": "Medium",
        "q": "Which strait connects the Atlantic Ocean to the Mediterranean Sea?",
        "must_have": ["Gibraltar"]
    },
    {
        "id": "geo_12",
        "domain": "Geography",
        "difficulty": "Easy",
        "q": "What is the capital city of Brazil?",
        "must_have": ["Brasília", "Brasilia"]
    },
    {
        "id": "geo_13",
        "domain": "Geography",
        "difficulty": "Easy",
        "q": "List all seven continents of the world in descending order of land area.",
        "must_have": ["Asia", "Africa", "North America", "South America", "Antarctica", "Europe", "Australia"]
    },
    {
        "id": "geo_14",
        "domain": "Geography",
        "difficulty": "Medium",
        "q": "What is the deepest point in the world's oceans?",
        "must_have": ["Mariana", "Challenger Deep"]
    },
    {
        "id": "geo_15",
        "domain": "Geography",
        "difficulty": "Easy",
        "q": "What is the capital city of Egypt?",
        "must_have": ["Cairo"]
    },
    {
        "id": "geo_16",
        "domain": "Geography",
        "difficulty": "Medium",
        "q": "Which country has the longest coastline in the world?",
        "must_have": ["Canada"]
    },
    {
        "id": "geo_17",
        "domain": "Geography",
        "difficulty": "Medium",
        "q": "What is the de facto capital city of Switzerland?",
        "must_have": ["Bern"]
    },
    {
        "id": "geo_18",
        "domain": "Geography",
        "difficulty": "Easy",
        "q": "What is the official currency of the United Kingdom?",
        "must_have": ["Pound", "Sterling", "GBP"]
    },
    {
        "id": "geo_19",
        "domain": "Geography",
        "difficulty": "Medium",
        "q": "Where is the Amazon Rainforest located and which countries does it span?",
        "must_have": ["South America", "Brazil"]
    },
    {
        "id": "geo_20",
        "domain": "Geography",
        "difficulty": "Medium",
        "q": "Which transcontinental country connects Europe and Asia across the Bosphorus Strait?",
        "must_have": ["Turkey", "Türkiye"]
    },

    # --- 5. Mathematics & Logic (20) ---
    {
        "id": "math_01",
        "domain": "Mathematics",
        "difficulty": "Hard",
        "q": "Find all positive integers x such that x^2 + 2x + 12 is a perfect square. Show a rigorous step-by-step solution.",
        "must_have": ["x = 4", "4"]
    },
    {
        "id": "math_02",
        "domain": "Mathematics",
        "difficulty": "Easy",
        "q": "State the Pythagorean theorem and explain what each variable represents.",
        "must_have": ["a^2 + b^2 = c^2", "hypotenuse", "right triangle"]
    },
    {
        "id": "math_03",
        "domain": "Mathematics",
        "difficulty": "Medium",
        "q": "Find the derivative of f(x) = 3x^4 - 5x^2 + 7x - 9 with respect to x.",
        "must_have": ["12x^3 - 10x + 7", "12x^3", "- 10x"]
    },
    {
        "id": "math_04",
        "domain": "Mathematics",
        "difficulty": "Easy",
        "q": "What is the indefinite integral of 2x with respect to x?",
        "must_have": ["x^2 + C", "x^2"]
    },
    {
        "id": "math_05",
        "domain": "Mathematics",
        "difficulty": "Medium",
        "q": "If two standard six-sided dice are rolled, what is the probability that the sum of the numbers is 7?",
        "must_have": ["1/6", "6/36"]
    },
    {
        "id": "math_06",
        "domain": "Mathematics",
        "difficulty": "Easy",
        "q": "What is the quadratic formula to solve ax^2 + bx + c = 0?",
        "must_have": ["-b", "b^2 - 4ac", "2a"]
    },
    {
        "id": "math_07",
        "domain": "Mathematics",
        "difficulty": "Medium",
        "q": "Solve the system of equations for x and y: 2x + 3y = 13 and x - y = 4.",
        "must_have": ["x = 5", "y = 1"]
    },
    {
        "id": "math_08",
        "domain": "Mathematics",
        "difficulty": "Hard",
        "q": "What is Euler's identity and why is it considered one of the most beautiful equations in mathematics?",
        "must_have": ["e^(i", "pi", "+ 1 = 0"]
    },
    {
        "id": "math_09",
        "domain": "Mathematics",
        "difficulty": "Easy",
        "q": "What is the sum of interior angles in any planar triangle?",
        "must_have": ["180", "pi radians"]
    },
    {
        "id": "math_10",
        "domain": "Mathematics",
        "difficulty": "Easy",
        "q": "What is the formula for the volume of a sphere of radius r?",
        "must_have": ["4/3", "pi", "r^3"]
    },
    {
        "id": "math_11",
        "domain": "Mathematics",
        "difficulty": "Hard",
        "q": "State Bayes' Theorem and write down its mathematical formula.",
        "must_have": ["P(A|B)", "P(B|A)", "P(A)", "P(B)"]
    },
    {
        "id": "math_12",
        "domain": "Mathematics",
        "difficulty": "Medium",
        "q": "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost?",
        "must_have": ["0.05", "5 cents"]
    },
    {
        "id": "math_13",
        "domain": "Mathematics",
        "difficulty": "Easy",
        "q": "What is a prime number and why is 1 not considered a prime number?",
        "must_have": ["prime", "factor", "1", "Fundamental Theorem of Arithmetic"]
    },
    {
        "id": "math_14",
        "domain": "Mathematics",
        "difficulty": "Easy",
        "q": "What is 15 percent of 240?",
        "must_have": ["36"]
    },
    {
        "id": "math_15",
        "domain": "Mathematics",
        "difficulty": "Easy",
        "q": "What is the mathematical recurrence formula for the Fibonacci sequence?",
        "must_have": ["F(n) = F(n-1) + F(n-2)", "F(0)"]
    },
    {
        "id": "math_16",
        "domain": "Mathematics",
        "difficulty": "Hard",
        "q": "Explain the formal epsilon-delta definition of a limit in calculus.",
        "must_have": ["epsilon", "delta", "|x - c|", "|f(x) - L|"]
    },
    {
        "id": "math_17",
        "domain": "Mathematics",
        "difficulty": "Medium",
        "q": "If 5 machines make 5 widgets in 5 minutes, how many minutes do 100 machines take to make 100 widgets?",
        "must_have": ["5 minutes", "5 min"]
    },
    {
        "id": "math_18",
        "domain": "Mathematics",
        "difficulty": "Easy",
        "q": "What is the formula for the area of a circle with radius r?",
        "must_have": ["pi * r^2", "pi r^2", "πr²", "π * r^2"]
    },
    {
        "id": "math_19",
        "domain": "Mathematics",
        "difficulty": "Easy",
        "q": "What is an irrational number? Give three classic examples.",
        "must_have": ["fraction", "ratio", "pi", "sqrt(2)", "e"]
    },
    {
        "id": "math_20",
        "domain": "Mathematics",
        "difficulty": "Easy",
        "q": "What is the factorial of 6 (6!)?",
        "must_have": ["720"]
    }
]


def score_answer(item, answer):
    ans_lower = answer.lower()
    matches = 0
    needed = item["must_have"]
    for needle in needed:
        if needle.lower() in ans_lower:
            matches += 1
    # Check if key answer parts are present
    ratio = matches / len(needed)
    passed = (ratio >= 0.5) or (len(needed) == 1 and ratio == 1.0)
    return passed, ratio, matches, len(needed)


def _temporary_home():
    import atexit

    source = Path(os.environ.get("TENSEI_HOME") or SOURCE)
    db = source / "data" / "tensei.db"
    if not db.is_file():
        raise SystemExit("benchmark database not found: %s (run scripts/prepare_assets.py first)" % db)
    home = Path(tempfile.mkdtemp(prefix="tensei_bench_"))
    (home / "data").mkdir(parents=True, exist_ok=True)
    shutil.copy2(db, home / "data" / "tensei.db")
    brains = source / "brains"
    if brains.is_dir():
        shutil.copytree(brains, home / "brains")
    atexit.register(shutil.rmtree, home, ignore_errors=True)
    os.environ["TENSEI_HOME"] = str(home)
    return home


def run_benchmark():
    home = _temporary_home()
    from tensei import config
    from tensei.memory import Memory
    from tensei.brain import Brain
    from tensei.thinker import Thinker

    config.ensure_dirs()
    mem = Memory()
    brain = Brain(mem)
    thinker = Thinker(mem, brain)

    print("=" * 70)
    print("STARTING TENSEIAI 100-QUESTION BENCHMARK")
    print(f"Total questions: {len(QUESTIONS)} across 5 domains")
    print(f"Temporary home: {home}")
    print("=" * 70)

    results = []
    domain_scores = {}
    gaps = []

    t0 = time.time()
    for idx, item in enumerate(QUESTIONS, 1):
        q = item["q"]
        domain = item["domain"]
        if domain not in domain_scores:
            domain_scores[domain] = {"passed": 0, "total": 0}
        domain_scores[domain]["total"] += 1

        t_start = time.time()
        res = thinker.ask(q)
        duration = time.time() - t_start
        ans = res.get("answer", "")

        passed, ratio, matches, total_need = score_answer(item, ans)
        if passed:
            domain_scores[domain]["passed"] += 1
            status = "PASS"
        else:
            status = "FAIL"
            gaps.append({
                "id": item["id"],
                "domain": domain,
                "q": q,
                "needed": item["must_have"],
                "got_snippet": ans[:200]
            })

        print(f"[{idx:03d}/100] [{status}] ({domain[:4]}) {item['id']}: {q[:55]}... ({duration:.2f}s, {matches}/{total_need})")
        results.append({
            "id": item["id"],
            "domain": domain,
            "difficulty": item["difficulty"],
            "passed": passed,
            "ratio": ratio,
            "duration": duration,
            "mode": res.get("mode", ""),
            "confidence": res.get("confidence", 0.0),
            "answer": ans
        })

    total_passed = sum(1 for r in results if r["passed"])
    overall_acc = (total_passed / len(QUESTIONS)) * 100
    total_time = time.time() - t0

    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS SUMMARY")
    print("=" * 70)
    for dom, score in domain_scores.items():
        pct = (score["passed"] / score["total"]) * 100
        print(f" - {dom:15s}: {score['passed']}/{score['total']} ({pct:.1f}%)")
    print("-" * 70)
    print(f"OVERALL SCORE: {total_passed}/100 ({overall_acc:.1f}%) in {total_time:.1f}s")
    print("=" * 70)

    with open(Path(__file__).resolve().parent / "bench100_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "total_questions": len(QUESTIONS),
            "passed": total_passed,
            "accuracy": overall_acc,
            "time_seconds": total_time,
            "domains": domain_scores,
            "gaps": gaps,
            "results": results
        }, f, indent=2)

    return total_passed, gaps


if __name__ == "__main__":
    run_benchmark()
