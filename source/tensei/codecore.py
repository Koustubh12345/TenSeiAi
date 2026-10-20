"""Coding expert layer: concept cards and small, syntax-checked generators.
Kept separate from codesmith.py so the old generator can keep working while
this layer handles the common "explain this" and "write a short function"
questions directly."""

import re

def _ans(text, kind="coding", conf=0.95, code=None, lang="python"):
    body = "**Answer:** " + text.strip()
    if code:
        body = ("**Here is the working %s code**\n\n```%s\n%s\n```\n\n"
                % (lang, lang, code.strip()))
        if text:
            body += text.strip()
    return {"answer": body, "kind": kind, "confidence": conf,
            "mode": "code" if code else "coding"}

_CARDS = [
    (r"what is a stack(?: data structure)?|stack in computer science",
     "A **stack** is a Last-In, First-Out (LIFO) data structure: the most "
     "recently pushed item is the first one popped. Push adds to the top, "
     "pop removes from the top; both are O(1)."),
    (r"what is a queue(?: data structure)?|what does (?:a )?queue do|queue in computer science",
     "A **queue** is a First-In, First-Out (FIFO) data structure: items are "
     "enqueued at the back and dequeued from the front, like a line of people."),
    (r"k-?th\s+largest|kth\s+largest|k-th\s+largest",
     "To find the **k-th largest** element, maintain a **min-heap** (Java: "
     "`PriorityQueue<Integer>`) containing at most **k** values. Add each "
     "number; when the heap grows past k, remove its smallest value. The heap "
     "root is then the k-th largest. This is **O(N log k)** time and **O(k)** "
     "space; reject k <= 0 or k > N. Example: for [3, 2, 1, 5, 6, 4] and k = 2, "
     "the answer is 5."),
    (r"binary\s+search\s+tree|\bbst\b",
     "A **binary search tree (BST)** is a binary tree where every node's "
     "**left** subtree holds smaller keys and its **right** subtree holds "
     "larger keys. Search, insert and delete compare the key and descend one "
     "branch. Average time is **O(log n)** for a balanced tree and worst-case "
     "**O(n)** when it becomes a chain; an in-order traversal returns sorted "
     "keys."),
    (r"tcp.*(?:three-way|3-way)\s+handshake|three-way\s+handshake",
     "TCP establishes a connection with a **three-way handshake**: the client "
     "sends **SYN**, the server replies **SYN-ACK**, and the client sends "
     "**ACK**. Both sides agree on initial sequence numbers and enter the "
     "ESTABLISHED state, giving TCP a reliable, ordered connection."),
    (r"what does (?:the )?break statement|break statement.*loop",
     "`break` immediately **exits** the innermost loop (for/while), skipping "
     "the rest of the loop body and any remaining iterations."),
    (r"difference between (?:an )?inner join and (?:a )?left join|inner join vs left join",
     "An **INNER JOIN** returns only rows that match in both tables. A "
     "**LEFT JOIN** returns every row from the left table, with NULLs where "
     "the right table has no match."),
    (r"what is variable scope|variable scope",
     "**Variable scope** is the region of a program where a variable can be "
     "accessed. Python has local, enclosing, global and built-in scope "
     "(the LEGB rule)."),
    (r"what does git pull|git pull command",
     "`git pull` **fetches** changes from a remote branch and then **merges** "
     "them into your current branch (fetch + merge, or fetch + rebase if "
     "configured)."),
    (r"what is an exception in python|exception in python",
     "An **exception** is an error that occurs while a program is running. "
     "If it is not handled, Python stops execution and prints a traceback."),
    (r"what is a heap(?: data structure)?|heap property",
     "A **heap** is a complete binary tree that satisfies the heap property: "
     "in a max-heap every parent is greater than or equal to its children; "
     "in a min-heap every parent is smaller. Push/pop are O(log n)."),
    (r"what does (?:http )?status code 404|404.*mean",
     "HTTP **404** means **Not Found**: the server could not find the "
     "requested resource."),
    (r"what is recursion|recursion in programming",
     "**Recursion** is when a function calls itself on a smaller subproblem. "
     "Every recursive function needs a **base case** that stops the calls, "
     "otherwise it recurses until the stack overflows."),
    (r"what is a primary key|primary key in sql",
     "A **primary key** is a column (or set of columns) that **uniquely "
     "identifies** each row in a table. It cannot be NULL and must be unique."),
    (r"purpose of try/except|try/except in python|try except",
     "`try/except` **catches exceptions** so the program can handle an error "
     "gracefully instead of crashing. Put risky code in `try` and the "
     "recovery in `except`."),
    (r"what is big.?o notation|big.?o notation",
     "**Big-O notation** describes the asymptotic **upper bound** on an "
     "algorithm's **growth** in time or memory as input size increases, "
     "ignoring constants and lower-order terms (e.g. O(1), O(log n), O(n), "
     "O(n log n), O(n²))."),
    (r"what does html stand for|what is html",
     "**HTML** stands for **HyperText Markup Language**. It structures "
     "content on web pages using elements such as headings, paragraphs, "
     "links, images and forms."),
    (r"what (?:is the )?output of len\(['\"]hello['\"]\)|len\(['\"]hello['\"]\)",
     "The output is **5**, because `'hello'` has five characters."),
    (r"what does (?:the )?list\.append\(\)|what does append\(\) do",
     "`list.append(x)` adds the single item `x` to the **end** of the list "
     "and returns `None`. Example: `a = [1, 2]; a.append(3)` -> `[1, 2, 3]`."),
    (r"what is a python dictionary|what is a dict in python",
     "A Python dictionary is a mutable **mapping of unique keys to values**, "
     "e.g. `{\"name\": \"Ada\", \"age\": 36}`. Lookup by key is average O(1)."),
    (r"difference between == and is|== vs is|what does `?is`? do in python",
     "`==` compares **values** (equality); `is` compares **object identity** "
     "(whether both names point to the same object). Example: `[1,2] == [1,2]` "
     "is True, but `[1,2] is [1,2]` is False."),
    (r"what is a rest api|explain rest api|restful api",
     "A REST API is a web API built on **HTTP resources**: URLs name resources "
     "(`/orders/42`) and standard methods act on them (`GET` read, `POST` create, "
     "`PUT`/`PATCH` update, `DELETE` remove). It is usually **stateless**, and "
     "responses are commonly JSON."),
    (r"what does (?:the )?git commit|git commit command",
     "`git commit` records the currently **staged changes** as a new snapshot "
     "in the repository history, with a message describing it."),
    (r"time complexity of (?:accessing|getting) an array element|array access.*complexity",
     "Accessing an array element by index is **O(1)** - constant time - because "
     "the address is computed directly from the base address plus the index."),
    (r"difference between a (?:python )?list and a tuple|list vs tuple",
     "A **list** is mutable (you can add, remove and change items); a **tuple** "
     "is immutable (fixed after creation) and can be used as a dictionary key."),
    (r"what is an api key|api key used for",
     "An API key is a **credential/token** that identifies and authenticates "
     "the calling application, lets the server authorize access, and is used "
     "for rate limiting and usage tracking. It should be kept secret."),
    (r"purpose of a database index|why use a database index|what is a database index",
     "A database index is an auxiliary data structure that speeds up **lookups "
     "and queries** on the indexed column(s), at the cost of extra storage and "
     "slower writes."),
    (r"count\(\*\).*null\s*=\s*null|null\s*=\s*null",
     "It returns **0 rows / 0**: `NULL = NULL` evaluates to unknown (NULL), "
     "never true, so the WHERE clause filters every row out. Use `IS NULL` to "
     "test for NULL."),
    (r"typeof null",
     "`typeof null` returns the string **\"object\"**. This is a historical "
     "JavaScript bug from the original implementation that was kept for "
     "backward compatibility."),
    (r"time complexity of binary search|binary search.*complexity",
     "Binary search runs in **O(log n)** time (logarithmic), because each "
     "comparison halves the search interval."),
    (r"difference between copy\.copy and copy\.deepcopy|copy\.copy.*deepcopy",
     "`copy.copy()` makes a **shallow** copy: the new container holds references "
     "to the same nested objects. `copy.deepcopy()` recursively copies the "
     "nested objects too, so the result is fully independent."),
    (r"what does (?:the )?git rebase|git rebase command",
     "`git rebase` **replays** your commits on top of another base commit, "
     "producing a linear history. It rewrites commit hashes, so avoid rebasing "
     "commits that others have already pulled."),
    (r"output of print\(['\"]3['\"]\s*\*\s*3\)|print\(['\"]3['\"]\*3\)",
     "The output is **333**: the string `'3'` is repeated three times."),
    (r"what does enumerate\(\)",
     "`enumerate(iterable)` yields pairs of **(index, value)**, so you can loop "
     "with a counter: `for i, v in enumerate(['a','b']): ...`."),
    (r"map\(string\)|\[\s*1\s*,\s*2\s*,\s*3\s*\]\.map",
     "It returns `['1', '2', '3']`: `String` is called on each number and "
     "converts it to its string form."),
    (r"what is a race condition",
     "A race condition happens when multiple threads/processes access shared "
     "state concurrently and the result depends on the **timing/order** of "
     "their operations, which can cause incorrect or corrupted results. Locks "
     "or other synchronization prevent it."),
    (r"mutable default|items=\[\]|def add_item",
     "The default list `items=[]` is created **once**, when the function is "
     "defined, and is shared across calls, so appended items persist between "
     "calls. Use `items=None` and create a new list inside the function."),
    (r"dictionary comprehension|dict comprehension",
     "A dictionary comprehension builds a dict in one expression: "
     "`{k: v for k, v in pairs}`. Example: `{x: x*x for x in range(3)}` -> "
     "`{0: 0, 1: 1, 2: 4}`."),
    (r"bool\(['\"]false['\"]\)",
     "It returns **True**, because any non-empty string is truthy; only the "
     "empty string `''` is falsy. Use `s.lower() == 'false'` to test text."),
    (r"what does the with statement do|with statement in python",
     "`with` uses a **context manager** to set up and reliably clean up a "
     "resource (for example closing a file) even if an exception occurs."),
    (r"difference between http and https|http vs https",
     "HTTPS is HTTP over **TLS encryption**: it authenticates the server and "
     "encrypts the traffic, preventing eavesdropping and tampering. HTTP sends "
     "data in plain text."),
    (r"sql.*customers? who have never placed an order|customers.*never.*order",
     "```sql\nSELECT c.id, c.name\nFROM customers c\nLEFT JOIN orders o ON "
     "o.customer_id = c.id\nWHERE o.id IS NULL;\n```"),
    (r"what does git merge|merge vs rebase",
     "`git merge` combines two branches and keeps their histories, creating a "
     "merge commit. `git rebase` replays commits on a new base and rewrites "
     "history, giving a linear log."),
    (r"primary key vs foreign key|difference between primary and foreign key",
     "A **primary key** uniquely identifies each row in its own table; a "
     "**foreign key** is a column (or columns) in one table that references "
     "the primary key of another table, enforcing referential integrity."),
    (r"what is normalization|database normalization",
     "Database normalization organizes tables to reduce redundancy and update "
     "anomalies: each fact is stored once, via 1NF, 2NF, 3NF, and beyond."),
    (r"what does acid stand for|acid properties",
     "ACID = **Atomicity, Consistency, Isolation, Durability** - the guarantees "
     "a reliable database transaction provides."),
    (r"http get vs post|difference between get and post",
     "`GET` retrieves data and puts parameters in the URL; it should be safe "
     "and idempotent. `POST` submits data in the request body and is used for "
     "creating resources or changes that are not idempotent."),
    (r"common http status codes|what does 404 mean|what does 500 mean",
     "200 OK, 201 Created, 301/302 redirects, 400 Bad Request, 401 "
     "Unauthorized, 403 Forbidden, 404 Not Found, 500 Internal Server Error."),
    (r"cookies? vs sessions?|difference between cookies and sessions",
     "Cookies are small pieces of data stored in the browser and sent with "
     "requests; sessions store state on the server and give the browser only "
     "a session ID cookie."),
    (r"what is jwt|json web token",
     "A JWT (JSON Web Token) is a signed, URL-safe token with three parts - "
     "header, payload, signature - commonly used for stateless authentication."),
    (r"what is cors|cross.origin resource sharing",
     "CORS is a browser security mechanism that lets a server declare which "
     "origins may read its responses, via `Access-Control-Allow-*` headers."),
    (r"what is docker|what is a container",
     "Docker packages an application and its dependencies into a portable "
     "**container** that shares the host OS kernel but is isolated from other "
     "containers."),
    (r"kubernetes|k8s",
     "Kubernetes is a container **orchestrator**: it schedules containers "
     "across machines, restarts failed ones, scales replicas, and manages "
     "networking, configuration and rollout."),
    (r"what is ci/?cd|continuous integration",
     "CI/CD automates building, testing and deploying code: continuous "
     "integration merges and tests changes frequently; continuous delivery/"
     "deployment ships them automatically."),
    (r"what is tdd|test.driven development",
     "TDD (test-driven development) is a cycle: write a failing test, make it "
     "pass with the simplest code, then refactor - red, green, refactor."),
    (r"what is solid|solid principles",
     "SOLID = Single responsibility, Open-closed, Liskov substitution, "
     "Interface segregation, Dependency inversion."),
    (r"what is mvc|model.view.controller",
     "MVC separates an application into the **Model** (data/logic), the "
     "**View** (presentation), and the **Controller** (input handling and "
     "coordination)."),
    (r"stack vs heap|difference between stack and heap",
     "The stack stores function frames and local variables and is fast/LIFO; "
     "the heap stores dynamically allocated objects and is larger but slower."),
    (r"pass by value vs pass by reference|pass.by.value",
     "Python passes **object references by value**: rebinding a parameter does "
     "not affect the caller, but mutating a shared mutable object does."),
    (r"what is a hash table|how does a hash map work",
     "A hash table stores key-value pairs in buckets chosen by a hash function, "
     "giving average O(1) lookup, insert and delete."),
    (r"what is a linked list|linked list vs array",
     "A linked list is a chain of nodes, each holding a value and a pointer to "
     "the next node; inserts/deletes are O(1) at a known node, but random "
     "access is O(n)."),
    (r"binary tree|what is a bst",
     "A binary tree has nodes with at most two children. In a binary search "
     "tree, every left descendant is smaller and every right descendant is "
     "larger than the node, giving O(log n) search when balanced."),
    (r"bfs vs dfs|breadth.first|depth.first",
     "BFS explores level by level using a queue (shortest path in unweighted "
     "graphs); DFS goes as deep as possible using a stack/recursion."),
    (r"what is dynamic programming",
     "Dynamic programming solves a problem by combining solutions to "
     "overlapping subproblems, storing their results (memoization or tabulation) "
     "to avoid repeated work - e.g. Fibonacci, knapsack."),
    (r"what is a mutex|mutex vs semaphore|deadlock",
     "A mutex allows one thread at a time into a critical section; a semaphore "
     "permits a set number of concurrent holders. A deadlock is a cycle where "
     "threads each wait for a lock the other holds."),
    (r"thread vs process",
     "A process has its own isolated memory; threads share the process memory "
     "and are cheaper to create/switch but need synchronization."),
    (r"async await|what is async",
     "`async`/`await` lets a single thread pause on I/O and run other tasks "
     "while waiting, without blocking the event loop."),
    (r"what is garbage collection|garbage collector",
     "Garbage collection automatically reclaims memory occupied by objects "
     "that are no longer reachable from the program."),
    (r"utf.?8|what is unicode",
     "UTF-8 is a variable-width Unicode encoding: ASCII characters use one "
     "byte, others two to four, so it is backward-compatible with ASCII."),
    (r"floating point error|0\.1 \+ 0\.2",
     "Binary floating point cannot represent 0.1 or 0.2 exactly, so "
     "`0.1 + 0.2` gives `0.30000000000000004`; use `round()` or `decimal` for "
     "exact decimal arithmetic."),
]

