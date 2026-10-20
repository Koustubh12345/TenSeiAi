"""TenSeiAi "definitions" pack - clean, verified one-line answers for the
computer-science terms people ask about most.

"Why is this needed?"  Before this pack, "what is python" / "what is java"
matched tutorial and code passages instead of a real definition.  This pack
stores a proper definition-first answer for each subject, as both a memory
passage (for retrieval) and a Q&A pair (teacher://definitions-pack) so the
questions hit instantly with mode "learned".

Usage (from the source directory):
    python tools/seed_definitions.py
"""
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tensei.brain import Brain  # noqa: E402
from tensei.memory import Memory  # noqa: E402

EVIDENCE = [{"url": "teacher://definitions-pack",
             "title": "TenSeiAi curated definitions pack (verified)"}]

DEFS = [
    # ---------- languages ---------------------------------------------------
    ("What is Python?",
     "**Python** is a high-level, general-purpose programming language known for clear, readable syntax. It is interpreted (no separate compile step), supports object-oriented, functional and procedural styles, and ships with a large standard library plus a huge ecosystem of packages. It is widely used for web development, automation, data science and AI."),
    ("What is Java?",
     "**Java** is a high-level, class-based, object-oriented programming language built to run anywhere: source code is compiled to bytecode that executes on the Java Virtual Machine (JVM). It is statically typed, garbage-collected, and widely used for enterprise backends, Android apps and large-scale systems."),
    ("What is JavaScript?",
     "**JavaScript** is a high-level programming language that runs in web browsers and, via Node.js, on servers. It adds interactivity to web pages, powers single-page web apps, and is one of the most widely used languages in the world. It is dynamically typed; TypeScript adds static types on top of it."),
    ("What is TypeScript?",
     "**TypeScript** is JavaScript with static type checking added. You write types and the compiler checks them, then erases them to produce plain JavaScript that any browser or Node.js runtime can run. It catches many bugs at build time and scales better for large codebases."),
    ("What is C?",
     "**C** is a general-purpose, compiled programming language created in the early 1970s for systems programming. It gives direct control over memory and hardware with a small language core, and operating systems such as Linux and Windows are largely written in it."),
    ("What is C++?",
     "**C++** is a compiled, general-purpose programming language built on C with support for objects, templates and generic programming. It combines low-level control with high-level abstractions and is used for games, game engines, desktop software, databases and other performance-critical systems."),
    ("What is C#?",
     "**C#** ('C sharp') is a modern, object-oriented programming language from Microsoft that runs on the .NET runtime. It is statically typed, garbage-collected and used for Windows applications, web services, enterprise software and games built with Unity."),
    ("What is HTML?",
     "**HTML (HyperText Markup Language)** is the standard language for describing the structure of web pages: headings, paragraphs, links, images and forms. Browsers read HTML and render it as the page you see. It describes structure; CSS controls appearance and JavaScript adds behaviour."),
    ("What is CSS?",
     "**CSS (Cascading Style Sheets)** is the language that controls how HTML looks: colours, fonts, spacing, layout, animation and responsive behaviour across screen sizes. Rules target elements with selectors and 'cascade' by specificity and order."),
    ("What is SQL?",
     "**SQL (Structured Query Language)** is the standard language for working with relational databases. It is used to create tables, insert and update rows, filter data with WHERE clauses and join tables together. Common databases using it include PostgreSQL, MySQL, SQLite and SQL Server."),
    ("What is a programming language?",
     "A **programming language** is a formal language for writing instructions a computer can execute. Source code is turned into machine behaviour by a compiler, an interpreter or both, and each language makes different trade-offs in speed, safety and how directly it talks to the hardware."),
    # ---------- software building blocks ------------------------------------
    ("What is a compiler?",
     "A **compiler** translates source code written in one language into another form - usually machine code or bytecode - before the program runs. It reports syntax and type errors at build time and can optimise the result. C, C++ and Rust are typically compiled languages."),
    ("What is an interpreter?",
     "An **interpreter** executes source code directly, line by line, without a separate build step. This makes development fast and portable, at the cost of raw speed compared with compiled code. Python, JavaScript and Ruby use interpreters (often with a compiler inside for speed)."),
    ("What is a variable?",
     "A **variable** is a named storage location in a program that holds a value which can change while the program runs, such as a number, a string or an object. The name is used to read or update the value; its type may be fixed (static typing) or flexible (dynamic typing)."),
    ("What is a function in programming?",
     "A **function** is a named block of code that performs one task and can be called whenever it is needed, optionally taking inputs (arguments) and returning a result. Functions break programs into reusable pieces and avoid repeating the same code."),
    ("What is an array?",
     "An **array** is an ordered collection of values accessed by index, starting at 0 in most languages. Arrays keep elements together in memory so lookups by position are fast; they usually have a fixed size, while resizable cousins are called lists or dynamic arrays."),
    ("What is a data structure?",
     "A **data structure** is a way of organising data in memory so it can be used efficiently. Common ones are arrays and lists (ordered items), hash tables and dictionaries (key-value lookup), stacks and queues (order of processing), and trees and graphs (hierarchies and networks). The right choice is what makes an algorithm fast or slow."),
    ("What is an algorithm?",
     "An **algorithm** is a finite, step-by-step procedure for solving a problem or performing a computation. Sorting a list, finding the shortest route and searching text are classic examples. Algorithms are judged by correctness and by how their time and memory use grow with input size."),
    ("What is a loop in programming?",
     "A **loop** repeats a block of code until a condition is met or a sequence is exhausted. The common forms are the for loop (repeat over items or a known count) and the while loop (repeat while a condition stays true). Loops avoid writing the same instruction many times."),
    # ---------- systems ------------------------------------------------------
    ("What is Linux?",
     "**Linux** is a free, open-source operating system kernel first released by Linus Torvalds in 1991. Combined with tools from the GNU project and other software it forms the Linux operating systems that run most web servers, all Android phones and countless embedded devices."),
    ("What is Android?",
     "**Android** is a mobile operating system developed by Google and based on the Linux kernel. It runs apps written mainly in Kotlin or Java, packaged as APKs or app bundles, on phones, tablets, TVs, watches and car systems."),
    ("What is a database?",
     "A **database** is an organised store of data that can be searched, updated and kept consistent. Relational databases keep data in tables and are queried with SQL; other kinds store documents, key-value pairs, graphs or time series. Most applications keep their durable data in a database."),
    ("What is a server?",
     "A **server** is a computer (or program) that provides a service to other computers over a network: web pages, files, email, game sessions or API responses. It listens for requests on a port, does the work, and sends a response. The same machine can run many servers at once."),
    # ---------- hardware ------------------------------------------------------
    ("What is a CPU?",
     "The **CPU (central processing unit)** is the part of a computer that executes instructions: it fetches them, decodes them and performs arithmetic, logic and control operations. Modern CPUs have several cores and run billions of cycles per second. It is good at doing one thing quickly, rather than thousands at once like a GPU."),
    ("What is a GPU?",
     "A **GPU (graphics processing unit)** is a processor with thousands of small cores designed to perform many similar calculations in parallel. It renders graphics, and because neural-network maths is also massively parallel it is the standard hardware for training and running AI models."),
    ("What is RAM?",
     "**RAM (random-access memory)** is a computer's fast, temporary working memory. Running programs keep their active data in RAM because it is many times faster than a disk, but its contents are lost when the power goes off - persistent data lives on storage such as an SSD."),
    # ---------- software engineering ------------------------------------------
    ("What is a software framework?",
     "A **software framework** is a reusable set of code and rules that provides the structure of an application: you fill in your own parts, and it calls them. Django (web), React (interfaces) and Spring (Java services) are examples. A framework inverts control - it runs the show; a library is just called when you need it."),
    ("What is a software bug?",
     "A **software bug** is a mistake in a program that makes it behave differently from what was intended or specified: a crash, a wrong result, a freeze or a security hole. Bugs come from logic errors, wrong assumptions and edge cases. Finding and fixing them is called debugging."),
    ("What is malware?",
     "**Malware** is software written to harm or exploit: viruses that infect files, worms that spread themselves, trojans that hide inside useful programs, spyware that steals data, ransomware that encrypts files for payment, and adware. Protection means updates, app stores, careful downloads and backups."),
    ("What is the difference between frontend and backend?",
     "The **frontend** is the part of an application users see and interact with - pages, buttons, forms - built with HTML, CSS and JavaScript. The **backend** is the part that runs on servers: business logic, databases and APIs. A developer who does both is called full-stack."),
]


