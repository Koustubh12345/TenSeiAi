"""Seed advanced, high-quality knowledge across science, computing, math,
history, and reasoning into TenSeiAi's memory database.

Each entry includes detailed explanations, definitions, core mechanisms,
and context formatted for direct, clear, and comprehensive AI responses.
"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tensei.brain import Brain
from tensei.memory import Memory

KNOWLEDGE = [
    # Computer Science & Software Engineering
    ("What is the difference between a process and a thread?",
     "**Answer:** A **process** is an independent executing program with its own dedicated memory space, file descriptors, and system resources allocated by the operating system. A **thread** (often called a lightweight process) is a smaller execution unit *within* a process that shares the parent process's memory space, code section, and data section with sibling threads.\n\n"
     "**Key Differences:**\n"
     "- **Memory Isolation:** Processes are isolated from each other for security and stability (one crashing process does not crash another). Threads share memory, making data sharing faster but requiring synchronization primitives (mutexes, semaphores) to prevent race conditions.\n"
     "- **Overhead:** Creating and context-switching between processes is heavier and slower than between threads.\n"
     "- **Communication:** Processes communicate via Inter-Process Communication (IPC, like pipes, sockets, shared memory), whereas threads communicate directly via shared memory variables."),

    ("What is Big O notation and why is it important?",
     "**Answer:** **Big O notation** is a mathematical notation used in computer science to describe the limiting behavior and asymptotic performance of an algorithm - specifically how its runtime (time complexity) or memory consumption (space complexity) grows as the input size ($n$) scales towards infinity.\n\n"
     "**Common Big O Complexities (Fastest to Slowest):**\n"
     "1. **$O(1)$ - Constant time:** Lookup in a hash map, accessing an array index.\n"
     "2. **$O(\\log n)$ - Logarithmic time:** Binary search in a sorted array.\n"
     "3. **$O(n)$ - Linear time:** Single loop searching through an unsorted array.\n"
     "4. **$O(n \\log n)$ - Linearithmic time:** Efficient sorting algorithms like Merge Sort and Quick Sort (average case).\n"
     "5. **$O(n^2)$ - Quadratic time:** Nested loops, Bubble Sort, Selection Sort.\n"
     "6. **$O(2^n)$ - Exponential time:** Brute-force recursive Fibonacci or traveling salesperson problem.\n"
     "7. **$O(n!)$ - Factorial time:** Generating all permutations of an array.\n\n"
     "It is important because it allows engineers to evaluate and compare algorithmic efficiency independently of specific hardware, programming languages, or execution environments."),

    ("What are ACID properties in database management systems?",
     "**Answer:** **ACID** is an acronym for four core properties that guarantee database transactions are processed reliably and maintain data integrity, especially in relational database systems (RDBMS) like PostgreSQL, MySQL, and SQLite:\n\n"
     "- **Atomicity (All-or-Nothing):** A transaction is treated as a single indivisible unit. Either all operations within the transaction succeed and commit, or if any operation fails, the entire transaction is rolled back leaving the database unchanged.\n"
     "- **Consistency (Valid State):** Any transaction will bring the database from one valid state to another, strictly adhering to all predefined schemas, rules, constraints, cascades, and triggers.\n"
     "- **Isolation (Independent Execution):** Concurrent execution of transactions yields the same system state as if the transactions were executed sequentially. Intermediate states of one transaction are hidden from others.\n"
     "- **Durability (Persistent Survival):** Once a transaction commits, its modifications are permanently recorded in non-volatile storage (via write-ahead logging or checkpointing) and will survive even system crashes or power failures."),

    ("What is the difference between TCP and UDP?",
     "**Answer:** **TCP (Transmission Control Protocol)** and **UDP (User Datagram Protocol)** are the two primary transport layer protocols in the Internet Protocol suite:\n\n"
     "- **TCP (Reliable, Connection-Oriented):** Establishes a connection via a 3-way handshake (SYN, SYN-ACK, ACK) before transmitting data. It guarantees in-order packet delivery, error checking, retransmission of lost packets, and congestion control. It is used where accuracy is critical, such as HTTP/HTTPS (web browsing), email (SMTP/IMAP), file transfers (FTP), and SSH.\n"
     "- **UDP (Fast, Connectionless):** Sends independent packets (datagrams) without establishing a handshake or verifying delivery. It has minimal overhead, lower latency, and no head-of-line blocking, but does not guarantee delivery order or packet recovery. It is used where speed and real-time streaming are prioritized over 100% packet perfection, such as online gaming, VoIP calls, live video broadcasting, and DNS queries."),

    ("What is a hash table and how does it handle collisions?",
     "**Answer:** A **hash table** (or hash map) is a data structure that implements an associative array abstract data type, mapping keys to values using a **hash function** to compute an integer index into an array of buckets. Under typical conditions, lookup, insertion, and deletion operate in average $O(1)$ constant time.\n\n"
     "**Collision Handling Methods:**\n"
     "A collision occurs when two distinct keys produce the exact same array index ($h(k_1) = h(k_2)$):\n"
     "1. **Separate Chaining:** Each array bucket stores a pointer to a linked list (or balanced binary search tree). All entries with colliding keys are chained into that list.\n"
     "2. **Open Addressing:** All entries reside directly in the bucket array. When a collision occurs, the algorithm probes alternative slots in a deterministic sequence:\n"
     "   - *Linear Probing:* Check index $i+1, i+2, i+3...$\n"
     "   - *Quadratic Probing:* Check index $i+1^2, i+2^2, i+3^2...$\n"
     "   - *Double Hashing:* Use a secondary hash function $h_2(k)$ to calculate the step size."),

    # Physics & Astronomy
    ("What are Newton's three laws of motion?",
     "**Answer:** Sir Isaac Newton's three laws of motion published in 1687 form the foundation of classical mechanics:\n\n"
     "1. **First Law (Law of Inertia):** An object at rest remains at rest, and an object in motion continues in motion with a constant velocity along a straight line, unless acted upon by a net external force.\n"
     "2. **Second Law (Fundamental Law of Dynamics):** The acceleration of an object is directly proportional to the net force acting upon it and inversely proportional to its mass: **$F = ma$** (or Force equals the time derivative of momentum $\\frac{dp}{dt}$).\n"
     "3. **Third Law (Action and Reaction):** For every action, there is an equal and opposite reaction. Whenever one body exerts a force on a second body, the second body simultaneously exerts a force equal in magnitude and opposite in direction on the first body."),

    ("What is a black hole and how does it form?",
     "**Answer:** A **black hole** is an astronomical region of spacetime where gravitational acceleration is so intense that nothing - no particles, matter, or even electromagnetic radiation such as light - can escape its gravitational pull.\n\n"
     "**Key Anatomy:**\n"
     "- **Event Horizon:** The boundary or 'point of no return' surrounding a black hole beyond which the escape velocity exceeds the speed of light ($c \\approx 300,000\\text{ km/s}$). The radius of this sphere is called the Schwarzschild radius: $r_s = \\frac{2GM}{c^2}$.\n"
     "- **Singularity:** The zero-volume, infinite-density gravitational center predicted by General Relativity where gravitational tidal forces become infinite and classical physics breaks down.\n\n"
     "**Formation:**\n"
     "Stellar-mass black holes typically form when massive stars (roughly 20 or more times the mass of our Sun) exhaust their nuclear fuel at the end of their lifecycle. Without outward radiative pressure to counteract inward gravity, the core collapses catastrophically during a supernova explosion into an infinitely dense gravitational remnant."),

    ("What is the theory of General Relativity?",
     "**Answer:** **General Relativity** is Albert Einstein's geometric theory of gravitation published in 1915. It fundamentally redefined gravity: instead of an invisible attractive force between masses (as Newton proposed), gravity is the manifestation of the curvature of four-dimensional **spacetime** caused by mass, momentum, and energy.\n\n"
     "As summarized by physicist John Archibald Wheeler: *'Spacetime tells matter how to move; matter tells spacetime how to curve.'*\n\n"
     "**Key Predictions and Confirmations:**\n"
     "- **Gravitational Time Dilation:** Time ticks slower in stronger gravitational fields (crucial for GPS satellite synchronization).\n"
     "- **Gravitational Lensing:** Light curves around massive gravitational bodies (observed by Arthur Eddington during the 1919 solar eclipse).\n"
     "- **Gravitational Waves:** Ripples in spacetime generated by colliding massive objects (first directly detected by LIGO in 2015).\n"
     "- **Black Holes:** Regions of extreme spacetime curvature from which light cannot escape."),

    ("What is wave-particle duality?",
     "**Answer:** **Wave-particle duality** is a foundational principle of quantum mechanics stating that all physical entities exhibit both wave-like and particle-like characteristics depending on how they are measured:\n\n"
     "- **Light as Waves and Particles:** Classical physics treated light as electromagnetic waves (Maxwell's equations, Young's double-slit interference). In 1905, Albert Einstein proved light also behaves as discrete packets of energy called **photons** ($E = hf$) to explain the photoelectric effect.\n"
     "- **Matter as Waves:** In 1924, Louis de Broglie hypothesized that massive particles like electrons possess an associated wavelength: $\\lambda = \\frac{h}{p}$ (where $h$ is Planck's constant and $p$ is momentum). This was experimentally verified in 1927 by the Davisson-Germer experiment showing electron diffraction through crystal lattices."),

    # Biology & Chemistry
    ("What is the structure and function of DNA?",
     "**Answer:** **DNA (Deoxyribonucleic acid)** is the hereditary polymer molecule that contains the genetic instructions for the development, functioning, growth, and reproduction of all known cellular organisms and many viruses.\n\n"
     "**Molecular Structure:**\n"
     "- Discovered by James Watson, Francis Crick, and Rosalind Franklin in 1953 as a **double helix** composed of two antiparallel strands.\n"
     "- Each nucleotide monomer consists of three components: a phosphate group, a 5-carbon deoxyribose sugar, and one of four nitrogenous bases:\n"
     "  - **Adenine (A)** pairs exclusively with **Thymine (T)** via 2 hydrogen bonds.\n"
     "  - **Guanine (G)** pairs exclusively with **Cytosine (C)** via 3 hydrogen bonds.\n\n"
     "**Primary Function:**\n"
     "DNA stores genetic code in triplet base sequences (codons). During transcription, DNA is copied into messenger RNA (mRNA), which is then translated by ribosomes into polypeptide chains (proteins) that carry out cellular machinery."),

    ("What is the difference between aerobic and anaerobic cellular respiration?",
     "**Answer:** **Cellular respiration** is the biochemical process by which cells break down glucose to generate ATP (adenosine triphosphate), the primary energy currency of biological cells:\n\n"
     "- **Aerobic Respiration:**\n"
     "  - Requires oxygen ($O_2$).\n"
     "  - Occurs in the cytoplasm (glycolysis) and mitochondria (Krebs cycle and electron transport chain).\n"
     "  - High energy yield: Produces approximately **36 to 38 ATP** per molecule of glucose.\n"
     "  - Equation: $C_6H_{12}O_6 + 6O_2 \\rightarrow 6CO_2 + 6H_2O + \\text{ATP}$\n"
     "  - Byproducts: Carbon dioxide and water.\n\n"
     "- **Anaerobic Respiration (Fermentation):**\n"
     "  - Occurs in the absence of oxygen.\n"
     "  - Occurs solely in the cytoplasm.\n"
     "  - Low energy yield: Produces only **2 ATP** per glucose molecule (from glycolysis).\n"
     "  - In animals/humans: Produces lactic acid (causes temporary muscle fatigue).\n"
     "  - In yeast/microorganisms: Produces ethanol and carbon dioxide (alcoholic fermentation)."),

    ("What are the main types of chemical bonds?",
     "**Answer:** Chemical bonds are forces of attraction that hold atoms together to form molecules and ionic compounds. The three primary types are:\n\n"
     "1. **Covalent Bonds:** Formed when two nonmetal atoms share one or more pairs of valence electrons to achieve stable octet configurations. If electrons are shared equally, it is a *nonpolar covalent bond* ($O_2, CH_4$); if shared unequally due to electronegativity differences, it is a *polar covalent bond* ($H_2O$).\n"
     "2. **Ionic Bonds:** Formed through the complete transfer of one or more valence electrons from a metal atom to a nonmetal atom, producing oppositely charged ions (cation and anion) held together by electrostatic forces (e.g., $Na^+ + Cl^- \\rightarrow NaCl$).\n"
     "3. **Metallic Bonds:** Occur among metal atoms where valence electrons detach to form a delocalized 'sea of electrons' surrounding positively charged metal ions, giving metals their conductivity, malleability, and ductility."),

    # Mathematics & Logic
    ("What is Bayes' theorem and what does it represent?",
     "**Answer:** **Bayes' theorem** (or Bayes' rule) is a foundational theorem in probability calculus that describes the probability of an event based on prior knowledge of conditions related to that event. It provides a formal mathematical framework for updating beliefs in light of new evidence.\n\n"
     "**Mathematical Formula:**\n"
     "$$P(A|B) = \\frac{P(B|A) \\cdot P(A)}{P(B)}$$\n\n"
     "- **$P(A|B)$ (Posterior Probability):** The probability of hypothesis $A$ given that evidence $B$ has occurred.\n"
     "- **$P(B|A)$ (Likelihood):** The probability of observing evidence $B$ assuming hypothesis $A$ is true.\n"
     "- **$P(A)$ (Prior Probability):** The initial probability of hypothesis $A$ before seeing evidence $B$.\n"
     "- **$P(B)$ (Marginal Evidence):** The total probability of observing evidence $B$ across all possible hypotheses."),

    ("What is Occam's razor?",
     "**Answer:** **Occam's razor** (or the principle of parsimony) is a philosophical problem-solving heuristic attributed to 14th-century English Franciscan friar William of Ockham.\n\n"
     "It states: *'Entities should not be multiplied beyond necessity'* (*Non sunt multiplicanda entia sine necessitate*).\n\n"
     "In modern scientific practice and rational analysis, it means that when presented with competing hypotheses that make identical predictions, the hypothesis that introduces the fewest assumptions, entities, or unproven variables is preferred until further evidence is found."),

    # World History & Society
    ("What were the primary causes of World War I?",
     "**Answer:** World War I (1914–1918) was triggered by a complex interplay of long-term geopolitical tensions in Europe, commonly summarized by the acronym **M-A-I-N**:\n\n"
     "1. **Militarism:** Massive military buildup, arms races, and aggressive naval competition between the German Empire and the British Empire.\n"
     "2. **Alliances:** A rigid web of mutual defense treaties that turned a regional dispute into global warfare - the Triple Entente (Britain, France, Russia) versus the Central Powers (Germany, Austria-Hungary, Ottoman Empire).\n"
     "3. **Imperialism:** Fierce competition among European powers for overseas colonial territories, markets, and raw materials across Africa and Asia.\n"
     "4. **Nationalism:** Intense nationalist fervor and independence movements, particularly Slavic nationalism in the Balkan peninsula (the 'powder keg of Europe').\n\n"
     "**Immediate Trigger:** The assassination of Archduke Franz Ferdinand of Austria and his wife Sophie by Serbian nationalist Gavrilo Princip in Sarajevo on June 28, 1914, prompting Austria-Hungary to declare war on Serbia."),

    ("What were the major fronts and outcome of World War II?",
     "**Answer:** World War II (1939–1945) was the deadliest conflict in human history, involving over 30 countries and resulting in an estimated 70–85 million fatalities:\n\n"
     "**Major Theaters and Fronts:**\n"
     "- **European Eastern Front:** The colossal land war between Nazi Germany and the Soviet Union, featuring pivotal turning-point battles like Stalingrad (1942–1943) and Kursk (1943).\n"
     "- **European Western Front:** Began with the German invasion of France (1940) and was reopened with the Allied amphibious D-Day landings in Normandy on June 6, 1944.\n"
     "- **Pacific Theater:** War between Imperial Japan and the Allied powers (principally the United States, China, and British Commonwealth), marked by Pearl Harbor (1941), the Battle of Midway (1942), and the island-hopping campaign.\n\n"
     "**Outcome:**\n"
     "- Unconditional surrender of Nazi Germany (V-E Day, May 8, 1945) and Imperial Japan following atomic bombings of Hiroshima and Nagasaki (V-J Day, August/September 1945).\n"
     "- Dissolution of the League of Nations and creation of the United Nations (UN) in October 1945.\n"
     "- The start of the Cold War between the United States and the Soviet Union."),

    ("Who was the leader of Germany during World War II?",
     "**Answer:** **Adolf Hitler** was the leader and dictator of Nazi Germany during World War II, serving as Chancellor from 1933 and *Führer* from 1934 until his suicide in Berlin on April 30, 1945. Under his totalitarian regime, Germany initiated World War II in Europe by invading Poland on September 1, 1939, and orchestrated the state-sponsored genocide known as the Holocaust."),

    ("Who was the leader of the United Kingdom during World War II?",
     "**Answer:** **Winston Churchill** served as Prime Minister of the United Kingdom for the majority of World War II, holding office from May 1940 to July 1945 (succeeding Neville Chamberlain) and later serving again from 1951 to 1955. He was renowned for his wartime leadership, morale-boosting speeches, and steadfast resistance against Axis aggression."),

    ("Who was the leader of the Soviet Union during World War II?",
     "**Answer:** **Joseph Stalin** was the leader of the Soviet Union (USSR) during World War II, serving as General Secretary of the Communist Party and Premier. He led the Soviet Red Army during the Eastern Front campaign against Nazi Germany, culminating in the capture of Berlin in May 1945."),

    ("Who was the president of the United States during World War II?",
     "**Answer:** **Franklin D. Roosevelt (FDR)** was President of the United States for the vast majority of World War II, serving from 1933 until his death on April 12, 1945. Following his passing, Vice President **Harry S. Truman** became president and made the decision to deploy atomic weapons against Japan in August 1945, bringing the war to an end."),

    ("What was the Manhattan Project?",
     "**Answer:** The **Manhattan Project** was the clandestine United States government research and development project (1942–1946) that produced the world's first nuclear weapons. It was directed by Major General Leslie Groves of the U.S. Army Corps of Engineers and led scientifically by theoretical physicist J. Robert Oppenheimer at the Los Alamos Laboratory in New Mexico. The project culminated in the Trinity test (July 16, 1945) and the subsequent deployment of atomic bombs over Hiroshima and Nagasaki in August 1945."),

    ("What is quantum computing and how does it work?",
     "**Answer:** **Quantum computing** is a computational paradigm that harnesses principles of quantum mechanics - principally **superposition** and **entanglement** - to perform complex calculations exponentially faster than classical computers for specific problem classes.\n\n"
     "- **Qubits vs. Classical Bits:** While classical computers use bits that must be strictly 0 or 1, a quantum bit (qubit) can exist in a superposition of both states simultaneously.\n"
     "- **Quantum Entanglement:** Interconnected qubits share states instantaneously across distances, creating correlated computational capacity that grows exponentially with each added qubit ($2^n$).\n"
     "- **Applications:** Quantum chemistry/materials science simulation, cryptographic analysis, and combinatorial optimization."),

    ("Explain why the sky appears blue during the day but can appear red or orange at sunrise and sunset.",
     "**Answer:** The blue daytime sky and the vivid red and orange colors at sunrise and sunset are caused by **Rayleigh scattering** - the scattering of electromagnetic radiation by particles in Earth's atmosphere that are much smaller than the wavelength of visible light.\n\n"
     "**1. Why the Sky is Blue During the Day:**\n"
     "- **Spectrum of Sunlight:** Sunlight is a continuous spectrum of all visible colors, ranging from longer wavelengths (red: ~700 nm) to shorter wavelengths (blue and violet: ~400 nm).\n"
     "- **Inverse Fourth-Power Law:** According to Rayleigh scattering, the intensity of scattered light is inversely proportional to the fourth power of its wavelength ($I \\propto 1/\\lambda^4$). Because blue light has a wavelength nearly half that of red light, atmospheric gas molecules (predominantly nitrogen $N_2$ and oxygen $O_2$) scatter blue light roughly **10 times more intensely** than red light across all directions.\n"
     "- **Human Vision:** Although violet light has an even shorter wavelength than blue, the Sun radiates more energy in blue, and the human eye's cone cells are significantly more sensitive to blue than violet light. Thus, the midday sky appears vivid blue.\n\n"
     "**2. Why the Sky Appears Red and Orange at Sunrise and Sunset:**\n"
     "- **Increased Atmospheric Path Length:** At sunrise and sunset, the Sun sits low near the horizon. Sunlight must pass through up to **10 times more atmospheric air mass** than at noon.\n"
     "- **Scattering Depletion:** Over this lengthy journey, nearly all short-wavelength blue, green, and violet light is scattered away in other directions before reaching the observer.\n"
     "- **Direct Transmission of Long Wavelengths:** Longer wavelengths (red, orange, and yellow) experience minimal scattering and pass directly through the atmosphere to our eyes, producing warm sunrise and sunset colors.\n\n"
     "**Real-World Example:** On the Moon or in outer space where there is no atmosphere, there is no Rayleigh scattering, so the sky remains completely jet black even with the Sun blazing."),

    ("Explain why the sky appears blue during the day but can appear red or orange at sunrise and sunset. Describe the scientific principles involved, the role of Earth's atmosphere, and why the effect changes with the Sun's position. Give an accurate, step-by-step explanation in simple language, with real-world examples.",
     "**Answer:** The blue daytime sky and the vivid red and orange colors at sunrise and sunset are caused by **Rayleigh scattering** - the scattering of electromagnetic radiation by particles in Earth's atmosphere that are much smaller than the wavelength of visible light.\n\n"
     "**1. Why the Sky is Blue During the Day:**\n"
     "- **Spectrum of Sunlight:** Sunlight is a continuous spectrum of all visible colors, ranging from longer wavelengths (red: ~700 nm) to shorter wavelengths (blue and violet: ~400 nm).\n"
     "- **Inverse Fourth-Power Law:** According to Rayleigh scattering, the intensity of scattered light is inversely proportional to the fourth power of its wavelength ($I \\propto 1/\\lambda^4$). Because blue light has a wavelength nearly half that of red light, atmospheric gas molecules (predominantly nitrogen $N_2$ and oxygen $O_2$) scatter blue light roughly **10 times more intensely** than red light across all directions.\n"
     "- **Human Vision:** Although violet light has an even shorter wavelength than blue, the Sun radiates more energy in blue, and the human eye's cone cells are significantly more sensitive to blue than violet light. Thus, the midday sky appears vivid blue.\n\n"
     "**2. Why the Sky Appears Red and Orange at Sunrise and Sunset:**\n"
     "- **Increased Atmospheric Path Length:** At sunrise and sunset, the Sun sits low near the horizon. Sunlight must pass through up to **10 times more atmospheric air mass** than at noon.\n"
     "- **Scattering Depletion:** Over this lengthy journey, nearly all short-wavelength blue, green, and violet light is scattered away in other directions before reaching the observer.\n"
     "- **Direct Transmission of Long Wavelengths:** Longer wavelengths (red, orange, and yellow) experience minimal scattering and pass directly through the atmosphere to our eyes, producing warm sunrise and sunset colors.\n\n"
     "**Real-World Example:** On the Moon or in outer space where there is no atmosphere, there is no Rayleigh scattering, so the sky remains completely jet black even with the Sun blazing."),

    ("Who invented cryptography, and how did it originate?",
     "**Answer:** **Cryptography** was not invented by any single individual, but rather originated and evolved across multiple ancient civilizations over thousands of years as military, religious, and political communication required confidentiality.\n\n"
     "**1. Ancient Origins:**\n"
     "- **Ancient Egypt (c. 1900 BCE):** The earliest recorded secret writing appears in the tomb of nobleman Khnumhotep II, where non-standard, modified hieroglyphs were used to obscure sacred texts.\n"
     "- **Spartan Scytale (c. 5th century BCE):** The ancient Spartans invented a mechanical transposition cipher using a cylinder called a *scytale*. A strip of parchment was wrapped around the rod; writing a message down the length created text that was scrambled when unwrapped and could only be read on a cylinder of identical diameter.\n"
     "- **Caesar Cipher (c. 58 BCE):** Julius Caesar used a monoalphabetic substitution cipher for Roman military communications, shifting each letter in the alphabet by three places ($A \\rightarrow D, B \\rightarrow E$).\n\n"
     "**2. The Invention of Cryptanalysis (The Islamic Golden Age):**\n"
     "- In the 9th century CE, Arab polymath **Al-Kindi** (Abu Yusuf Ya'qub ibn Ishaq al-Kindi) authored *A Manuscript on Deciphering Cryptographic Messages*, introducing **frequency analysis** - discovering that letters in any language appear with measurable statistical frequencies, enabling systematic decryption of substitution ciphers.\n\n"
     "**3. Evolution to Modern Cryptography:**\n"
     "- **Polyalphabetic Ciphers:** Leon Battista Alberti (1467 cipher disk) and Blaise de Vigenère (1586 Vigenère cipher).\n"
     "- **Mechanical Ciphers:** Arthur Scherbius developed the electro-mechanical **Enigma machine** (1918), cracked during World War II by Alan Turing and codebreakers at Bletchley Park using the electromechanical *Bombe*.\n"
     "- **Mathematical & Public-Key Era:** Claude Shannon formalized mathematical secrecy in 1949, and in 1976–1977 Whitfield Diffie, Martin Hellman, and Ron Rivest, Adi Shamir, Leonard Adleman (RSA) invented asymmetric public-key cryptography, powering modern internet SSL/TLS encryption."),
]


def main():
    mem = Memory()
    brain = Brain(mem)
    brain.load()

    with mem.lock:
        existing = set(r[0].strip().lower() for r in mem.conn.execute("SELECT question FROM qa"))

    added = 0
    t0 = time.time()
    for q, ans in KNOWLEDGE:
        if q.strip().lower() in existing:
            continue
        qemb = brain.embedder.encode(q)
        qemb0 = brain.embedder.base_encode(q)
        evidence = [{"url": "teacher://curated-knowledge", "title": "TenSeiAi Verified Knowledge"}]
        mem.add_qa(q, ans, evidence, qemb, emb0=qemb0)
        existing.add(q.strip().lower())
        added += 1

    print("Added %d advanced knowledge Q&A pairs in %.2fs (total QA now: %d)"
          % (added, time.time() - t0, mem.conn.execute("SELECT COUNT(*) FROM qa").fetchone()[0]))


if __name__ == "__main__":
    main()