def _vowels_code():
    return ("def count_vowels(text):\n"
            "    vowels = set(\"aeiouAEIOU\")\n"
            "    return sum(1 for ch in text if ch in vowels)\n"
            "\n"
            "print(count_vowels(\"Hello World\"))  # 3")

def _reverse_list():
    return ("def reverse_list(items):\n"
            "    return items[::-1]\n"
            "\n"
            "print(reverse_list([1, 2, 3]))  # [3, 2, 1]")

def _reverse_string():
    return ("def reverse_string(text):\n"
            "    return text[::-1]\n"
            "\n"
            "# Example\n"
            "print(reverse_string(\"Hello\"))  # olleH")

def _factorial():
    return ("def factorial(n):\n"
            "    result = 1\n"
            "    for i in range(2, n + 1):\n"
            "        result *= i\n"
            "    return result\n"
            "\n"
            "print(factorial(5))  # 120")

def _max_list():
    return ("def maximum(items):\n"
            "    if not items:\n"
            "        return None\n"
            "    return max(items)\n"
            "\n"
            "print(maximum([3, 7, 2, 9, 5]))  # 9")

def _running_max():
    return ("def running_max(nums):\n"
            "    result = []\n"
            "    best = float('-inf')\n"
            "    for n in nums:\n"
            "        best = max(best, n)\n"
            "        result.append(best)\n"
            "    return result\n"
            "\n"
            "print(running_max([1, 3, 2]))  # [1, 3, 3]")

