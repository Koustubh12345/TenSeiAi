"""TenSeiAi "coding" pack - the programming questions people ask AI assistants most.

Covers Python, JavaScript, HTML/CSS, SQL, Git, algorithms and the classic
beginner errors, with short verified answers and working snippets.

Usage:
    python tools/seed_code_pack.py            # add data
    python tools/seed_code_pack.py --train    # add data + retrain the brain
"""
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tensei.brain import Brain  # noqa: E402
from tensei.memory import Memory  # noqa: E402

EVIDENCE = [{"url": "teacher://code-pack",
             "title": "TenSeiAi curated coding pack (verified)"}]

CODE = [
    # ---------- Python basics ------------------------------------------------
    ("How do I print in Python?",
     "Use print(): `print(\"Hello, world!\")`. To join values: `print(\"x =\", x)`. For formatted output use f-strings: `print(f\"x = {x:.2f}\")`."),
    ("How do I take input in Python?",
     "`name = input(\"Your name: \")` returns a **string**. For a number convert it: `age = int(input(\"Age: \"))` or `float(...)`."),
    ("How do I write a comment in Python?",
     "Start the line with `#`: `# this is a comment`. For multi-line documentation use a docstring: `\"\"\"Docstring\"\"\"` as the first statement of a function, class or module."),
    ("How do I make a list in Python?",
     "`nums = [1, 2, 3]`, `names = list()`, or a comprehension: `squares = [n*n for n in range(10)]`. Access with `nums[0]`; append with `nums.append(4)`; length is `len(nums)`."),
    ("How do I make a dictionary in Python?",
     "`user = {\"name\": \"Ada\", \"age\": 36}`. Read: `user[\"name\"]` (KeyError if missing) or safely `user.get(\"name\", \"unknown\")`. Add/update: `user[\"city\"] = \"London\"`. Loop: `for k, v in user.items():`."),
    ("How do I loop through a list in Python?",
     "`for item in items:`. With index: `for i, item in enumerate(items):`. Both index and list: `for i in range(len(items)):` but enumerate is cleaner. While loops: `while condition:`."),
    ("How do I write a function in Python?",
     "```python\ndef greet(name, greeting=\"Hello\"):\n    \"\"\"Return a greeting.\"\"\"\n    return f\"{greeting}, {name}!\"\n\nprint(greet(\"Ada\"))  # Hello, Ada!\n```\nDefault arguments make parameters optional."),
    ("How do I use if/elif/else in Python?",
     "```python\nif score >= 90:\n    grade = \"A\"\nelif score >= 80:\n    grade = \"B\"\nelse:\n    grade = \"C\"\n```\nIndentation (4 spaces) defines the blocks; no braces needed."),
    ("How do I use f-strings in Python?",
     "Prefix the string with f and put expressions in braces: `f\"{name} is {age} years old\"`. Formatting: `f\"{price:.2f}\"` (2 decimals), `f\"{rate:.1%}\"` (percent), `f\"{n:>10}\"` (right-align width 10), `f\"{x=}\"` (shows `x=42`)."),
    ("How do I read a file in Python?",
     "```python\nwith open(\"data.txt\", \"r\", encoding=\"utf-8\") as f:\n    text = f.read()          # whole file\n# or line by line:\nwith open(\"data.txt\") as f:\n    for line in f:\n        print(line.rstrip())\n```\n`with` closes the file automatically, even on errors."),
    ("How do I write a file in Python?",
     "```python\nwith open(\"out.txt\", \"w\", encoding=\"utf-8\") as f:\n    f.write(\"hello\\n\")\n```\nMode `\"w\"` overwrites, `\"a\"` appends, `\"w\"`+`json.dump` for JSON. Always pass `encoding=\"utf-8\"` for text."),
    ("How do I handle errors in Python?",
     "```python\ntry:\n    n = int(text)\nexcept ValueError as e:\n    print(\"not a number:\", e)\n    n = 0\nfinally:\n    print(\"done\")\n```\nCatch the specific exception you expect; bare `except:` hides real bugs."),
    ("How do I use a list comprehension?",
     "`[x*x for x in range(5)]` -> `[0, 1, 4, 9, 16]`. With a condition: `[x for x in nums if x % 2 == 0]`. With if/else: `[\"even\" if x%2==0 else \"odd\" for x in nums]`. Dict version: `{k: v for k, v in pairs}`."),
    ("How do I sort a list in Python?",
     "`nums.sort()` sorts in place; `sorted(nums)` returns a new list. Descending: `sorted(nums, reverse=True)`. By key: `items.sort(key=lambda t: t[1])`. Sort dicts by a field: `people.sort(key=lambda p: p[\"age\"])`. For mixed case text: `key=str.lower`."),
    ("How do I reverse a string in Python?",
     "`text[::-1]`. As a function: `def reverse(s): return s[::-1]`. Reversing a list also works: `nums[::-1]` (or `nums.reverse()` in place)."),
    ("How do I check if a string contains a substring?",
     "`if \"cat\" in text:` - case-sensitive. Case-insensitive: `if \"cat\" in text.lower():`. Position: `text.find(\"cat\")` returns -1 when absent; `text.index` raises instead."),
    ("How do I split and join strings in Python?",
     "`parts = \"a,b,c\".split(\",\")` -> `['a', 'b', 'c']`. Join: `\", \".join(parts)`. Split on whitespace (any amount): `text.split()`. Strip whitespace: `text.strip()`."),
    ("How do I remove duplicates from a list in Python?",
     "Keep order: `list(dict.fromkeys(items))`. Unordered: `list(set(items))`. For dicts by a key: build a dict keyed by the field: `{d[\"id\"]: d for d in rows}.values()`."),
    ("How do I define a class in Python?",
     "```python\nclass Dog:\n    def __init__(self, name):\n        self.name = name\n\n    def speak(self):\n        return f\"{self.name} says woof\"\n\nd = Dog(\"Rex\")\nprint(d.speak())\n```\n`__init__` is the constructor; `self` is the instance."),
    ("What is inheritance in Python?",
     "A class can extend another: `class Puppy(Dog):` inherits its methods. Override by redefining; call the parent version with `super().speak()`. Use inheritance for real 'is-a' relationships; prefer plain composition otherwise."),
    ("How do I import a module in Python?",
     "`import math` then `math.sqrt(9)`. Or `from math import sqrt` then `sqrt(9)`. Your own files: `from mymodule import myfunc` if the file `mymodule.py` is in the same folder or on sys.path. Avoid `from module import *`."),
    ("How do I install a package in Python?",
     "`pip install requests` (or `python -m pip install requests` if pip is not on PATH). Install for the current project in a virtual environment: `python -m venv .venv`, activate it, then pip install. Freeze versions with `pip freeze > requirements.txt`."),
    ("What is a virtual environment and why use one?",
     "A private folder of packages for one project. Create: `python -m venv .venv`; activate: Windows `.venv\\\\Scripts\\\\activate`, macOS/Linux `source .venv/bin/activate`; then `pip install`. It stops project A's package versions from breaking project B."),
    ("What does if __name__ == '__main__' mean?",
     "That block runs only when the file is executed directly, not when the file is imported as a module. It is how a file can act both as a library and as a script:\n```python\ndef main():\n    ...\n\nif __name__ == \"__main__\":\n    main()\n```"),
    ("How do I check the type of a variable in Python?",
     "`type(x)` gives the exact class; `isinstance(x, (int, float))` tests compatibility (preferred, works with subclasses). For debugging: `print(type(x), x)` or `print(repr(x))`."),
    ("How do I convert types in Python?",
     "`int(\"42\")`, `float(\"3.5\")`, `str(42)`, `bool(0)` (False), `list(\"abc\")` -> `['a','b','c']`. These raise ValueError on bad input - wrap in try/except when parsing user data."),
    ("How do I do math in Python?",
     "Operators: `+ - * / //` (integer divide) `%` (remainder) `**` (power). `//` and `/` differ: `7//2 == 3`, `7/2 == 3.5`. For functions: `import math; math.sqrt(16), math.pi`. For arrays: numpy."),
    ("How do I generate a random number in Python?",
     "```python\nimport random\nrandom.random()          # 0..1 float\nrandom.randint(1, 6)    # dice roll, inclusive\nrandom.choice([\"a\",\"b\"]) # pick one\nrandom.shuffle(cards)   # in place\n# reproducible:\nrng = random.Random(42)\n```\nFor security-sensitive tokens use the `secrets` module instead."),
    ("How do I get the current date and time in Python?",
     "`from datetime import datetime; now = datetime.now()`. Format: `now.strftime(\"%Y-%m-%d %H:%M\")`. Parse: `datetime.strptime(\"2026-05-01\", \"%Y-%m-%d\")`. For time zones use `datetime.now(timezone.utc)`."),
    ("How do I work with JSON in Python?",
     "```python\nimport json\nobj = json.loads('{\"a\": 1}')      # string -> dict\ntext = json.dumps(obj, indent=2)   # dict -> string\nwith open(\"f.json\", encoding=\"utf-8\") as fh:\n    data = json.load(fh)\n```"),
    ("How do I read a CSV file in Python?",
     "```python\nimport csv\nwith open(\"people.csv\", newline=\"\", encoding=\"utf-8\") as f:\n    for row in csv.DictReader(f):\n        print(row[\"name\"])\n```\nFor heavy data work use `pandas.read_csv` instead."),
    ("How do I use regex in Python?",
     "```python\nimport re\nre.match(r\"\\\\d+\", text)          # match at start\nre.search(r\"\\\\d+\", text)         # anywhere\nre.findall(r\"\\\\w+@\\\\w+\\\\.\\\\w+\", text)\nre.sub(r\"\\\\s+\", \" \", text)       # replace\n```\nUse raw strings (r\"...\") so backslashes survive. Compile patterns used in loops: `pat = re.compile(...)`."),
    ("How do I write a lambda in Python?",
     "`double = lambda x: x * 2`. Lambdas are single-expression anonymous functions, mostly used as sort keys or inside map/filter: `sorted(words, key=lambda w: len(w))`. For anything longer use a normal `def`."),
    ("What are *args and **kwargs?",
     "They collect extra arguments: `def f(*args, **kwargs):` puts positional extras in the tuple `args` and keyword extras in the dict `kwargs`. Useful for wrappers. Unpack the other way too: `f(*[1,2])`, `g(**{\"x\": 1})`."),
    ("What is a generator in Python?",
     "A function that uses `yield` to produce values lazily, one at a time:\n```python\ndef countdown(n):\n    while n > 0:\n        yield n\n        n -= 1\n```\nIt uses almost no memory for huge sequences; loop over it with `for x in countdown(5):`."),
    ("What is a decorator in Python?",
     "A function that wraps another to add behaviour:\n```python\nimport functools\ndef logged(fn):\n    @functools.wraps(fn)\n    def wrapper(*a, **k):\n        print(\"calling\", fn.__name__)\n        return fn(*a, **k)\n    return wrapper\n```\nUse with `@logged` above the function. Flask routes and pytest fixtures are decorators."),
    ("How do I use type hints in Python?",
     "```python\ndef total(nums: list[int]) -> int:\n    return sum(nums)\n\nname: str | None = None\n```\nHints document intent and power IDEs; Python does not enforce them at runtime. Check them with `mypy` if you want enforcement."),
    ("How do I write a test in Python?",
     "With unittest (built in):\n```python\nimport unittest\nfrom mymath import add\n\nclass TestAdd(unittest.TestCase):\n    def test_adds(self):\n        self.assertEqual(add(2, 3), 5)\n\nif __name__ == \"__main__\":\n    unittest.main()\n```\nRun with `python -m unittest`. pytest is the popular alternative: `def test_add(): assert add(2,3) == 5`."),
    ("How do I measure how long code takes in Python?",
     "```python\nimport time\nstart = time.perf_counter()\nwork()\nprint(f\"took {time.perf_counter()-start:.3f}s\")\n```\nFor tiny snippets use `python -m timeit`. Profile real programs with `python -m cProfile -s cumtime app.py`."),
    ("How do I run a Python script?",
     "`python script.py` (Windows) or `python3 script.py` (Linux/macOS). Make it runnable by path on Linux: add `#!/usr/bin/env python3` on line 1, then `chmod +x script.py` and run `./script.py`."),
    ("What is the difference between a list and a tuple?",
     "Lists are mutable - `a = [1, 2]`, `a.append(3)`. Tuples are immutable - `t = (1, 2)`, fixed size, hashable (usable as dict keys). Use tuples for records you won't change, lists for collections that grow."),
    ("What is the difference between == and is in Python?",
     "`==` compares values: `[1,2] == [1,2]` is True. `is` compares identity (same object): `a is b`. Use `is` only for `None`, `True`, `False` - never to compare numbers or strings."),
    ("How do I merge two dictionaries in Python?",
     "`merged = {**a, **b}` or `merged = a | b` (3.9+). Later keys win. To merge without overwriting existing: `merged = {**b, **a}`. For lists of dicts: pandas or a manual loop groupby."),
    ("How do I use map and filter in Python?",
     "`list(map(str, [1, 2]))` -> `['1','2']`; `list(filter(lambda x: x > 2, [1,2,3]))` -> `[3]`. Comprehensions usually read better: `[str(x) for x in nums]`, `[x for x in nums if x > 2]`."),
    ("What is pip and how do I use it?",
     "pip is Python's package installer. `pip install package`, `pip install package==1.2.3`, `pip uninstall package`, `pip list`, `pip freeze > requirements.txt`, `pip install -r requirements.txt`. If 'pip not recognized' use `python -m pip` instead."),
    ("How do I make an HTTP request in Python?",
     "```python\nimport requests\nr = requests.get(\"https://api.github.com\", timeout=10)\nr.raise_for_status()\ndata = r.json()\n```\nPOST JSON: `requests.post(url, json={\"a\": 1}, timeout=10)`. Always set a timeout; the standard library alternative is `urllib.request`."),
    ("How do I scrape a web page in Python?",
     "Fetch with requests, parse with BeautifulSoup (`pip install beautifulsoup4`):\n```python\nimport requests\nfrom bs4 import BeautifulSoup\nhtml = requests.get(url, timeout=10).text\nsoup = BeautifulSoup(html, \"html.parser\")\nfor h in soup.select(\"h2\"):\n    print(h.get_text(strip=True))\n```\nRespect robots.txt and terms of service; prefer official APIs when they exist."),
    ("What is an f-string vs .format?",
     "f-strings are the modern way: `f\"{name} scored {score:.1f}\"`. `.format` still appears in older code: `\"{} scored {:.1f}\".format(name, score)`. Both beat `%` formatting for readability; use f-strings in new code."),
    ("How do I copy a list or dict in Python?",
     "Shallow: `list(b)`, `dict(d)`, `b = a[:]`. Deep (nested structures): `import copy; c = copy.deepcopy(a)`. Assignment `b = a` shares the same object - changing one changes 'both'."),
    ("How do I find the largest or smallest item in Python?",
     "`max(nums)`, `min(nums)`. With a key: `max(words, key=len)`. Index of the max: `nums.index(max(nums))` or `max(range(len(nums)), key=nums.__getitem__)`. Top 3: `sorted(nums)[-3:]` or `heapq.nlargest(3, nums)`."),
    ("How do I do integer division and modulo in Python?",
     "`divmod(17, 5)` gives `(3, 2)` - quotient and remainder together. `17 // 5 == 3`, `17 % 5 == 2`. Check even/odd: `n % 2 == 0`. Time formatting: `mins, secs = divmod(seconds, 60)`."),
    ("How do I check if a file exists in Python?",
     "```python\nfrom pathlib import Path\np = Path(\"data.txt\")\nif p.exists():\n    ...\n```\npathlib is the modern way to join, read and inspect paths: `p = Path(\"folder\") / \"file.txt\"`."),
    ("How do I create a folder in Python?",
     "```python\nfrom pathlib import Path\nPath(\"out/reports\").mkdir(parents=True, exist_ok=True)\n```\n`parents=True` creates missing parents; `exist_ok=True` prevents an error when it already exists."),
    ("How do I pass command line arguments in Python?",
     "```python\nimport argparse\np = argparse.ArgumentParser()\np.add_argument(\"name\")\np.add_argument(\"--count\", type=int, default=1)\na = p.parse_args()\nprint(a.name * a.count)\n```\nRun: `python app.py Ada --count 3`. Quick and dirty: `sys.argv[1:]`."),

    # ---------- classic errors ----------------------------------------------
    ("How do I fix NameError: name is not defined?",
     "Python saw a name it does not know. Causes: a typo (`pritn`), using a variable before assigning it, or calling a function defined later in the file at import time. Fix the spelling, define/assign before use, and check the traceback line number - it tells you exactly where."),
    ("How do I fix IndentationError?",
     "Python blocks must share the same indentation (4 spaces is standard). You mixed tabs and spaces or misaligned a block. In VS Code: enable 'render whitespace', convert tabs to spaces, and re-check the lines above the error - the mistake is often one line earlier."),
    ("How do I fix TypeError: 'NoneType' object is not subscriptable?",
     "Something returned None and you indexed or called it - e.g. `result = thing.get(\"x\")` was None, then `result[\"y\"]`. Add a check (`if result is None: ...`) or a default (`result = thing.get(\"x\", {})`) and find why the value was missing."),
    ("How do I fix ModuleNotFoundError?",
     "The module is not installed (or is not on the path). Install: `pip install module-name`. If it installed but still fails, you are probably running a different Python/venv - check `python -c \"import sys; print(sys.executable)\"` and install with `python -m pip`. Your own file: run from the project folder or add it to sys.path."),
    ("How do I fix IndexError: list index out of range?",
     "You asked for an element that does not exist. Valid indices for a list of length n are 0..n-1. Check with `if i < len(items):` or iterate directly (`for x in items:`). Off-by-one classic: `range(1, len(items)+1)` should usually be `range(len(items))`."),
    ("How do I fix KeyError in a dictionary?",
     "The key does not exist. Use `d.get(key, default)` when a miss is normal, `if key in d:` before indexing, or catch it: `except KeyError:`. When building, `d.setdefault(key, []).append(x)` avoids repeated lookups. The traceback shows the missing key."),
    ("How do I fix ValueError in Python?",
     "Something had the right type but the wrong value - `int(\"abc\")`, unpacking the wrong count, etc. Convert defensively: `try: n = int(s) except ValueError: n = 0`, or validate first (`if s.isdigit():`). The message usually names the value."),
    ("How do I fix SyntaxError?",
     "Python could not parse the file. Check the reported line and the one before it: missing colon after if/for/def, unclosed bracket/quote, `=` instead of `==` in a comparison, or a stray comma. An editor with bracket matching finds it fastest."),
    ("How do I fix AttributeError?",
     "You called a method or attribute the object does not have - often because the variable is None or a different type than you think. Print `type(obj)` right before the failing line, check spelling (`len()` not `length()`), and make sure the object was created as expected."),
    ("How do I fix 'command not found: python' or 'pip is not recognized'?",
     "Python is not on the PATH for this shell. Windows: reinstall with 'Add Python to PATH' checked, or use the `py` launcher (`py -3 script.py`) and `py -m pip`. macOS/Linux: use `python3`/`pip3` or install via your package manager. Verify with `python --version` in a NEW terminal after installing."),
    ("How do I fix RecursionError: maximum recursion depth exceeded?",
     "A function keeps calling itself without reaching the base case. Add or fix the stopping condition, make sure the recursive call moves toward it (n-1, smaller list), and convert deep loops to iteration. Python's default limit is 1000 - raising it (`sys.setrecursionlimit`) is a bandage, not a fix."),
    ("How do I fix ZeroDivisionError?",
     "You divided by zero. Guard it: `avg = total / count if count else 0`, or `if d != 0:`. For floats returning NumPy, use `np.divide(a, b, out=np.zeros_like(a), where=b!=0)`."),
    ("How do I fix FileNotFoundError?",
     "The path is wrong or relative to a different working directory than you expect. Print `os.getcwd()` and the full path you build; use `pathlib.Path(__file__).parent / \"file.txt\"` for files next to your script, and check case/spelling on Linux."),
    ("How do I fix 'Permission denied' when installing or saving?",
     "You hit a protected location. Do NOT `sudo pip install` (breaks system Python) - use a virtual environment. For file saves: pick a user folder, or fix ownership/permissions (`chmod`). On Windows, closed files (Excel has the CSV open!) or antivirus locks are common causes of saves failing silently."),
    ("How do I fix UnicodeDecodeError?",
     "The file is not UTF-8 (or you opened binary data as text). Open with the right encoding: `open(path, encoding=\"utf-8\", errors=\"replace\")`, or guess: latin-1 never fails (but can garble). Detect properly with `chardet` when unknown."),
    ("How do I fix 'unexpected indent'?",
     "The line is indented more than the surrounding block without a reason (stray space at the start of the line, or leftover code moved out of a block). Re-indent that line to match its block, and check blank lines with hidden spaces."),
    ("How do I fix circular import in Python?",
     "Two modules import each other. Fix by moving the shared pieces into a third module, importing inside the function that needs it (lazy import), or importing the module (`import b`) instead of names (`from b import x`). Usually it is a sign one module should not depend on the other."),
    ("How do I fix 'RuntimeError: dictionary changed size during iteration'?",
     "You modified a dict while looping over it. Iterate over a copy: `for k in list(d):` then delete/update, or collect changes and apply after the loop. Same for lists and sets - build a new list with a comprehension when possible."),

    # ---------- JavaScript ---------------------------------------------------
    ("How do I write JavaScript in an HTML page?",
     "Inside `<script>` tags, usually just before `</body>`:\n```html\n<script>\n  document.getElementById(\"out\").textContent = \"Hello\";\n</script>\n```\nFor a file: `<script src=\"app.js\" defer></script>` - `defer` runs it after the HTML is parsed."),
    ("How do I print to the console in JavaScript?",
     "`console.log(\"value:\", value)`. Other levels: `console.warn`, `console.error`, `console.table(arrayOfObjects)`. Open DevTools (F12) > Console to see it."),
    ("What is the difference between let, const and var?",
     "`const` = cannot be reassigned (still mutable inside for objects). `let` = reassignable, block-scoped. `var` = the old keyword: function-scoped, hoisted, avoid it. Default: `const`, switch to `let` only when you must reassign."),
    ("How do I write a function in JavaScript?",
     "Classic: `function add(a, b) { return a + b; }`. Arrow: `const add = (a, b) => a + b;`. Arrow functions are shorter but do not have their own `this` - use classic functions for object methods that need `this`."),
    ("How do I make an HTTP request in JavaScript?",
     "```javascript\nconst res = await fetch(\"https://api.example.com/data\");\nif (!res.ok) throw new Error(res.status);\nconst data = await res.json();\n```\nInside an `async` function. POST: `fetch(url, {method: \"POST\", headers: {\"Content-Type\": \"application/json\"}, body: JSON.stringify(obj)})`."),
    ("How do I use async and await in JavaScript?",
     "Mark the function `async`, then `await` promises inside it:\n```javascript\nasync function load() {\n  try {\n    const data = await getData();\n  } catch (err) {\n    console.error(err);\n  }\n}\n```\nRun independent calls together with `await Promise.all([a(), b()])`."),
    ("How do I loop through an array in JavaScript?",
     "`for (const item of items) {}` for values; `for (const [i, item] of items.entries())` with index. Functional style: `items.forEach(x => ...)`, `items.map(x => x*2)`, `items.filter(x => x > 2)`, `items.reduce((sum, x) => sum + x, 0)`."),
    ("How do I add or remove an element from an array in JavaScript?",
     "Add end: `a.push(x)`; start: `a.unshift(x)`. Remove end: `a.pop()`; start: `a.shift()`. Remove by value: `a = a.filter(v => v !== x)`; by index: `a.splice(i, 1)`. Check existence: `a.includes(x)`."),
    ("How do I check if a variable is null or undefined in JavaScript?",
     "Both falsey: `if (!x)` catches 0 and '' too. Exactly: `x === null`, `x === undefined`, or `x == null` (loose equality matches both). Optional chaining: `user?.address?.city` avoids the error entirely. Nullish default: `const n = count ?? 0`."),
    ("How do I convert a string to a number in JavaScript?",
     "`Number(\"42\")` (strict), `parseInt(\"42px\")` -> 42, `parseFloat(\"3.14\")`, or unary plus `+str`. `Number(\"\")` is 0; `Number(\"abc\")` is NaN - check with `Number.isNaN(x)`."),
    ("How do I format a date in JavaScript?",
     "Modern: `new Date().toLocaleDateString(\"en-GB\", {year: \"numeric\", month: \"long\", day: \"numeric\"})` -> '5 May 2026'. ISO string: `new Date().toISOString()`. For serious date math/time zones use a library like date-fns or Luxon."),
    ("How do I add an event listener in JavaScript?",
     "`document.querySelector(\"#btn\").addEventListener(\"click\", () => { alert(\"hi\"); })`. Form: listen for `submit` and call `e.preventDefault()` to stop the page reload. Input: `input` event fires on every keystroke."),
    ("How do I store data in the browser?",
     "`localStorage.setItem(\"key\", JSON.stringify(obj))` persists until cleared; `sessionStorage` lasts for the tab; cookies get sent to the server. Read back: `JSON.parse(localStorage.getItem(\"key\") ?? \"null\")`. Never store tokens you cannot afford to leak in localStorage."),
    ("What is JSON and how do I use it in JavaScript?",
     "JSON is a text format for data: `{\"name\": \"Ada\", \"age\": 36}`. Convert: `JSON.stringify(obj)` to send/store, `JSON.parse(text)` to read. JSON only allows double quotes, no trailing commas, no comments."),
    ("How do I handle errors in JavaScript?",
     "```javascript\ntry {\n  risky();\n} catch (err) {\n  console.error(err.message);\n} finally {\n  cleanup();\n}\n```\nAsync: `.catch(...)` on promises or try/catch inside async/await. Throw your own with `throw new Error(\"message\")`."),
    ("What is === vs == in JavaScript?",
     "`===` compares value AND type - always use it. `==` converts types first, so `\"1\" == 1` is true and weird cases lurk (`[] == false` is true). The one exception people keep: `x == null` as a deliberate null-or-undefined check."),

    # ---------- HTML and CSS -------------------------------------------------
    ("What is the basic HTML page structure?",
     "```html\n<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n  <meta charset=\"utf-8\">\n  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n  <title>My page</title>\n</head>\n<body>\n  <h1>Hello</h1>\n</body>\n</html>\n```\nThe viewport meta makes phones show the page at normal size."),
    ("What are the most used HTML tags?",
     "Headings `h1`-`h6`, `p`, links `a href`, images `img src alt`, lists `ul/ol/li`, buttons, inputs and forms, `div`/`span` for grouping, `header/nav/main/section/footer` for structure, and `table` for tabular data. In 2026 prefer semantic tags over div soup."),
    ("How do I add an image in HTML?",
     "`<img src=\"photo.jpg\" alt=\"Description of the photo\" width=\"600\">`. Alt text is required for accessibility (and shows when the image fails). Keep images compressed; use `loading=\"lazy\"` for images below the fold."),
    ("How do I make a link open in a new tab?",
     "`<a href=\"https://example.com\" target=\"_blank\" rel=\"noopener noreferrer\">text</a>`. The `rel` protects against a subtle security issue where the opened page controls your tab."),
    ("How do I center a div?",
     "Modern one-liner on the parent: `display: grid; place-items: center;` (or flexbox: `display: flex; align-items: center; justify-content: center;`). Text only: `text-align: center`. Give the parent a height if it collapses."),
    ("How do I center text in CSS?",
     "Horizontally: `text-align: center` on the parent. Vertically inside a fixed-height box: flex on the parent (`display: flex; align-items: center; justify-content: center;`) or `line-height` equal to the height for single lines."),
    ("What is the CSS box model?",
     "Every element is a box: **content -> padding -> border -> margin**. `box-sizing: border-box;` makes width include padding+border (much easier layouts) - put `*, *::before, *::after { box-sizing: border-box; }` at the top of your CSS."),
    ("What is the difference between flexbox and grid?",
     "Flexbox lays items out **in one direction** (row or column) and distributes space - great for toolbars, nav bars, card rows. Grid lays out **rows AND columns** with precise tracks - great for page layouts and galleries. They combine well: grid for the page, flex inside components."),
    ("How do I make a responsive website?",
     "Use the viewport meta tag, fluid widths (`max-width: 100%`, not fixed pixels), relative units (`rem`, `%`, `clamp()`), and media queries:\n```css\n@media (min-width: 768px) {\n  .cards { grid-template-columns: repeat(3, 1fr); }\n}\n```\nDesign mobile-first, then enhance upward."),
    ("How do I change the font in CSS?",
     "`body { font-family: \"Inter\", system-ui, Arial, sans-serif; }`. System fonts (system-ui) load instantly. For custom fonts use `@font-face` or a hosted font with `font-display: swap`, and always list fallbacks. Size: `font-size: 1rem` (16px default)."),
    ("How do I add a shadow in CSS?",
     "Box: `box-shadow: 0 2px 8px rgba(0,0,0,.15);` (x y blur colour). Text: `text-shadow: 0 1px 2px rgba(0,0,0,.4)`. Keep effects subtle and consistent - one shadow scale for the whole site."),
    ("How do I make a button in CSS?",
     "```css\n.btn {\n  display: inline-block;\n  padding: .6rem 1.2rem;\n  border: 0;\n  border-radius: 8px;\n  background: #2563eb;\n  color: #fff;\n  font: inherit;\n  cursor: pointer;\n}\n.btn:hover { background: #1d4ed8; }\n.btn:focus-visible { outline: 2px solid #93c5fd; }\n```\nNever remove focus outlines without a replacement - keyboard users need them."),
    ("What are CSS variables?",
     "Custom properties you define once and reuse:\n```css\n:root { --brand: #2563eb; --radius: 10px; }\n.card { border-radius: var(--radius); }\n.btn  { background: var(--brand); }\n```\nThey cascade and can be themed (e.g. different value inside dark mode media query)."),
    ("How do I support dark mode in CSS?",
     "```css\n@media (prefers-color-scheme: dark) {\n  :root { --bg: #0b0e14; --text: #e6e6e6; }\n}\nbody { background: var(--bg, #fff); color: var(--text, #111); }\n```\nDrive everything from variables so both themes stay consistent."),
    ("What is semantic HTML and why does it matter?",
     "Using tags that describe meaning: `<nav>`, `<main>`, `<article>`, `<button>`, `<label>`. It helps screen readers, search engines and future-you. A clickable thing that acts like a button should BE a `<button>` (keyboard support comes free)."),

    # ---------- SQL and data -------------------------------------------------
    ("How do I write a SELECT query in SQL?",
     "```sql\nSELECT name, email\nFROM users\nWHERE age >= 18\nORDER BY name\nLIMIT 10;\n```\nOrder of clauses is fixed: SELECT ... FROM ... WHERE ... GROUP BY ... HAVING ... ORDER BY ... LIMIT."),
    ("What is the difference between WHERE and HAVING?",
     "`WHERE` filters rows **before** grouping; `HAVING` filters groups **after** aggregation. Example: `SELECT city, COUNT(*) FROM users WHERE age > 18 GROUP BY city HAVING COUNT(*) > 100;`"),
    ("How do I join two tables in SQL?",
     "```sql\nSELECT o.id, c.name\nFROM orders o\nJOIN customers c ON c.id = o.customer_id;\n```\n`JOIN`/`INNER JOIN` keeps matches only; `LEFT JOIN` keeps all left rows with NULLs where there is no match. Join on indexed keys for speed."),
    ("What is a primary key vs a foreign key?",
     "A **primary key** uniquely identifies each row in a table (often an auto-incrementing id). A **foreign key** is a column pointing at another table's primary key, enforcing that the reference exists. Together they keep relational data honest."),
    ("How do I group and count in SQL?",
     "```sql\nSELECT city, COUNT(*) AS people, AVG(age) AS avg_age\nFROM users\nGROUP BY city\nORDER BY people DESC;\n```\nEvery selected column must be in GROUP BY or wrapped in an aggregate (COUNT, SUM, AVG, MIN, MAX)."),
    ("How do I insert, update and delete rows in SQL?",
     "`INSERT INTO users (name, age) VALUES ('Ada', 36);`\n`UPDATE users SET age = 37 WHERE name = 'Ada';`\n`DELETE FROM users WHERE age < 18;`\nAlways include the WHERE unless you truly mean every row; test with SELECT first."),
    ("How do I create a table in SQL?",
     "```sql\nCREATE TABLE users (\n  id INTEGER PRIMARY KEY AUTOINCREMENT,\n  name TEXT NOT NULL,\n  email TEXT UNIQUE,\n  created_at TEXT DEFAULT CURRENT_TIMESTAMP\n);\n```\nNOT NULL and UNIQUE are cheap guards that save data-cleaning later; add an index on columns you filter or join by."),
    ("How do I find duplicates in SQL?",
     "```sql\nSELECT email, COUNT(*) AS n\nFROM users\nGROUP BY email\nHAVING COUNT(*) > 1;\n```\nThen fix: keep the lowest id per email (`DELETE FROM users WHERE id NOT IN (SELECT MIN(id) FROM users GROUP BY email)`)."),
    ("What is an index in a database?",
     "An index is a sorted lookup structure (usually a B-tree) that makes WHERE/JOIN/ORDER BY on those columns fast, at the cost of extra write time and storage. Create for columns you filter by often: `CREATE INDEX idx_users_email ON users(email);`. Unused indexes just slow inserts down."),
    ("What is SQL injection and how do I prevent it?",
     "An attack where user text is treated as SQL. Prevent it with **parameterised queries**: `cur.execute(\"SELECT * FROM users WHERE name = ?\", (name,))` - never f-strings into SQL. This one habit closes the entire vulnerability class."),

    # ---------- Git -----------------------------------------------------------
    ("What are the basic git commands?",
     "`git init` (start), `git status` (what changed), `git add -A` (stage all), `git commit -m \"message\"` (save snapshot), `git log --oneline` (history), `git diff` (unstaged changes), `git pull` (get updates), `git push` (send commits)."),
    ("How do I undo a git commit?",
     "Keep changes, undo commit: `git reset --soft HEAD~1`. Discard changes too (careful): `git reset --hard HEAD~1`. Already pushed? Do not reset shared history - use `git revert <hash>` to make a new commit that undoes it."),
    ("How do I create and switch a git branch?",
     "`git switch -c feature/login` creates and switches (older syntax: `git checkout -b`). List: `git branch`. Switch back: `git switch main`. Merge: `git switch main` then `git merge feature/login`. Delete merged branch: `git branch -d feature/login`."),
    ("How do I resolve a git merge conflict?",
     "Open the conflicted files, find the `<<<<<<<`, `=======`, `>>>>>>>` markers, edit to the exact result you want, remove the markers, then `git add file` and `git commit`. To abort and start over: `git merge --abort`. View any file's stage: `git diff --check`."),
    ("How do I save unfinished work in git?",
     "`git stash` parks changes and cleans the tree; `git stash pop` brings them back. Named: `git stash push -m \"wip login\"`; list: `git stash list`; apply and keep the stash: `git stash apply`."),
    ("How do I see my git history?",
     "`git log --oneline --graph --decorate --all` for the pretty version. One file: `git log -p -- file.py`. Who changed a line: `git blame file.py`. Search messages: `git log --grep=\"fix\"`. Time-travel to a hash: `git switch <hash>`."),
    ("How do I fix 'git: command not found'?",
     "Install Git (git-scm.com or your package manager: `sudo apt install git`, `brew install git`; on Windows use Git for Windows), then restart the terminal. Check with `git --version`. Configure once: `git config --global user.name \"You\"` and `git config --global user.email you@example.com`."),
    ("How do I connect a local repo to GitHub?",
     "Create an empty repo on GitHub, then:\n```bash\ngit remote add origin https://github.com/user/repo.git\ngit branch -M main\ngit push -u origin main\n```\nFor HTTPS, use a personal access token as the password; SSH keys are nicer long-term (`ssh-keygen`, add the public key to GitHub)."),
    ("What is a .gitignore file?",
     "A list of paths git should never track: `__pycache__/`, `*.log`, `.env`, `venv/`, `node_modules/`, `*.db`. Add it before the first commit so secrets and junk never enter history. If a file is already tracked, `git rm --cached path` after adding the rule."),
    ("What is the difference between git fetch and git pull?",
     "`git fetch` downloads new commits from the remote but changes nothing on your branch - safe look. `git pull` = fetch + merge into your current branch (or rebase with `--rebase`). Fetch first when you want to inspect before integrating."),
    ("How do I commit only part of my changes?",
     "`git add -p` walks through each change hunk and asks stage-or-skip ('y'/'n'/'s' to split). Perfect for keeping commits clean and single-topic. Then `git commit -m \"...\"` as usual."),

    # ---------- algorithms and concepts -------------------------------------
    ("What is Big O notation?",
     "Big O describes how an algorithm's time or memory grows with input size n, ignoring constants. Common: O(1) constant (dict lookup), O(log n) binary search, O(n) one pass, O(n log n) good sorting, O(n^2) nested loops, O(2^n) brute-force subsets. Design for the size you actually have."),
    ("How does binary search work?",
     "On a **sorted** list, check the middle; if too small, search the right half, else the left - halving each time (O(log n)):\n```python\ndef bsearch(a, x):\n    lo, hi = 0, len(a) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if a[mid] == x: return mid\n        if a[mid] < x: lo = mid + 1\n        else: hi = mid - 1\n    return -1\n```"),
    ("How does quicksort work?",
     "Pick a pivot, partition smaller items left and larger right, then sort each side recursively. Average O(n log n), worst O(n^2) with bad pivots (random pivot fixes typical cases), and it sorts in place. In practice use the language's built-in sort - it is tuned (Timsort in Python, introsort in C++)."),
    ("How does a hash table work?",
     "A hash function turns a key into an index into an array of buckets. Lookup/insert average O(1); collisions are handled by chaining or open addressing. Python's dict and set are hash tables - that is why `x in seen` is fast."),
    ("What is recursion?",
     "A function that calls itself on a smaller version of the problem until it hits a base case. Every loop can be written recursively and vice versa. Watch for stack depth (Python ~1000 frames) and repeated work - memoise (cache results) to keep it fast:\n```python\nfrom functools import lru_cache\n@lru_cache(maxsize=None)\ndef fib(n):\n    return n if n < 2 else fib(n-1) + fib(n-2)\n```"),
    ("What is the difference between a stack and a queue?",
     "A **stack** is last-in-first-out: push/pop at one end - undo buttons, call stacks, DFS. A **queue** is first-in-first-out: enqueue at back, dequeue at front - printers, message queues, BFS. Python: list works as a stack; use `collections.deque` for a fast queue."),
    ("What is a linked list?",
     "Nodes that each hold a value and a pointer to the next node. Insert/delete at a known position is O(1), but reaching position i is O(n) because you walk the chain, and memory is scattered. Real programs reach for arrays/lists first; linked lists shine in specialised cases (LRU caches, intrusive lists)."),
    ("What is dynamic programming?",
     "Solving a problem by combining answers to **overlapping subproblems**, caching each result once. Recipe: define the state, write the recurrence, choose an order (bottom-up loop or top-down memo), then optimise memory. Classic wins: coin change, edit distance, knapsack, shortest paths."),
    ("What is BFS vs DFS?",
     "**Breadth-first search** explores level by level with a queue - finds the shortest path in unweighted graphs. **Depth-first search** dives down one branch with a stack/recursion - good for exploring all paths, cycle detection and topological sort. Both O(V+E) on a graph with V vertices and E edges."),
    ("What is memoization?",
     "Caching a function's results by its arguments so repeated calls are instant. In Python `functools.lru_cache` (or `cache`) does it in one decorator. Only works for pure functions (same input -> same output, no side effects)."),
    ("What is the two-pointer technique?",
     "Walk two indices through data instead of nested loops. Examples: find a pair summing to a target in a sorted list (one pointer each end, O(n)); remove duplicates in place (slow/fast); reverse a string in place; detect a cycle in a linked list (tortoise and hare)."),
    ("How do I check if a number is prime?",
     "```python\ndef is_prime(n):\n    if n < 2: return False\n    if n % 2 == 0: return n == 2\n    d = 3\n    while d * d <= n:\n        if n % d == 0: return False\n        d += 2\n    return True\n```\nOnly test divisors up to sqrt(n) - O(sqrt n). For many queries, precompute a sieve of Eratosthenes."),
    ("What is time vs space complexity trade-off?",
     "You can often buy speed with memory or save memory with time: caching (hash map) turns repeated O(n) work into O(1) but stores data; streaming processes huge data in constant memory but makes multiple passes. Choose by the bottleneck: slow machine vs limited RAM."),

    # ---------- general dev --------------------------------------------------
    ("How do I write clean code?",
     "Small functions that do one thing with honest names, no surprises (side effects clearly named), early returns instead of deep nesting, comments for **why** not what, consistent formatting (let a formatter decide), and delete dead code. Code is read far more than written - optimise for the reader."),
    ("How do I debug code effectively?",
     "Read the error message fully (file, line, type). Reproduce reliably, then shrink the input until the bug is obvious (bisect the code/data). Print or breakpoint the values you assume. Change one thing at a time. Write the failing case as a test, fix, keep the test. The bug is usually in what you did not question."),
    ("What is the difference between a framework and a library?",
     "You **call** a library; a framework **calls you** (it defines the skeleton and your code plugs in - 'inversion of control'). React/Flask/Django are frameworks; requests/NumPy/Lodash are libraries. Both are just dependencies - the pattern of who runs the show is the difference."),
    ("What is an API endpoint?",
     "A specific URL your program can call to do one thing: `GET /users/42` returns that user; `POST /users` creates one; `DELETE /users/42` removes it. The set of endpoints plus their formats is the API. HTTP methods (GET/POST/PUT/DELETE), status codes and JSON are the shared grammar."),
    ("What do HTTP status codes mean?",
     "1xx info (rare), 2xx success (**200** OK, 201 created, 204 no content), 3xx redirects (301 permanent, 302 temporary), 4xx your fault (**400** bad request, **401** unauthenticated, **403** forbidden, **404** not found, 429 too many requests), 5xx server's fault (**500**, 503 unavailable). Retry 5xx and 429 with backoff; fix 4xx."),
    ("What is a REST API?",
     "A style of web API built on plain HTTP resources: nouns in URLs (`/orders/42`), actions as HTTP methods (GET/POST/PUT/DELETE), JSON bodies, and stateless requests (each carries its own auth). Predictable and easy to cache. GraphQL and gRPC are popular alternatives with different trade-offs."),
    ("What is an environment variable?",
     "A named value given to a program by its environment. Set in shell: `export API_KEY=...` (mac/Linux) or `setx API_KEY ...` (Windows). Read in Python: `os.environ.get(\"API_KEY\")`. Use them for secrets and per-machine settings so they never enter git."),
    ("How do I keep secrets out of my code?",
     "Store them in environment variables or a `.env` file that is listed in `.gitignore`; load locally with python-dotenv; use your platform's secret manager in production. If a secret was ever committed, rotate it - deleting the commit is not enough since history keeps it."),
    ("What is Docker in one paragraph?",
     "Docker packages an app with its OS dependencies into an image; running it creates a container - a lightweight, isolated process that behaves the same on any machine. A Dockerfile describes the build; `docker build -t app .` makes the image; `docker run -p 8000:8000 app` starts it. It removes the 'works on my machine' class of problems."),
    ("What is a web server vs an app server?",
     "A web server (Nginx, Apache) handles raw HTTP: TLS, static files, caching, forwarding. An app server runs your code (Flask with gunicorn, Node with Express, Django with uWSGI) and produces dynamic responses. Production stacks usually put them in that order: users -> web server -> app server -> database."),
    ("What is CI/CD?",
     "**Continuous integration**: every push automatically runs tests and builds - bugs are caught in minutes, not weeks. **Continuous delivery/deployment**: passing builds are packaged and (optionally automatically) released to production. Tools: GitHub Actions, GitLab CI, Jenkins. Start with 'run tests on push' - that alone catches most breakage."),
    ("How do I make my website load faster?",
     "Compress and resize images (usually 80%+ of the bytes; serve WebP/AVIF), lazy-load below-the-fold media, minify and cache CSS/JS with long cache headers (hash filenames to bust), use a CDN for static files, load fonts with `font-display: swap`, and ship less JavaScript. Measure with Lighthouse before and after."),
    ("What is caching?",
     "Storing a computed result so the next request is cheap: browser cache (Cache-Control headers), CDN edge cache, application cache (Redis or an in-memory dict), database query cache. Rules of thumb: cache the expensive and reused, set an expiry, name keys carefully, and have a way to bust the cache when data changes."),
]