def main():
    t0 = time.time()
    mem = Memory()
    brain = Brain(mem)

    existing = set()
    with mem.lock:
        for (q,) in mem.conn.execute("SELECT question FROM qa"):
            existing.add(re.sub(r"\W+", " ", (q or "").lower()).strip())

    def norm(q):
        return re.sub(r"\W+", " ", q.lower()).strip()

    qa_added = 0
    doc_added = 0
    for q, a in DEFS:
        text = q + " " + re.sub(r"\*\*", "", a)
        ids = mem.add_passages("defs://definitions",
                               "TenSeiAi definitions pack", text,
                               source="defs", topic="definitions")
        doc_added += len(ids)
        nq = norm(q)
        if nq in existing:
            print("skip (already present):", q)
            continue
        existing.add(nq)
        emb = brain.embedder.encode(q)
        mem.add_qa(q, a, EVIDENCE, emb,
                   emb0=brain.embedder.base_encode(q), mode="defs")
        qa_added += 1
    mem.kv_set("defs_pack_v1", {"qa": qa_added, "docs": doc_added,
                                "at": time.time()})
    print("[defs] added %d Q&A pairs, %d passages in %.1fs"
          % (qa_added, doc_added, time.time() - t0))
    print("[defs] memory now:", mem.stats())
    return 0


if __name__ == "__main__":
    sys.exit(main())