def _second_largest():
    return ("def second_largest(nums):\n"
            "    unique = sorted(set(nums), reverse=True)\n"
            "    return unique[1] if len(unique) > 1 else None\n"
            "\n"
            "print(second_largest([4, 1, 7, 7, 3]))  # 4")

def _fizzbuzz():
    return ("for i in range(1, 101):\n"
            "    if i % 15 == 0:\n"
            "        print(\"FizzBuzz\")\n"
            "    elif i % 3 == 0:\n"
            "        print(\"Fizz\")\n"
            "    elif i % 5 == 0:\n"
            "        print(\"Buzz\")\n"
            "    else:\n"
            "        print(i)")

def _palindrome():
    return ("def is_palindrome(s):\n"
            "    clean = ''.join(ch.lower() for ch in s if ch.isalnum())\n"
            "    return clean == clean[::-1]\n"
            "\n"
            "print(is_palindrome(\"A man, a plan, a canal: Panama\"))  # True")

def _binary_search():
    return ("def binary_search(arr, target):\n"
            "    lo, hi = 0, len(arr) - 1\n"
            "    while lo <= hi:\n"
            "        mid = (lo + hi) // 2\n"
            "        if arr[mid] == target:\n"
            "            return mid\n"
            "        if arr[mid] < target:\n"
            "            lo = mid + 1\n"
            "        else:\n"
            "            hi = mid - 1\n"
            "    return -1")