def build_entries():
    entries = []
    for q, a in CODE:
        entries.append((q, a, "code"))
    return entries


def main():
    train = "--train" in sys.argv
    t0 = time.time()
    mem = Memory()
    brain = Brain(mem)

    existing = set()
    with mem.lock:
        for (q,) in mem.conn.execute("SELECT question FROM qa"):
            existing.add(re.sub(r"\W+", " ", (q or "").lower()).strip())

    def norm(q):
        return re.sub(r"\W+", " ", q.lower()).strip()

    entries = build_entries()
    qa_added = 0
    doc_added = 0
    for q, a, topic in entries:
        text = q + " " + re.sub(r"\*\*", "", a)
        ids = mem.add_passages("code://%s" % topic, "TenSeiAi coding pack: " + topic,
                               text, source="code", topic=topic)
        doc_added += len(ids)
        nq = norm(q)
        if nq in existing:
            continue
        existing.add(nq)
        emb = brain.embedder.encode(q)
        mem.add_qa(q, a, EVIDENCE, emb,
                   emb0=brain.embedder.base_encode(q), mode="code")
        qa_added += 1
    mem.kv_set("code_pack_v1", {"qa": qa_added, "docs": doc_added, "at": time.time()})
    print("[code] added %d Q&A pairs, %d passages in %.1fs"
          % (qa_added, doc_added, time.time() - t0))
    print("[code] memory now:", mem.stats())
    if train:
        meta = brain.train_all(log=lambda m: print(" [train]", m))
        print("[code] brain version:", meta.get("version"), "metrics:", meta.get("metrics"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