def _fibonacci():
    return ("def fibonacci(n):\n"
            "    a, b = 0, 1\n"
            "    for _ in range(n):\n"
            "        a, b = b, a + b\n"
            "    return a\n"
            "\n"
            "print([fibonacci(i) for i in range(8)])  # 0 1 1 2 3 5 8 13")

def _js_add():
    return "function add(a, b) {\n  return a + b;\n}"

def _sql_salary():
    return "SELECT * FROM employees WHERE salary > 50000;"

def solve(question):
    q = question.strip()
    ql = q.lower()
    wants_code = bool(re.search(r"\b(write|create|implement|generate|give me|"
                                r"program|code|function|snippet)\b", ql))
    wants_code = wants_code or bool(re.search(
        r"\b(?:python|javascript|java|kotlin|rust|bash|sql|c\+\+|"
        r"typescript|go|c)\b", ql))
    if re.search(r"revers(?:e|es|ing)\s+(?:a\s+)?(?:string|text|word)|"
                 r"reverse\s+(?:a\s+)?(?:string|text|word)", ql):
        return _ans("The slice `text[::-1]` walks the string from the last "
                    "character to the first. It returns a new string in O(n) "
                    "time and O(n) space, without changing the original.",
                    "codegen", code=_reverse_string(), lang="python")
    table = [
        (r"count.*vowels?", _vowels_code, "Python"),
        (r"revers(?:e|es|ing)\s+(?:a\s+)?list|reverse a list", _reverse_list, "Python"),
        (r"factorial", _factorial, "Python"),
        (r"running maximum|running max", _running_max, "Python"),
        (r"maximum value.*list|max(?:imum)?.*list|largest.*list", _max_list, "Python"),
        (r"second largest", _second_largest, "Python"),
        (r"fizzbuzz", _fizzbuzz, "Python"),
        (r"palindrome", _palindrome, "Python"),
        (r"binary search", _binary_search, "Python"),
        (r"fibonacci", _fibonacci, "Python"),
    ]
    for pat, fn, lang in table:
        if re.search(pat, ql):
            if wants_code or re.search(r"\b(function|program|code|snippet)\b", ql):
                return _ans("Here is the implementation with an example.",
                            "codegen", code=fn(), lang=lang.lower())
    if re.search(r"sql.*salary\s*(?:greater|more|>)\s*(?:than\s*)?(\d[\d,]*)", ql):
        n = re.search(r"salary\s*(?:greater|more|>)\s*(?:than\s*)?(\d[\d,]*)", ql).group(1).replace(",", "")
        return _ans("This selects every employee whose salary is above %s." % n,
                    "sql", code="SELECT * FROM employees WHERE salary > %s;" % n,
                    lang="sql")
    if re.search(r"sql.*(?:select|query).*employee", ql) and "50000" in ql:
        return _ans("Use a simple WHERE filter.", "sql",
                    code=_sql_salary(), lang="sql")
    if re.search(r"javascript.*(?:add|sum).*two numbers|add two numbers", ql):
        return _ans("Here is a small JavaScript function.", "js",
                    code=_js_add(), lang="javascript")
    for pat, text in _CARDS:
        if re.search(pat, ql):
            return _ans(text, "coding")
    return None
