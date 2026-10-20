"""TenSeiAi code composer: answers "give me / write me" code and script
requests with an actual working snippet instead of describing the topic.

It parses the ask, composes the code, and SYNTAX-CHECKS it locally
(bash -n for shells, compile() for python) before answering.
"""

import re
import subprocess

_VERBS = ("write", "create", "make", "generate", "give", "show me", "build",
          "code me", "need", "want", "how to", "how do", "implement", "develop",
          "can you", "please", "solve", "construct", "provide", "example", "code")
_CODEWORDS = ("script", "code", "bash", "shell", "sh ", "python", "program",
              "snippet", "command", "function", "tool", "cli", "algorithm",
              "class", "method", "loop", "array", "list", "dict", "regex",
              "sql", "query", "html", "css", "api", "endpoint", "server",
              "reverse", "sort", "quicksort", "binary search", "fibonacci",
              "factorial", "palindrome", "prime", "anagram")

_DIRECT_CODE_PHRASES = (
    "binary search", "quick sort", "quicksort", "bubble sort", "merge sort",
    "fibonacci", "reverse a string", "reverse string", "palindrome", "anagram", "anagrams",
    "fizzbuzz", "fizz buzz", "two sum", "linked list", "breadth first",
    "depth first", "read a file", "write a file", "http request", "fetch json",
    "sql query", "html css", "flask app", "bash script", "dockerfile",
    "hello world", "in python", "in c++", "in java", "in javascript",
    "in rust", "in bash", "in golang", "in go", "sieve of eratosthenes",
    "sieve", "kth largest", "k-th largest", "priorityqueue", "min-heap", "min heap",
    "password manager", "aes-256", "aes 256", "aes encryption", "lru cache",
    "dijkstra"
)


def is_code_request(q):
    ql = " " + q.lower() + " "
    if any(p in ql for p in _DIRECT_CODE_PHRASES):
        return True
    return any(w in ql for w in _CODEWORDS) and any(v in ql for v in _VERBS)


def detect_lang(q):
    ql = q.lower()
    if "bash" in ql or "shell" in ql or "sh script" in ql or "unix" in ql:
        return "bash"
    if "python" in ql:
        return "python"
    if "kotlin" in ql:
        return "kotlin"
    if "typescript" in ql:
        return "typescript"
    if "javascript" in ql or " node " in ql or " js " in ql:
        return "javascript"
    if "dart" in ql:
        return "dart"
    if "swift" in ql:
        return "swift"
    if "c#" in ql or "csharp" in ql or "c sharp" in ql:
        return "csharp"
    if "rust" in ql:
        return "rust"
    if "c++" in ql or "cpp" in ql:
        return "cpp"
    if re.search(r'\bgo(?:lang)?\b', ql):
        return "go"
    if "ruby" in ql:
        return "ruby"
    if "php" in ql:
        return "php"
    if "lua" in ql:
        return "lua"
    if re.search(r'\bin c\b|\bc language\b|\bc code\b|\bc program\b|'
                 r'write a c \w+ program|\ba c (?:program|function|script)\b',
                 ql):
        return "c"
    if "java " in ql or ql.strip().endswith("java"):
        return "java"
    return "bash"


_OBJWORDS = r'(?:folder|directory|dir|file|name)'


def _actions(q):
    """Which filesystem actions the ask is really about. The action words must
    sit near an object word ("creates a folder ..."), otherwise a request verb
    like "Create a rust program" would be mistaken for a folder action."""
    acts = []
    m = re.search(r'\b(?:creat\w*|mak\w*|generat\w*|mkdir)\b[^.;]{0,45}?\b'
                  r'(?:folder|directory|dir|file|name)\w*\b', q, re.I)
    if m:
        acts.append((m.start(), "create"))
    m = re.search(r'\b(?:delet\w*|remov\w*|eras\w*)\b[^.;]{0,35}?\b'
                  r'(?:folder|directory|dir|file|it)\b', q, re.I)
    if m and not re.search(r'\b(?:older|than|except)\b', q, re.I):
        acts.append((m.start(), "delete"))
    acts.sort()
    return [a for _, a in acts]


_STOPNAME = {"the", "a", "an", "new", "basic", "called", "named", "making",
             "folder", "directory", "dir", "file", "script", "it"}


def _target_name(q, default="Tensei"):
    m = re.search(r'(?:called|named)\s+["\']?([A-Za-z0-9_.\-]+)', q, re.I)
    if m:
        return m.group(1)
    m = re.search(r'name[d]?\s+["\']?([A-Za-z0-9_.\-]+)', q, re.I)
    if m:
        return m.group(1)
    m = re.search(r'([A-Za-z0-9_\-]+)\s+(?:folder|directory|dir)\b', q, re.I)
    if m and m.group(1).lower() not in _STOPNAME:
        return m.group(1)
    m = re.search(r'(?:folder|directory|dir)\s+["\']?([A-Za-z0-9_.\-]+)', q, re.I)
    if m and m.group(1).lower() not in _STOPNAME:
        return m.group(1)
    return default


def _wants(q, *words):
    ql = q.lower()
    return any(w in ql for w in words)


def _bash_script(q, name):
    acts = _actions(q)
    if not acts:
        return None
    enter = bool(re.search(r'\b(?:go(?:es)?\s+into|cd\s+into|enter|'
                           r'navigate\s+into|and\s+cd|change\s+into)\b', q, re.I))
    lines = ["#!/usr/bin/env bash", "set -euo pipefail"]
    note = []
    for act in acts:
        if act == "create":
            lines.append('mkdir -p "%s"' % name)
            note.append("creates ./%s" % name)
            if enter:
                lines.append('cd "%s"' % name)
                note.append("enters ./%s" % name)
        else:
            lines.append('rm -rf "%s"' % name)
            note.append("deletes ./%s" % name)
    lines.append('echo "done: %s"' % (" then ".join(note) or "script finished"))
    code = "\n".join(lines)
    return code, "; ".join(note)


def _python_script(q, name):
    acts = _actions(q)
    if not acts:
        return None
    lines = ["import os", "import shutil"]
    note = []
    for act in acts:
        if act == "create":
            lines.append('os.makedirs("%s", exist_ok=True)' % name)
            note.append("creates ./%s" % name)
        else:
            lines.append('shutil.rmtree("%s")' % name)
            note.append("deletes ./%s" % name)
    lines.append('print("done: %s")' % "; ".join(note))
    return "\n".join(lines), "; ".join(note)


def _syntax_check(lang, code):
    try:
        if lang == "bash":
            r = subprocess.run(["bash", "-n", "-c", code],
                               capture_output=True, timeout=6)
            return r.returncode == 0, "bash -n"
        if lang == "python":
            compile(code, "<tensei>", "exec")
            return True, "python compile()"
        if lang in ("c", "cpp"):
            x = "c" if lang == "c" else "c++"
            for cc in ("cc", "gcc", "clang"):
                try:
                    r = subprocess.run([cc, "-fsyntax-only", "-x", x, "-"],
                                       input=code.encode(), capture_output=True,
                                       timeout=10)
                    if r.returncode == 0:
                        return True, "%s -fsyntax-only" % cc
                    return False, ""
                except FileNotFoundError:
                    continue
    except Exception:
        pass
    return False, ""


_HELLO = {
    "bash": '#!/usr/bin/env bash\nset -euo pipefail\n\necho "Hello, World!"',
    "python": 'print("Hello, World!")',
    "javascript": 'console.log("Hello, World!");',
    "java": ('public class Hello {\n'
             '    public static void main(String[] args) {\n'
             '        System.out.println("Hello, World!");\n'
             '    }\n}'),
    "rust": 'fn main() {\n    println!("Hello, World!");\n}',
    "cpp": ('#include <iostream>\n\n'
            'int main() {\n'
            '    std::cout << "Hello, World!\\n";\n'
            '    return 0;\n}'),
    "dart": "void main() {\n    print('Hello, World!');\n}",
    "go": ('package main\n\nimport "fmt"\n\nfunc main() {\n'
           '    fmt.Println("Hello, World!")\n}'),
    "ruby": 'puts "Hello, World!"',
    "php": '<?php\necho "Hello, World!\\n";',
    "kotlin": ('fun main() {\n'
               '    println("Hello, World!")\n'
               '}'),
    "swift": 'print("Hello, World!")',
    "csharp": ('using System;\n\n'
               'class Program\n{\n'
               '    static void Main()\n'
               '    {\n'
               '        Console.WriteLine("Hello, World!");\n'
               '    }\n}'),
    "typescript": 'console.log("Hello, World!");',
    "c": ('#include <stdio.h>\n\n'
          'int main(void) {\n'
          '    printf("Hello, World!\\n");\n'
          '    return 0;\n}'),
    "lua": 'print("Hello, World!")',
}


_FULL = {
    "bash": ('#!/usr/bin/env bash\nset -euo pipefail\n\n\n'
             'greet() {\n    echo "Hello, $1!"\n}\n\n\n'
             'main() {\n    local names=("$@")\n'
             '    if [ ${#names[@]} -eq 0 ]; then\n'
             '        names=("World")\n    fi\n'
             '    for name in "${names[@]}"; do\n'
             '        greet "$name"\n    done\n}\n\n\n'
             'main "$@"'),
    "python": ('import sys\n\n\n'
               'def greet(name):\n    return "Hello, %s!" % name\n\n\n'
               'def main():\n'
               '    names = sys.argv[1:] or ["World"]\n'
               '    for name in names:\n'
               '        print(greet(name))\n\n\n'
               'if __name__ == "__main__":\n    main()'),
    "kotlin": ('fun greet(name: String): String {\n'
               '    return "Hello, $name!"\n}\n\n'
               'fun main(args: Array<String>) {\n'
               '    val names = if (args.isEmpty()) listOf("World") else args.toList()\n'
               '    for (name in names) {\n'
               '        println(greet(name))\n'
               '    }\n}'),
    "dart": ("String greet(String name) {\n"
             "  return 'Hello, $name!';\n}\n\n"
             "void main(List<String> args) {\n"
             "  final names = args.isEmpty ? ['World'] : args;\n"
             "  for (final name in names) {\n"
             "    print(greet(name));\n"
             "  }\n}"),
    "java": ('public class Main {\n'
             '    static String greet(String name) {\n'
             '        return "Hello, " + name + "!";\n    }\n\n'
             '    public static void main(String[] args) {\n'
             '        String[] names = args.length > 0 ? args : new String[]{"World"};\n'
             '        for (String name : names) {\n'
             '            System.out.println(greet(name));\n'
             '        }\n    }\n}'),
    "cpp": ('#include <iostream>\n#include <string>\n#include <vector>\n\n'
            'std::string greet(const std::string& name) {\n'
            '    return "Hello, " + name + "!";\n}\n\n'
            'int main(int argc, char* argv[]) {\n'
            '    std::vector<std::string> names;\n'
            '    if (argc > 1) {\n'
            '        for (int i = 1; i < argc; ++i) names.push_back(argv[i]);\n'
            '    } else {\n'
            '        names.push_back("World");\n'
            '    }\n'
            '    for (const auto& n : names) {\n'
            '        std::cout << greet(n) << "\\n";\n'
            '    }\n    return 0;\n}'),
    "c": ('#include <stdio.h>\n\n'
          'static void greet(const char *name) {\n'
          '    printf("Hello, %s!\\n", name);\n}\n\n'
          'int main(int argc, char *argv[]) {\n'
          '    if (argc > 1) {\n'
          '        for (int i = 1; i < argc; ++i) {\n'
          '            greet(argv[i]);\n'
          '        }\n'
          '    } else {\n'
          '        greet("World");\n'
          '    }\n    return 0;\n}'),
    "rust": ('use std::env;\n\n'
             'fn greet(name: &str) -> String {\n'
             '    format!("Hello, {}!", name)\n}\n\n'
             'fn main() {\n'
             '    let args: Vec<String> = env::args().skip(1).collect();\n'
             '    let names = if args.is_empty() {\n'
             '        vec![String::from("World")]\n'
             '    } else {\n'
             '        args\n'
             '    };\n'
             '    for name in &names {\n'
             '        println!("{}", greet(name));\n'
             '    }\n}'),
    "javascript": ("function greet(name) {\n"
                   "  return `Hello, ${name}!`;\n}\n\n"
                   "function main() {\n"
                   "  const names = process.argv.slice(2);\n"
                   "  if (names.length === 0) names.push('World');\n"
                   "  for (const name of names) {\n"
                   "    console.log(greet(name));\n"
                   "  }\n}\n\nmain();"),
    "typescript": ("function greet(name: string): string {\n"
                   "  return `Hello, ${name}!`;\n}\n\n"
                   "function main(): void {\n"
                   "  const names = process.argv.slice(2);\n"
                   "  if (names.length === 0) names.push('World');\n"
                   "  for (const name of names) {\n"
                   "    console.log(greet(name));\n"
                   "  }\n}\n\nmain();"),
    "go": ('package main\n\nimport (\n    "fmt"\n    "os"\n)\n\n'
           'func greet(name string) string {\n'
           '    return "Hello, " + name + "!"\n}\n\n'
           'func main() {\n'
           '    names := os.Args[1:]\n'
           '    if len(names) == 0 {\n'
           '        names = []string{"World"}\n'
           '    }\n'
           '    for _, name := range names {\n'
           '        fmt.Println(greet(name))\n'
           '    }\n}'),
    "csharp": ('using System;\n\n'
               'class Program\n{\n'
               '    static string Greet(string name)\n'
               '    {\n'
               '        return "Hello, " + name + "!";\n    }\n\n'
               '    static void Main(string[] args)\n'
               '    {\n'
               '        var names = args.Length > 0 ? args : new[] { "World" };\n'
               '        foreach (var name in names)\n'
               '        {\n'
               '            Console.WriteLine(Greet(name));\n'
               '        }\n    }\n}'),
    "swift": ('import Foundation\n\n'
              'func greet(_ name: String) -> String {\n'
              '    return "Hello, \\(name)!"\n}\n\n'
              'let names = CommandLine.arguments.dropFirst()\n'
              'let targets = names.isEmpty ? ["World"] : Array(names)\n'
              'for name in targets {\n'
              '    print(greet(name))\n}'),
    "ruby": ('def greet(name)\n'
             '  "Hello, #{name}!"\nend\n\n'
             'names = ARGV\n'
             'names = ["World"] if names.empty?\n'
             'names.each do |name|\n'
             '  puts greet(name)\nend'),
    "php": ('<?php\nfunction greet($name) {\n'
            '    return "Hello, " . $name . "!";\n}\n\n'
            '$names = array_slice($argv, 1);\n'
            'if (empty($names)) {\n    $names = ["World"];\n}\n'
            'foreach ($names as $name) {\n'
            '    echo greet($name) . PHP_EOL;\n}'),
    "lua": ('local function greet(name)\n'
            '    return "Hello, " .. name .. "!"\nend\n\n'
            'local args = {...}\n'
            'if #args == 0 then\n    args = {"World"}\nend\n'
            'for _, name in ipairs(args) do\n'
            '    print(greet(name))\nend'),
}


def _wants_big(q):
    m = re.search(r'\b(\d{2,3})\s*lines?\b', q, re.I)
    if m and int(m.group(1)) >= 10:
        return True
    return bool(re.search(r'\b(big|full|complete|real|proper)\b', q, re.I))


def _has_negative_constraint(q, term):
    """Detect negative constraints like 'without using sort', 'no slicing', 'avoid reverse'."""
    pattern = r'\b(?:without|no|not|avoid|never|don\'t|dont)\s+(?:using\s+)?(?:built-?in\s+)?' + re.escape(term)
    return bool(re.search(pattern, q, re.I))


_TASKS = {
    "anagram": {
        "python": (
            'def are_anagrams(s1: str, s2: str) -> bool:\n'
            '    """\n'
            '    Checks whether two strings are anagrams without using sort() or sorted().\n'
            '    Handles uppercase letters (case-insensitive) and ignores whitespace.\n'
            '    Time Complexity: O(n + m) linear scan.\n'
            '    Space Complexity: O(k) frequency map space (at most O(1) for fixed alphabet).\n'
            '    """\n'
            '    counts = {}\n\n'
            '    for ch in s1:\n'
            '        if not ch.isspace():\n'
            '            c = ch.lower()\n'
            '            counts[c] = counts.get(c, 0) + 1\n\n'
            '    for ch in s2:\n'
            '        if not ch.isspace():\n'
            '            c = ch.lower()\n'
            '            if c not in counts:\n'
            '                return False\n'
            '            counts[c] -= 1\n'
            '            if counts[c] == 0:\n'
            '                del counts[c]\n\n'
            '    return len(counts) == 0\n\n\n'
            'if __name__ == "__main__":\n'
            '    test_cases = [\n'
            '        ("Listen", "Silent", True),\n'
            '        ("Astronomer", "Moon starer", True),\n'
            '        ("The Eyes", "They See", True),\n'
            '        ("Hello", "World", False),\n'
            '        ("aab", "abb", False),\n'
            '    ]\n'
            '    for s1, s2, expected in test_cases:\n'
            '        res = are_anagrams(s1, s2)\n'
            '        status = "PASS" if res == expected else "FAIL"\n'
            '        print(f"[{status}] \'{s1}\' & \'{s2}\' -> {res}")\n'
        ),
        "javascript": (
            'function areAnagrams(s1, s2) {\n'
            '  const counts = new Map();\n'
            '  for (const ch of s1) {\n'
            '    if (/\\s/.test(ch)) continue;\n'
            '    const c = ch.toLowerCase();\n'
            '    counts.set(c, (counts.get(c) || 0) + 1);\n'
            '  }\n'
            '  for (const ch of s2) {\n'
            '    if (/\\s/.test(ch)) continue;\n'
            '    const c = ch.toLowerCase();\n'
            '    if (!counts.has(c)) return false;\n'
            '    const rem = counts.get(c) - 1;\n'
            '    if (rem === 0) counts.delete(c);\n'
            '    else counts.set(c, rem);\n'
            '  }\n'
            '  return counts.size === 0;\n'
            '}\n\n'
            'console.log(areAnagrams("Listen", "Silent"));\n'
            'console.log(areAnagrams("Astronomer", "Moon starer"));\n'
        ),
        "cpp": (
            '#include <iostream>\n'
            '#include <string>\n'
            '#include <unordered_map>\n'
            '#include <cctype>\n\n'
            'bool areAnagrams(const std::string& s1, const std::string& s2) {\n'
            '    std::unordered_map<char, int> counts;\n'
            '    for (char c : s1) {\n'
            '        if (!std::isspace(static_cast<unsigned char>(c))) {\n'
            '            counts[std::tolower(static_cast<unsigned char>(c))]++;\n'
            '        }\n'
            '    }\n'
            '    for (char c : s2) {\n'
            '        if (!std::isspace(static_cast<unsigned char>(c))) {\n'
            '            char lc = std::tolower(static_cast<unsigned char>(c));\n'
            '            auto it = counts.find(lc);\n'
            '            if (it == counts.end()) return false;\n'
            '            it->second--;\n'
            '            if (it->second == 0) counts.erase(it);\n'
            '        }\n'
            '    }\n'
            '    return counts.empty();\n'
            '}\n\n'
            'int main() {\n'
            '    std::cout << std::boolalpha;\n'
            '    std::cout << areAnagrams("Listen", "Silent") << "\\n";\n'
            '    std::cout << areAnagrams("Astronomer", "Moon starer") << "\\n";\n'
            '    return 0;\n'
            '}\n'
        ),
        "java": (
            'import java.util.HashMap;\n'
            'import java.util.Map;\n\n'
            'public class AnagramChecker {\n'
            '    public static boolean areAnagrams(String s1, String s2) {\n'
            '        Map<Character, Integer> counts = new HashMap<>();\n'
            '        for (char c : s1.toCharArray()) {\n'
            '            if (!Character.isWhitespace(c)) {\n'
            '                char lc = Character.toLowerCase(c);\n'
            '                counts.put(lc, counts.getOrDefault(lc, 0) + 1);\n'
            '            }\n'
            '        }\n'
            '        for (char c : s2.toCharArray()) {\n'
            '            if (!Character.isWhitespace(c)) {\n'
            '                char lc = Character.toLowerCase(c);\n'
            '                if (!counts.containsKey(lc)) return false;\n'
            '                int rem = counts.get(lc) - 1;\n'
            '                if (rem == 0) counts.remove(lc);\n'
            '                else counts.put(lc, rem);\n'
            '            }\n'
            '        }\n'
            '        return counts.isEmpty();\n'
            '    }\n'
            '    public static void main(String[] args) {\n'
            '        System.out.println(areAnagrams("Listen", "Silent"));\n'
            '        System.out.println(areAnagrams("Astronomer", "Moon starer"));\n'
            '    }\n'
            '}\n'
        ),
    },
    "second_largest": {
        "python": (
            'def find_second_largest_unique(numbers):\n'
            '    """\n'
            '    Finds the second-largest unique number in a list without using sort() or sorted().\n'
            '    Handles lists with fewer than two unique numbers by returning None.\n'
            '    Time Complexity: O(n) - Single linear scan.\n'
            '    Space Complexity: O(1) - Constant auxiliary memory.\n'
            '    """\n'
            '    if not numbers or len(numbers) < 2:\n'
            '        return None\n\n'
            '    first = float("-inf")\n'
            '    second = float("-inf")\n'
            '    seen_unique = 0\n\n'
            '    for num in numbers:\n'
            '        if num > first:\n'
            '            second = first\n'
            '            first = num\n'
            '            seen_unique += 1\n'
            '        elif num < first and num > second:\n'
            '            second = num\n'
            '            seen_unique += 1\n\n'
            '    if second == float("-inf"):\n'
            '        return None  # Fewer than two unique numbers\n'
            '    return second\n\n\n'
            'if __name__ == "__main__":\n'
            '    tests = [\n'
            '        [5, 3, 9, 1, 7],\n'
            '        [10, 10, 10, 9, 8],\n'
            '        [42],\n'
            '        [7, 7, 7],\n'
            '        [],\n'
            '        [-10, -5, -20, -2, -1]\n'
            '    ]\n'
            '    print("Finding second largest unique number (without sorting):")\n'
            '    for t in tests:\n'
            '        print(f"  {t} -> {find_second_largest_unique(t)}")\n'
        ),
        "javascript": (
            'function findSecondLargest(numbers) {\n'
            '  if (!numbers || numbers.length < 2) return null;\n'
            '  let first = -Infinity, second = -Infinity;\n'
            '  for (const num of numbers) {\n'
            '    if (num > first) {\n'
            '      second = first;\n'
            '      first = num;\n'
            '    } else if (num < first && num > second) {\n'
            '      second = num;\n'
            '    }\n'
            '  }\n'
            '  return second === -Infinity ? null : second;\n'
            '}\n\n'
            'console.log(findSecondLargest([5, 3, 9, 1, 7]));\n'
        ),
        "cpp": (
            '#include <iostream>\n'
            '#include <vector>\n'
            '#include <limits>\n'
            '#include <optional>\n\n'
            'std::optional<int> findSecondLargest(const std::vector<int>& numbers) {\n'
            '    if (numbers.size() < 2) return std::nullopt;\n'
            '    long long first = std::numeric_limits<long long>::min();\n'
            '    long long second = std::numeric_limits<long long>::min();\n'
            '    for (int num : numbers) {\n'
            '        if (num > first) {\n'
            '            second = first;\n'
            '            first = num;\n'
            '        } else if (num < first && num > second) {\n'
            '            second = num;\n'
            '        }\n'
            '    }\n'
            '    if (second == std::numeric_limits<long long>::min()) return std::nullopt;\n'
            '    return static_cast<int>(second);\n'
            '}\n\n'
            'int main() {\n'
            '    std::vector<int> nums = {5, 3, 9, 1, 7};\n'
            '    auto res = findSecondLargest(nums);\n'
            '    if (res) std::cout << "Second largest: " << *res << "\\n";\n'
            '    return 0;\n'
            '}\n'
        ),
        "java": (
            'public class Main {\n'
            '    public static Integer findSecondLargest(int[] numbers) {\n'
            '        if (numbers == null || numbers.length < 2) return null;\n'
            '        Long first = Long.MIN_VALUE;\n'
            '        Long second = Long.MIN_VALUE;\n'
            '        for (int num : numbers) {\n'
            '            if (num > first) {\n'
            '                second = first;\n'
            '                first = (long) num;\n'
            '            } else if (num < first && num > second) {\n'
            '                second = (long) num;\n'
            '            }\n'
            '        }\n'
            '        return (second == Long.MIN_VALUE) ? null : second.intValue();\n'
            '    }\n'
            '    public static void main(String[] args) {\n'
            '        int[] nums = {5, 3, 9, 1, 7};\n'
            '        System.out.println("Second largest: " + findSecondLargest(nums));\n'
            '    }\n'
            '}\n'
        ),
    },
    "reverse_string_no_slice": {
        "python": (
            'def reverse_string(s: str) -> str:\n'
            '    """\n'
            '    Reverses a string without using slicing ([::-1]) or built-in reverse functions.\n'
            '    Time Complexity: O(n) - Linear pass.\n'
            '    Space Complexity: O(n) - Auxiliary character buffer.\n'
            '    """\n'
            '    reversed_chars = []\n'
            '    # Iterate backwards from the last character to the first\n'
            '    for i in range(len(s) - 1, -1, -1):\n'
            '        reversed_chars.append(s[i])\n'
            '    return "".join(reversed_chars)\n\n\n'
            'def reverse_two_pointer(s: str) -> str:\n'
            '    """Alternative two-pointer in-place swap using a mutable list."""\n'
            '    chars = list(s)\n'
            '    left, right = 0, len(chars) - 1\n'
            '    while left < right:\n'
            '        chars[left], chars[right] = chars[right], chars[left]\n'
            '        left += 1\n'
            '        right -= 1\n'
            '    return "".join(chars)\n\n\n'
            'if __name__ == "__main__":\n'
            '    sample = "Hello, World!"\n'
            '    print("Original:", sample)\n'
            '    print("Reversed (loop):", reverse_string(sample))\n'
            '    print("Reversed (two-pointer):", reverse_two_pointer(sample))\n'
        ),
        "javascript": (
            'function reverseString(s) {\n'
            '  let reversed = "";\n'
            '  for (let i = s.length - 1; i >= 0; i--) {\n'
            '    reversed += s[i];\n'
            '  }\n'
            '  return reversed;\n'
            '}\n\n'
            'console.log(reverseString("Hello, World!"));\n'
        ),
        "cpp": (
            '#include <iostream>\n'
            '#include <string>\n\n'
            'std::string reverseString(std::string s) {\n'
            '    int left = 0, right = s.length() - 1;\n'
            '    while (left < right) {\n'
            '        char temp = s[left];\n'
            '        s[left] = s[right];\n'
            '        s[right] = temp;\n'
            '        left++;\n'
            '        right--;\n'
            '    }\n'
            '    return s;\n'
            '}\n\n'
            'int main() {\n'
            '    std::cout << reverseString("Hello, World!") << "\\n";\n'
            '    return 0;\n'
            '}\n'
        ),
        "java": (
            'public class Main {\n'
            '    public static String reverseString(String s) {\n'
            '        char[] chars = s.toCharArray();\n'
            '        int left = 0, right = chars.length - 1;\n'
            '        while (left < right) {\n'
            '            char temp = chars[left];\n'
            '            chars[left] = chars[right];\n'
            '            chars[right] = temp;\n'
            '            left++;\n'
            '            right--;\n'
            '        }\n'
            '        return new String(chars);\n'
            '    }\n'
            '    public static void main(String[] args) {\n'
            '        System.out.println(reverseString("Hello, World!"));\n'
            '    }\n'
            '}\n'
        ),
    },
    "find_duplicates": {
        "python": (
            'def find_duplicates(nums):\n'
            '    """\n'
            '    Detects and returns all duplicate elements in a list using a set.\n'
            '    Time Complexity: O(n) - Single linear pass over the list.\n'
            '    Space Complexity: O(n) - Auxiliary storage for seen and duplicate sets.\n'
            '    """\n'
            '    seen = set()\n'
            '    duplicates = set()\n'
            '    for item in nums:\n'
            '        if item in seen:\n'
            '            duplicates.add(item)\n'
            '        else:\n'
            '            seen.add(item)\n'
            '    return list(duplicates)\n\n\n'
            'if __name__ == "__main__":\n'
            '    sample_list = [1, 2, 3, 4, 2, 7, 8, 8, 3]\n'
            '    result = find_duplicates(sample_list)\n'
            '    print("Original list:", sample_list)\n'
            '    print("Duplicate elements found:", result)\n'
        ),
        "javascript": (
            'function findDuplicates(nums) {\n'
            '  const seen = new Set();\n'
            '  const duplicates = new Set();\n'
            '  for (const item of nums) {\n'
            '    if (seen.has(item)) {\n'
            '      duplicates.add(item);\n'
            '    } else {\n'
            '      seen.add(item);\n'
            '    }\n'
            '  }\n'
            '  return Array.from(duplicates);\n'
            '}\n\n'
            'console.log("Duplicates:", findDuplicates([1, 2, 3, 4, 2, 7, 8, 8, 3]));\n'
        ),
        "cpp": (
            '#include <iostream>\n'
            '#include <vector>\n'
            '#include <unordered_set>\n\n'
            'std::vector<int> findDuplicates(const std::vector<int>& nums) {\n'
            '    std::unordered_set<int> seen;\n'
            '    std::unordered_set<int> duplicates;\n'
            '    for (int num : nums) {\n'
            '        if (seen.find(num) != seen.end()) {\n'
            '            duplicates.insert(num);\n'
            '        } else {\n'
            '            seen.insert(num);\n'
            '        }\n'
            '    }\n'
            '    return std::vector<int>(duplicates.begin(), duplicates.end());\n'
            '}\n\n'
            'int main() {\n'
            '    std::vector<int> nums = {1, 2, 3, 4, 2, 7, 8, 8, 3};\n'
            '    auto dups = findDuplicates(nums);\n'
            '    std::cout << "Duplicates found: ";\n'
            '    for (int x : dups) std::cout << x << " ";\n'
            '    std::cout << "\\n";\n'
            '    return 0;\n'
            '}\n'
        ),
        "java": (
            'import java.util.*;\n\n'
            'public class Main {\n'
            '    public static List<Integer> findDuplicates(int[] nums) {\n'
            '        Set<Integer> seen = new HashSet<>();\n'
            '        Set<Integer> duplicates = new HashSet<>();\n'
            '        for (int num : nums) {\n'
            '            if (!seen.add(num)) {\n'
            '                duplicates.add(num);\n'
            '            }\n'
            '        }\n'
            '        return new ArrayList<>(duplicates);\n'
            '    }\n\n'
            '    public static void main(String[] args) {\n'
            '        int[] sample = {1, 2, 3, 4, 2, 7, 8, 8, 3};\n'
            '        System.out.println("Duplicates found: " + findDuplicates(sample));\n'
            '    }\n'
            '}\n'
        ),
    },
    "is_prime": {
        "python": (
            'def is_prime(n: int) -> bool:\n'
            '    """\n'
            '    Checks whether an integer n is prime in O(sqrt(n)) time.\n'
            '    Uses 6k +/- 1 divisor candidate stepping.\n'
            '    """\n'
            '    if n <= 1:\n'
            '        return False\n'
            '    if n <= 3:\n'
            '        return True\n'
            '    if n % 2 == 0 or n % 3 == 0:\n'
            '        return False\n'
            '    i = 5\n'
            '    while i * i <= n:\n'
            '        if n % i == 0 or n % (i + 2) == 0:\n'
            '            return False\n'
            '        i += 6\n'
            '    return True\n\n\n'
            'if __name__ == "__main__":\n'
            '    test_cases = [1, 2, 3, 4, 17, 19, 20, 29, 49, 97, 100]\n'
            '    print("Prime Check Demonstration:")\n'
            '    for num in test_cases:\n'
            '        print(f"  {num:3d} -> {\x27Prime\x27 if is_prime(num) else \x27Composite / Not Prime\x27}")\n'
        ),
        "javascript": (
            'function isPrime(n) {\n'
            '  if (n <= 1) return false;\n'
            '  if (n <= 3) return true;\n'
            '  if (n % 2 === 0 || n % 3 === 0) return false;\n'
            '  for (let i = 5; i * i <= n; i += 6) {\n'
            '    if (n % i === 0 || n % (i + 2) === 0) return false;\n'
            '  }\n'
            '  return true;\n'
            '}\n\n'
            'console.log("is 29 prime?", isPrime(29));\n'
            'console.log("is 100 prime?", isPrime(100));\n'
        ),
        "cpp": (
            '#include <iostream>\n\n'
            'bool isPrime(int n) {\n'
            '    if (n <= 1) return false;\n'
            '    if (n <= 3) return true;\n'
            '    if (n % 2 == 0 || n % 3 == 0) return false;\n'
            '    for (int i = 5; i * i <= n; i += 6) {\n'
            '        if (n % i == 0 || n % (i + 2) == 0) return false;\n'
            '    }\n'
            '    return true;\n'
            '}\n\n'
            'int main() {\n'
            '    int test_vals[] = {1, 2, 3, 4, 17, 20, 29, 97, 100};\n'
            '    for (int x : test_vals) {\n'
            '        std::cout << x << " -> " << (isPrime(x) ? "Prime" : "Not Prime") << "\\n";\n'
            '    }\n'
            '    return 0;\n'
            '}\n'
        ),
        "java": (
            'public class Main {\n'
            '    public static boolean isPrime(int n) {\n'
            '        if (n <= 1) return false;\n'
            '        if (n <= 3) return true;\n'
            '        if (n % 2 == 0 || n % 3 == 0) return false;\n'
            '        for (int i = 5; i * i <= n; i += 6) {\n'
            '            if (n % i == 0 || n % (i + 2) == 0) return false;\n'
            '        }\n'
            '        return true;\n'
            '    }\n\n'
            '    public static void main(String[] args) {\n'
            '        int[] tests = {1, 2, 3, 4, 17, 20, 29, 97, 100};\n'
            '        for (int x : tests) {\n'
            '            System.out.println(x + " -> " + (isPrime(x) ? "Prime" : "Not Prime"));\n'
            '        }\n'
            '    }\n'
            '}\n'
        ),
    },
    "password_manager": {
        "python": (
            'import os\n'
            'import sys\n'
            'import json\n'
            'import hashlib\n'
            'import hmac\n'
            'import struct\n\n\n'
            'class AES256:\n'
            '    """FIPS-197 AES-256 block cipher implementation."""\n'
            '    SBOX = [\n'
            '        0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,\n'
            '        0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,\n'
            '        0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,\n'
            '        0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,\n'
            '        0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,\n'
            '        0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,\n'
            '        0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,\n'
            '        0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,\n'
            '        0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,\n'
            '        0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,\n'
            '        0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,\n'
            '        0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,\n'
            '        0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,\n'
            '        0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,\n'
            '        0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,\n'
            '        0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16\n'
            '    ]\n'
            '    RCON = [0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36]\n\n'
            '    def __init__(self, key: bytes):\n'
            '        if len(key) != 32:\n'
            '            raise ValueError("AES-256 requires a 32-byte (256-bit) key.")\n'
            '        self._key_schedule = self._expand_key(key)\n\n'
            '    @classmethod\n'
            '    def _sub_word(cls, w):\n'
            '        return [cls.SBOX[b] for b in w]\n\n'
            '    @classmethod\n'
            '    def _rot_word(cls, w):\n'
            '        return w[1:] + w[:1]\n\n'
            '    def _expand_key(self, key):\n'
            '        w = [list(key[4*i:4*(i+1)]) for i in range(8)]\n'
            '        for i in range(8, 60):\n'
            '            temp = list(w[i - 1])\n'
            '            if i % 8 == 0:\n'
            '                temp = [b ^ r for b, r in zip(self._sub_word(self._rot_word(temp)), [self.RCON[i // 8], 0, 0, 0])]\n'
            '            elif i % 8 == 4:\n'
            '                temp = self._sub_word(temp)\n'
            '            w.append([a ^ b for a, b in zip(w[i - 8], temp)])\n'
            '        return w\n\n'
            '    @staticmethod\n'
            '    def _xtime(a):\n'
            '        return (((a << 1) ^ 0x1b) & 0xff) if (a & 0x80) else (a << 1)\n\n'
            '    def _mix_column(self, col):\n'
            '        t = col[0] ^ col[1] ^ col[2] ^ col[3]\n'
            '        u = col[0]\n'
            '        col[0] ^= t ^ self._xtime(col[0] ^ col[1])\n'
            '        col[1] ^= t ^ self._xtime(col[1] ^ col[2])\n'
            '        col[2] ^= t ^ self._xtime(col[2] ^ col[3])\n'
            '        col[3] ^= t ^ self._xtime(col[3] ^ u)\n\n'
            '    def encrypt_block(self, block: bytes) -> bytes:\n'
            '        state = [[block[r + 4 * c] for c in range(4)] for r in range(4)]\n'
            '        for c in range(4):\n'
            '            for r in range(4):\n'
            '                state[r][c] ^= self._key_schedule[c][r]\n'
            '        for rnd in range(1, 14):\n'
            '            for r in range(4):\n'
            '                for c in range(4):\n'
            '                    state[r][c] = self.SBOX[state[r][c]]\n'
            '            state[1] = state[1][1:] + state[1][:1]\n'
            '            state[2] = state[2][2:] + state[2][:2]\n'
            '            state[3] = state[3][3:] + state[3][:3]\n'
            '            for c in range(4):\n'
            '                col = [state[r][c] for r in range(4)]\n'
            '                self._mix_column(col)\n'
            '                for r in range(4):\n'
            '                    state[r][c] = col[r]\n'
            '            for c in range(4):\n'
            '                for r in range(4):\n'
            '                    state[r][c] ^= self._key_schedule[rnd * 4 + c][r]\n'
            '        for r in range(4):\n'
            '            for c in range(4):\n'
            '                state[r][c] = self.SBOX[state[r][c]]\n'
            '        state[1] = state[1][1:] + state[1][:1]\n'
            '        state[2] = state[2][2:] + state[2][:2]\n'
            '        state[3] = state[3][3:] + state[3][:3]\n'
            '        for c in range(4):\n'
            '            for r in range(4):\n'
            '                state[r][c] ^= self._key_schedule[14 * 4 + c][r]\n'
            '        out = bytearray(16)\n'
            '        for r in range(4):\n'
            '            for c in range(4):\n'
            '                out[r + 4 * c] = state[r][c]\n'
            '        return bytes(out)\n\n\n'
            'class AES256CTR:\n'
            '    def __init__(self, key: bytes):\n'
            '        self.aes = AES256(key)\n\n'
            '    def crypt(self, data: bytes, iv: bytes) -> bytes:\n'
            '        if len(iv) != 16:\n'
            '            raise ValueError("IV must be exactly 16 bytes.")\n'
            '        counter = int.from_bytes(iv, "big")\n'
            '        out = bytearray()\n'
            '        for i in range(0, len(data), 16):\n'
            '            chunk = data[i:i+16]\n'
            '            ctr_bytes = counter.to_bytes(16, "big")\n'
            '            keystream = self.aes.encrypt_block(ctr_bytes)\n'
            '            out.extend(a ^ b for a, b in zip(chunk, keystream[:len(chunk)]))\n'
            '            counter = (counter + 1) & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF\n'
            '        return bytes(out)\n\n\n'
            'class PasswordManager:\n'
            '    ITERATIONS = 100000\n\n'
            '    def __init__(self, master_password: str, vault_path: str = "passwords.vault"):\n'
            '        if not master_password or not isinstance(master_password, str):\n'
            '            raise ValueError("Master password must be a non-empty string.")\n'
            '        self.master_password = master_password\n'
            '        self.vault_path = vault_path\n'
            '        self.salt = None\n'
            '        self.enc_key = None\n'
            '        self.mac_key = None\n'
            '        self.entries = {}\n'
            '        self._load_or_initialize()\n\n'
            '    def _derive_keys(self, salt: bytes):\n'
            '        dk = hashlib.pbkdf2_hmac("sha256", self.master_password.encode("utf-8"), salt, self.ITERATIONS, dklen=64)\n'
            '        return dk[:32], dk[32:]\n\n'
            '    def _load_or_initialize(self):\n'
            '        if not os.path.exists(self.vault_path):\n'
            '            self.salt = os.urandom(16)\n'
            '            self.enc_key, self.mac_key = self._derive_keys(self.salt)\n'
            '            self.entries = {}\n'
            '            self.save()\n'
            '            return\n'
            '        with open(self.vault_path, "r", encoding="utf-8") as f:\n'
            '            envelope = json.load(f)\n'
            '        self.salt = bytes.fromhex(envelope["salt"])\n'
            '        iv = bytes.fromhex(envelope["iv"])\n'
            '        ciphertext = bytes.fromhex(envelope["ciphertext"])\n'
            '        expected_mac = bytes.fromhex(envelope["mac"])\n'
            '        self.enc_key, self.mac_key = self._derive_keys(self.salt)\n'
            '        computed_mac = hmac.new(self.mac_key, self.salt + iv + ciphertext, hashlib.sha256).digest()\n'
            '        if not hmac.compare_digest(computed_mac, expected_mac):\n'
            '            raise PermissionError("Authentication failed: Invalid master password or corrupted vault.")\n'
            '        cipher = AES256CTR(self.enc_key)\n'
            '        plaintext = cipher.crypt(ciphertext, iv)\n'
            '        self.entries = json.loads(plaintext.decode("utf-8"))\n\n'
            '    def save(self):\n'
            '        iv = os.urandom(16)\n'
            '        plaintext = json.dumps(self.entries, indent=2).encode("utf-8")\n'
            '        cipher = AES256CTR(self.enc_key)\n'
            '        ciphertext = cipher.crypt(plaintext, iv)\n'
            '        mac = hmac.new(self.mac_key, self.salt + iv + ciphertext, hashlib.sha256).digest()\n'
            '        envelope = {\n'
            '            "version": 1,\n'
            '            "cipher": "AES-256-CTR",\n'
            '            "kdf": "PBKDF2-HMAC-SHA256",\n'
            '            "iterations": self.ITERATIONS,\n'
            '            "salt": self.salt.hex(),\n'
            '            "iv": iv.hex(),\n'
            '            "ciphertext": ciphertext.hex(),\n'
            '            "mac": mac.hex()\n'
            '        }\n'
            '        with open(self.vault_path, "w", encoding="utf-8") as f:\n'
            '            json.dump(envelope, f, indent=2)\n\n'
            '    def set_password(self, service: str, username: str, password: str):\n'
            '        if not service or not service.strip():\n'
            '            raise ValueError("Service name cannot be empty.")\n'
            '        if not password:\n'
            '            raise ValueError("Password cannot be empty.")\n'
            '        self.entries[service.strip().lower()] = {\n'
            '            "service": service.strip(),\n'
            '            "username": username.strip(),\n'
            '            "password": password\n'
            '        }\n'
            '        self.save()\n\n'
            '    def get_password(self, service: str):\n'
            '        return self.entries.get(service.strip().lower())\n\n'
            '    def list_services(self):\n'
            '        return sorted([v["service"] for v in self.entries.values()])\n\n'
            '    def delete_service(self, service: str):\n'
            '        key = service.strip().lower()\n'
            '        if key in self.entries:\n'
            '            del self.entries[key]\n'
            '            self.save()\n'
            '            return True\n'
            '        return False\n\n\n'
            'if __name__ == "__main__":\n'
            '    vault_file = "demo_passwords.vault"\n'
            '    try:\n'
            '        pm = PasswordManager("MasterSecretPassphrase!", vault_file)\n'
            '        pm.set_password("GitHub", "developer", "demo_token_value")\n'
            '        pm.set_password("Email", "user@example.com", "Correct-Horse-Battery-Staple")\n'
            '        entry = pm.get_password("github")\n'
            '        print(f"Retrieved {entry[\'service\']} password: {entry[\'password\']}")\n'
            '        print(f"All saved services: {pm.list_services()}")\n'
            '    finally:\n'
            '        if os.path.exists(vault_file):\n'
            '            os.remove(vault_file)\n'
        ),
    },
    "lru_cache": {
        "python": (
            'class Node:\n'
            '    def __init__(self, key=0, value=0):\n'
            '        self.key = key\n'
            '        self.value = value\n'
            '        self.prev = None\n'
            '        self.next = None\n\n\n'
            'class LRUCache:\n'
            '    """Least Recently Used (LRU) Cache with O(1) get and put operations."""\n'
            '    def __init__(self, capacity: int):\n'
            '        if capacity <= 0:\n'
            '            raise ValueError("Capacity must be positive.")\n'
            '        self.capacity = capacity\n'
            '        self.cache = {}\n'
            '        self.head = Node()\n'
            '        self.tail = Node()\n'
            '        self.head.next = self.tail\n'
            '        self.tail.prev = self.head\n\n'
            '    def _remove(self, node: Node):\n'
            '        p, n = node.prev, node.next\n'
            '        p.next, n.prev = n, p\n\n'
            '    def _add_to_front(self, node: Node):\n'
            '        node.prev = self.head\n'
            '        node.next = self.head.next\n'
            '        self.head.next.prev = node\n'
            '        self.head.next = node\n\n'
            '    def get(self, key: int) -> int:\n'
            '        if key not in self.cache:\n'
            '            return -1\n'
            '        node = self.cache[key]\n'
            '        self._remove(node)\n'
            '        self._add_to_front(node)\n'
            '        return node.value\n\n'
            '    def put(self, key: int, value: int) -> None:\n'
            '        if key in self.cache:\n'
            '            node = self.cache[key]\n'
            '            node.value = value\n'
            '            self._remove(node)\n'
            '            self._add_to_front(node)\n'
            '            return\n'
            '        if len(self.cache) >= self.capacity:\n'
            '            lru = self.tail.prev\n'
            '            self._remove(lru)\n'
            '            del self.cache[lru.key]\n'
            '        new_node = Node(key, value)\n'
            '        self.cache[key] = new_node\n'
            '        self._add_to_front(new_node)\n\n\n'
            'if __name__ == "__main__":\n'
            '    cache = LRUCache(2)\n'
            '    cache.put(1, 10)\n'
            '    cache.put(2, 20)\n'
            '    print("get(1):", cache.get(1))\n'
            '    cache.put(3, 30)\n'
            '    print("get(2) (evicted):", cache.get(2))\n'
        ),
    },
    "dijkstra": {
        "python": (
            'import heapq\n\n\n'
            'def dijkstra(graph, start):\n'
            '    """Computes shortest paths from start using Dijkstra\'s algorithm."""\n'
            '    if start not in graph:\n'
            '        raise ValueError(f"Start node \'{start}\' not in graph.")\n'
            '    distances = {node: float("inf") for node in graph}\n'
            '    distances[start] = 0.0\n'
            '    predecessors = {node: None for node in graph}\n'
            '    pq = [(0.0, start)]\n\n'
            '    while pq:\n'
            '        curr_dist, curr_node = heapq.heappop(pq)\n'
            '        if curr_dist > distances[curr_node]:\n'
            '            continue\n'
            '        for neighbor, weight in graph.get(curr_node, []):\n'
            '            if weight < 0:\n'
            '                raise ValueError("Negative edge weights not supported.")\n'
            '            dist = curr_dist + weight\n'
            '            if dist < distances[neighbor]:\n'
            '                distances[neighbor] = dist\n'
            '                predecessors[neighbor] = curr_node\n'
            '                heapq.heappush(pq, (dist, neighbor))\n'
            '    return distances, predecessors\n\n\n'
            'if __name__ == "__main__":\n'
            '    graph = {\n'
            '        "A": [("B", 4), ("C", 2)],\n'
            '        "B": [("A", 4), ("C", 1), ("D", 5)],\n'
            '        "C": [("A", 2), ("B", 1), ("D", 8), ("E", 10)],\n'
            '        "D": [("B", 5), ("C", 8), ("E", 2)],\n'
            '        "E": [("C", 10), ("D", 2)]\n'
            '    }\n'
            '    dists, preds = dijkstra(graph, "A")\n'
            '    print("Shortest distances from A:", dists)\n'
        ),
    },
    "reverse_linked_list": {
        "python": (
            'class ListNode:\n'
            '    def __init__(self, val=0, next=None):\n'
            '        self.val = val\n'
            '        self.next = next\n\n\n'
            'def reverse_linked_list(head):\n'
            '    """Reverses a singly linked list in-place in O(n) time and O(1) space."""\n'
            '    prev = None\n'
            '    curr = head\n'
            '    while curr is not None:\n'
            '        next_node = curr.next\n'
            '        curr.next = prev\n'
            '        prev = curr\n'
            '        curr = next_node\n'
            '    return prev\n\n\n'
            'if __name__ == "__main__":\n'
            '    head = ListNode(1, ListNode(2, ListNode(3, ListNode(4))))\n'
            '    rev = reverse_linked_list(head)\n'
            '    vals = []\n'
            '    while rev:\n'
            '        vals.append(rev.val)\n'
            '        rev = rev.next\n'
            '    print("Reversed linked list:", vals)\n'
        ),
    },
    "two_sum": {
        "python": (
            'def two_sum(nums, target):\n'
            '    """Finds two indices such that nums[i] + nums[j] == target in O(n) time."""\n'
            '    seen = {}\n'
            '    for i, num in enumerate(nums):\n'
            '        diff = target - num\n'
            '        if diff in seen:\n'
            '            return [seen[diff], i]\n'
            '        seen[num] = i\n'
            '    return []\n\n\n'
            'if __name__ == "__main__":\n'
            '    nums = [2, 7, 11, 15]\n'
            '    target = 9\n'
            '    print("Two Sum indices:", two_sum(nums, target))\n'
        ),
    },
    "dockerfile": {
        "python": (
            '# Dockerfile for Python Flask application\n'
            'FROM python:3.11-slim\n\n'
            'WORKDIR /app\n\n'
            'ENV PYTHONDONTWRITEBYTECODE=1\n'
            'ENV PYTHONUNBUFFERED=1\n'
            'ENV FLASK_APP=app.py\n\n'
            'COPY requirements.txt .\n'
            'RUN pip install --no-cache-dir -r requirements.txt\n\n'
            'COPY . .\n\n'
            'EXPOSE 5000\n\n'
            'CMD ["python", "app.py"]\n'
        ),
    },
    "password": {
        "python": ('import secrets\nimport string\n\n\n'
                   'def make_password(length=16):\n'
                   '    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"\n'
                   '    return "".join(secrets.choice(alphabet) for _ in range(length))\n\n\n'
                   'for i in range(10):\n'
                   '    print(make_password())'),
        "bash": ('#!/usr/bin/env bash\nset -euo pipefail\n\n'
                 'for i in {1..10}; do\n'
                 '    LC_ALL=C tr -dc "A-Za-z0-9!@#$%^&*" < /dev/urandom | head -c 16\n'
                 '    echo\n'
                 'done'),
        "javascript": ('const crypto = require("crypto");\n\n'
                       'function makePassword(length = 16) {\n'
                       '  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*";\n'
                       '  let out = "";\n'
                       '  for (let i = 0; i < length; i++) out += chars[crypto.randomInt(chars.length)];\n'
                       '  return out;\n}\n\n'
                       'for (let i = 0; i < 10; i++) console.log(makePassword());'),
    },
    "fizzbuzz": {
        "python": ('for n in range(1, 101):\n'
                   '    out = ""\n'
                   '    if n % 3 == 0:\n        out += "Fizz"\n'
                   '    if n % 5 == 0:\n        out += "Buzz"\n'
                   '    print(out or n)'),
        "bash": ('#!/usr/bin/env bash\nfor n in $(seq 1 100); do\n'
                 '    out=""\n'
                 '    (( n % 3 == 0 )) && out+="Fizz"\n'
                 '    (( n % 5 == 0 )) && out+="Buzz"\n'
                 '    echo "${out:-$n}"\ndone'),
    },
    "calculator": {
        "python": ('def calc(a, op, b):\n'
                   '    if op == "+":\n        return a + b\n'
                   '    if op == "-":\n        return a - b\n'
                   '    if op == "*":\n        return a * b\n'
                   '    if op == "/":\n'
                   '        return a / b if b else "cannot divide by zero"\n'
                   '    return "unknown operator"\n\n\n'
                   'expr = input("enter like: 2 + 3 ").split()\n'
                   'print(calc(float(expr[0]), expr[1], float(expr[2])))'),
    },
    "dice": {
        "python": ('import random\n\n\n'
                   'rolls = [random.randint(1, 6) for _ in range(5)]\n'
                   'print("rolls:", rolls, "total:", sum(rolls))'),
        "bash": ('#!/usr/bin/env bash\n'
                 'for i in {1..5}; do\n'
                 '    echo $((RANDOM % 6 + 1))\ndone'),
    },
    "reverse_string": {
        "python": ('def reverse_string(s):\n'
                   '    return s[::-1]\n\n\n'
                   'text = input("enter a string: ")\n'
                   'print(reverse_string(text))'),
        "java": ('public class Main {\n'
                 '    public static String reverseString(String s) {\n'
                 '        return new StringBuilder(s).reverse().toString();\n'
                 '    }\n\n'
                 '    public static void main(String[] args) {\n'
                 '        System.out.println(reverseString("Hello World"));\n'
                 '    }\n}'),
        "kotlin": ('fun reverseString(s: String): String = s.reversed()\n\n'
                   'fun main() {\n'
                   '    println(reverseString("Hello World"))\n'
                   '}'),
        "javascript": ('function reverseString(s) {\n'
                       '  return s.split("").reverse().join("");\n'
                       '}\n\n'
                       'console.log(reverseString("Hello World"));'),
        "cpp": ('#include <algorithm>\n#include <iostream>\n'
                '#include <string>\n\n'
                'int main() {\n'
                '    std::string s = "Hello World";\n'
                '    std::reverse(s.begin(), s.end());\n'
                '    std::cout << s << "\\n";\n'
                '    return 0;\n}'),
        "c": ('#include <stdio.h>\n#include <string.h>\n\n'
              'int main(void) {\n'
              '    char s[] = "Hello World";\n'
              '    int n = strlen(s);\n'
              '    for (int i = 0; i < n / 2; i++) {\n'
              '        char t = s[i];\n'
              '        s[i] = s[n - 1 - i];\n'
              '        s[n - 1 - i] = t;\n'
              '    }\n'
              '    printf("%s\\n", s);\n'
              '    return 0;\n}'),
        "bash": ('#!/usr/bin/env bash\n'
                 'read -rp "enter a string: " s\n'
                 'echo "$s" | rev'),
    },
    "binary_search": {
        "python": ('def binary_search(arr, target):\n'
                   '    left, right = 0, len(arr) - 1\n'
                   '    while left <= right:\n'
                   '        mid = (left + right) // 2\n'
                   '        if arr[mid] == target:\n'
                   '            return mid\n'
                   '        elif arr[mid] < target:\n'
                   '            left = mid + 1\n'
                   '        else:\n'
                   '            right = mid - 1\n'
                   '    return -1\n\n\n'
                   'nums = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91]\n'
                   'target = 23\n'
                   'idx = binary_search(nums, target)\n'
                   'print(f"Target {target} found at index: {idx}")'),
        "javascript": ('function binarySearch(arr, target) {\n'
                       '  let left = 0, right = arr.length - 1;\n'
                       '  while (left <= right) {\n'
                       '    const mid = Math.floor((left + right) / 2);\n'
                       '    if (arr[mid] === target) return mid;\n'
                       '    else if (arr[mid] < target) left = mid + 1;\n'
                       '    else right = mid - 1;\n'
                       '  }\n'
                       '  return -1;\n'
                       '}\n\n'
                       'const nums = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91];\n'
                       'console.log("Index:", binarySearch(nums, 23));'),
        "cpp": ('#include <iostream>\n#include <vector>\n\n'
                'int binary_search(const std::vector<int>& arr, int target) {\n'
                '    int left = 0, right = arr.size() - 1;\n'
                '    while (left <= right) {\n'
                '        int mid = left + (right - left) / 2;\n'
                '        if (arr[mid] == target) return mid;\n'
                '        if (arr[mid] < target) left = mid + 1;\n'
                '        else right = mid - 1;\n'
                '    }\n'
                '    return -1;\n}\n\n'
                'int main() {\n'
                '    std::vector<int> nums = {2, 5, 8, 12, 16, 23, 38, 56, 72, 91};\n'
                '    std::cout << "Index: " << binary_search(nums, 23) << "\\n";\n'
                '    return 0;\n}'),
        "c": ('#include <stdio.h>\n\n'
              'int binary_search(int arr[], int n, int target) {\n'
              '    int left = 0, right = n - 1;\n'
              '    while (left <= right) {\n'
              '        int mid = left + (right - left) / 2;\n'
              '        if (arr[mid] == target) return mid;\n'
              '        if (arr[mid] < target) left = mid + 1;\n'
              '        else right = mid - 1;\n'
              '    }\n'
              '    return -1;\n}\n\n'
              'int main(void) {\n'
              '    int nums[] = {2, 5, 8, 12, 16, 23, 38, 56, 72, 91};\n'
              '    printf("Index: %d\\n", binary_search(nums, 10, 23));\n'
              '    return 0;\n}'),
        "java": ('public class Main {\n'
                 '    public static int binarySearch(int[] arr, int target) {\n'
                 '        int left = 0, right = arr.length - 1;\n'
                 '        while (left <= right) {\n'
                 '            int mid = left + (right - left) / 2;\n'
                 '            if (arr[mid] == target) return mid;\n'
                 '            if (arr[mid] < target) left = mid + 1;\n'
                 '            else right = mid - 1;\n'
                 '        }\n'
                 '        return -1;\n'
                 '    }\n\n'
                 '    public static void main(String[] args) {\n'
                 '        int[] nums = {2, 5, 8, 12, 16, 23, 38, 56, 72, 91};\n'
                 '        System.out.println("Index: " + binarySearch(nums, 23));\n'
                 '    }\n}'),
    },
    "even_check": {
        "python": ('def is_even(n):\n'
                   '    return n % 2 == 0\n\n\n'
                   'for n in (4, 7, 10):\n'
                   '    print(n, "even" if is_even(n) else "odd")'),
        "java": ('public class Main {\n'
                 '    public static boolean isEven(int n) {\n'
                 '        return n % 2 == 0;\n'
                 '    }\n\n'
                 '    public static void main(String[] args) {\n'
                 '        int[] test = {4, 7, 10};\n'
                 '        for (int n : test) {\n'
                 '            System.out.println(n + " " + (isEven(n) ? "even" : "odd"));\n'
                 '        }\n    }\n}'),
        "kotlin": ('fun isEven(n: Int): Boolean = n % 2 == 0\n\n'
                   'fun main() {\n'
                   '    for (n in listOf(4, 7, 10)) {\n'
                   '        println("$n " + if (isEven(n)) "even" else "odd")\n'
                   '    }\n}'),
        "javascript": ('function isEven(n) {\n'
                       '  return n % 2 === 0;\n'
                       '}\n\n'
                       '[4, 7, 10].forEach((n) => console.log(n, isEven(n) ? "even" : "odd"));'),
        "cpp": ('#include <iostream>\n\n'
                'bool isEven(int n) {\n'
                '    return n % 2 == 0;\n'
                '}\n\n'
                'int main() {\n'
                '    for (int n : {4, 7, 10}) {\n'
                '        std::cout << n << " " << (isEven(n) ? "even" : "odd") << "\\n";\n'
                '    }\n'
                '    return 0;\n}'),
        "c": ('#include <stdio.h>\n\n'
              'int is_even(int n) {\n'
              '    return n % 2 == 0;\n'
              '}\n\n'
              'int main(void) {\n'
              '    int test[] = {4, 7, 10};\n'
              '    for (int i = 0; i < 3; i++) {\n'
              '        printf("%d %s\\n", test[i], is_even(test[i]) ? "even" : "odd");\n'
              '    }\n'
              '    return 0;\n}'),
    },
    "factorial": {
        "python": ('def factorial(n):\n'
                   '    result = 1\n'
                   '    for i in range(2, n + 1):\n'
                   '        result *= i\n'
                   '    return result\n\n\n'
                   'print(factorial(10))'),
        "cpp": ('#include <iostream>\n\n'
                'long long factorial(int n) {\n'
                '    long long result = 1;\n'
                '    for (int i = 2; i <= n; i++) {\n'
                '        result *= i;\n'
                '    }\n'
                '    return result;\n'
                '}\n\n'
                'int main() {\n'
                '    std::cout << "10! = " << factorial(10) << "\\n";\n'
                '    return 0;\n}'),
        "c": ('#include <stdio.h>\n\n'
              'long long factorial(int n) {\n'
              '    long long result = 1;\n'
              '    for (int i = 2; i <= n; i++) {\n'
              '        result *= i;\n'
              '    }\n'
              '    return result;\n'
              '}\n\n'
              'int main(void) {\n'
              '    printf("10! = %lld\\n", factorial(10));\n'
              '    return 0;\n}'),
        "java": ('public class Main {\n'
                 '    public static long factorial(int n) {\n'
                 '        long result = 1;\n'
                 '        for (int i = 2; i <= n; i++) {\n'
                 '            result *= i;\n'
                 '        }\n'
                 '        return result;\n'
                 '    }\n\n'
                 '    public static void main(String[] args) {\n'
                 '        System.out.println("10! = " + factorial(10));\n'
                 '    }\n}'),
        "kotlin": ('fun factorial(n: Int): Long {\n'
                   '    var result = 1L\n'
                   '    for (i in 2..n) {\n'
                   '        result *= i\n'
                   '    }\n'
                   '    return result\n'
                   '}\n\n'
                   'fun main() {\n'
                   '    println("10! = " + factorial(10))\n'
                   '}'),
        "javascript": ('function factorial(n) {\n'
                       '  let result = 1;\n'
                       '  for (let i = 2; i <= n; i++) result *= i;\n'
                       '  return result;\n'
                       '}\n\n'
                       'console.log("10! =", factorial(10));'),
    },
    "primes": {
        "python": ('def primes_up_to(limit):\n'
                   '    found = []\n'
                   '    for n in range(2, limit + 1):\n'
                   '        if all(n % p for p in range(2, int(n ** 0.5) + 1)):\n'
                   '            found.append(n)\n'
                   '    return found\n\n\n'
                   'print(primes_up_to(50))'),
        "java": ('public class Main {\n'
                 '    public static boolean isPrime(int n) {\n'
                 '        if (n < 2) return false;\n'
                 '        for (int i = 2; i * i <= n; i++) {\n'
                 '            if (n % i == 0) return false;\n'
                 '        }\n'
                 '        return true;\n'
                 '    }\n\n'
                 '    public static void main(String[] args) {\n'
                 '        for (int n = 2; n <= 50; n++) {\n'
                 '            if (isPrime(n)) System.out.print(n + " ");\n'
                 '        }\n'
                 '        System.out.println();\n'
                 '    }\n}'),
        "cpp": ('#include <iostream>\n\n'
                'bool isPrime(int n) {\n'
                '    if (n < 2) return false;\n'
                '    for (int i = 2; i * i <= n; i++) {\n'
                '        if (n % i == 0) return false;\n'
                '    }\n'
                '    return true;\n'
                '}\n\n'
                'int main() {\n'
                '    for (int n = 2; n <= 50; n++) {\n'
                '        if (isPrime(n)) std::cout << n << " ";\n'
                '    }\n'
                '    std::cout << "\\n";\n'
                '    return 0;\n}'),
        "javascript": ('function isPrime(n) {\n'
                       '  if (n < 2) return false;\n'
                       '  for (let i = 2; i * i <= n; i++) {\n'
                       '    if (n % i === 0) return false;\n'
                       '  }\n'
                       '  return true;\n'
                       '}\n\n'
                       'const primes = [];\n'
                       'for (let n = 2; n <= 50; n++) if (isPrime(n)) primes.push(n);\n'
                       'console.log(primes.join(" "));'),
        "bash": ('#!/usr/bin/env bash\n'
                 'for n in $(seq 2 50); do\n'
                 '    is_prime=1\n'
                 '    for ((i = 2; i * i <= n; i++)); do\n'
                 '        (( n % i == 0 )) && is_prime=0 && break\n'
                 '    done\n'
                 '    (( is_prime )) && printf "%s " "$n"\ndone\necho'),
    },
    "sieve": {
        "python": ('def sieve_of_eratosthenes(n: int) -> list[int]:\n'
                   '    """Finds all prime numbers up to n using the Sieve of Eratosthenes."""\n'
                   '    if not isinstance(n, int):\n'
                   '        raise TypeError(f"Input must be an integer, got {type(n).__name__}")\n'
                   '    if n < 2:\n'
                   '        return []\n\n'
                   '    is_prime = [True] * (n + 1)\n'
                   '    is_prime[0] = is_prime[1] = False\n\n'
                   '    limit = int(n ** 0.5)\n'
                   '    for p in range(2, limit + 1):\n'
                   '        if is_prime[p]:\n'
                   '            for multiple in range(p * p, n + 1, p):\n'
                   '                is_prime[multiple] = False\n\n'
                   '    return [i for i, prime in enumerate(is_prime) if prime]\n\n\n'
                   'if __name__ == "__main__":\n'
                   '    test_cases = [30, 10, 1, 2, -5]\n'
                   '    print("=== Sieve of Eratosthenes Prime Finder ===")\n'
                   '    for val in test_cases:\n'
                   '        primes = sieve_of_eratosthenes(val)\n'
                   '        print(f"Primes up to {val:2d} ({len(primes):2d} total): {primes}")'),
        "java": ('import java.util.ArrayList;\n'
                 'import java.util.Arrays;\n'
                 'import java.util.List;\n\n'
                 'public class Main {\n'
                 '    public static List<Integer> sieveOfEratosthenes(int n) {\n'
                 '        if (n < 2) return new ArrayList<>();\n'
                 '        boolean[] isPrime = new boolean[n + 1];\n'
                 '        Arrays.fill(isPrime, true);\n'
                 '        isPrime[0] = isPrime[1] = false;\n'
                 '        for (int p = 2; p * p <= n; p++) {\n'
                 '            if (isPrime[p]) {\n'
                 '                for (int m = p * p; m <= n; m += p) {\n'
                 '                    isPrime[m] = false;\n'
                 '                }\n'
                 '            }\n'
                 '        }\n'
                 '        List<Integer> primes = new ArrayList<>();\n'
                 '        for (int i = 2; i <= n; i++) {\n'
                 '            if (isPrime[i]) primes.add(i);\n'
                 '        }\n'
                 '        return primes;\n'
                 '    }\n\n'
                 '    public static void main(String[] args) {\n'
                 '        System.out.println("Primes up to 30: " + sieveOfEratosthenes(30));\n'
                 '    }\n}'),
        "cpp": ('#include <iostream>\n#include <vector>\n\n'
                'std::vector<int> sieve(int n) {\n'
                '    if (n < 2) return {};\n'
                '    std::vector<bool> isPrime(n + 1, true);\n'
                '    isPrime[0] = isPrime[1] = false;\n'
                '    for (int p = 2; p * p <= n; p++) {\n'
                '        if (isPrime[p]) {\n'
                '            for (int m = p * p; m <= n; m += p) isPrime[m] = false;\n'
                '        }\n'
                '    }\n'
                '    std::vector<int> primes;\n'
                '    for (int i = 2; i <= n; i++) if (isPrime[i]) primes.push_back(i);\n'
                '    return primes;\n'
                '}\n\n'
                'int main() {\n'
                '    auto primes = sieve(30);\n'
                '    std::cout << "Primes up to 30: ";\n'
                '    for (int p : primes) std::cout << p << " ";\n'
                '    std::cout << "\\n";\n'
                '    return 0;\n}'),
        "javascript": ('function sieveOfEratosthenes(n) {\n'
                       '  if (typeof n !== "number" || n < 2) return [];\n'
                       '  const isPrime = new Array(n + 1).fill(true);\n'
                       '  isPrime[0] = isPrime[1] = false;\n'
                       '  for (let p = 2; p * p <= n; p++) {\n'
                       '    if (isPrime[p]) {\n'
                       '      for (let m = p * p; m <= n; m += p) isPrime[m] = false;\n'
                       '    }\n'
                       '  }\n'
                       '  const primes = [];\n'
                       '  for (let i = 2; i <= n; i++) if (isPrime[i]) primes.push(i);\n'
                       '  return primes;\n'
                       '}\n\n'
                       'console.log("Primes up to 30:", sieveOfEratosthenes(30));'),
    },
    "kth_largest": {
        "java": ('import java.util.Arrays;\n'
                 'import java.util.PriorityQueue;\n\n'
                 'public class Main {\n\n'
                 '    /**\n'
                 '     * Finds the k-th largest element in an unsorted array using a Min-Heap.\n'
                 '     * Operates in O(N log k) time without sorting the entire array.\n'
                 '     */\n'
                 '    public static int findKthLargest(int[] nums, int k) {\n'
                 '        if (nums == null || nums.length == 0) {\n'
                 '            throw new IllegalArgumentException("Array must not be null or empty.");\n'
                 '        }\n'
                 '        if (k <= 0 || k > nums.length) {\n'
                 '            throw new IllegalArgumentException("k must be between 1 and array length (" + nums.length + "). Got: " + k);\n'
                 '        }\n\n'
                 '        PriorityQueue<Integer> minHeap = new PriorityQueue<>(k);\n'
                 '        for (int num : nums) {\n'
                 '            minHeap.offer(num);\n'
                 '            if (minHeap.size() > k) {\n'
                 '                minHeap.poll();\n'
                 '            }\n'
                 '        }\n'
                 '        return minHeap.peek();\n'
                 '    }\n\n'
                 '    public static void main(String[] args) {\n'
                 '        System.out.println("=== K-th Largest Element Finder (Min-Heap) ===");\n\n'
                 '        int[] arr1 = {3, 2, 1, 5, 6, 4};\n'
                 '        int k1 = 2;\n'
                 '        System.out.printf("Array: %s | k = %d -> %d-th largest: %d\\n",\n'
                 '                Arrays.toString(arr1), k1, k1, findKthLargest(arr1, k1));\n\n'
                 '        int[] arr2 = {3, 2, 3, 1, 2, 4, 5, 5, 6};\n'
                 '        int k2 = 4;\n'
                 '        System.out.printf("Array: %s | k = %d -> %d-th largest: %d\\n",\n'
                 '                Arrays.toString(arr2), k2, k2, findKthLargest(arr2, k2));\n\n'
                 '        int[] arr3 = {7, 10, 4, 3, 20, 15};\n'
                 '        int k3 = 1;\n'
                 '        System.out.printf("Array: %s | k = %d -> %d-th largest: %d\\n",\n'
                 '                Arrays.toString(arr3), k3, k3, findKthLargest(arr3, k3));\n\n'
                 '        try {\n'
                 '            findKthLargest(new int[]{}, 1);\n'
                 '        } catch (IllegalArgumentException e) {\n'
                 '            System.out.println("Handled empty array: " + e.getMessage());\n'
                 '        }\n'
                 '    }\n}'),
        "python": ('import heapq\n\n'
                   'def find_kth_largest(nums: list[int], k: int) -> int:\n'
                   '    """Finds the k-th largest element using a min-heap in O(N log k) time."""\n'
                   '    if not nums:\n'
                   '        raise ValueError("Array must not be empty.")\n'
                   '    if not (1 <= k <= len(nums)):\n'
                   '        raise ValueError(f"k must be between 1 and {len(nums)}, got {k}")\n'
                   '    min_heap = []\n'
                   '    for num in nums:\n'
                   '        heapq.heappush(min_heap, num)\n'
                   '        if len(min_heap) > k:\n'
                   '            heapq.heappop(min_heap)\n'
                   '    return min_heap[0]\n\n\n'
                   'if __name__ == "__main__":\n'
                   '    arr = [3, 2, 1, 5, 6, 4]\n'
                   '    k = 2\n'
                   '    print(f"Array: {arr}, k={k} -> {k}-th largest: {find_kth_largest(arr, k)}")'),
        "cpp": ('#include <iostream>\n#include <vector>\n#include <queue>\n#include <stdexcept>\n\n'
                'int findKthLargest(const std::vector<int>& nums, int k) {\n'
                '    if (nums.empty() || k <= 0 || k > static_cast<int>(nums.size())) {\n'
                '        throw std::invalid_argument("Invalid array or k");\n'
                '    }\n'
                '    std::priority_queue<int, std::vector<int>, std::greater<int>> minHeap;\n'
                '    for (int num : nums) {\n'
                '        minHeap.push(num);\n'
                '        if (static_cast<int>(minHeap.size()) > k) minHeap.pop();\n'
                '    }\n'
                '    return minHeap.top();\n'
                '}\n\n'
                'int main() {\n'
                '    std::vector<int> nums = {3, 2, 1, 5, 6, 4};\n'
                '    std::cout << "2nd largest: " << findKthLargest(nums, 2) << "\\n";\n'
                '    return 0;\n}'),
    },
    "swap": {
        "python": ('a = int(input("a: "))\n'
                   'b = int(input("b: "))\n'
                   'a, b = b, a\n'
                   'print("after swap: a =", a, "b =", b)'),
        "c": ('#include <stdio.h>\n\n'
              'int main(void) {\n'
              '    int a = 5, b = 9, t;\n'
              '    printf("before: a = %d b = %d\\n", a, b);\n'
              '    t = a;\n'
              '    a = b;\n'
              '    b = t;\n'
              '    printf("after:  a = %d b = %d\\n", a, b);\n'
              '    return 0;\n}'),
        "cpp": ('#include <iostream>\n#include <utility>\n\n'
                'int main() {\n'
                '    int a = 5, b = 9;\n'
                '    std::cout << "before: a = " << a << " b = " << b << "\\n";\n'
                '    std::swap(a, b);\n'
                '    std::cout << "after:  a = " << a << " b = " << b << "\\n";\n'
                '    return 0;\n}'),
        "java": ('public class Main {\n'
                 '    public static void main(String[] args) {\n'
                 '        int a = 5, b = 9, t;\n'
                 '        System.out.println("before: a = " + a + " b = " + b);\n'
                 '        t = a;\n'
                 '        a = b;\n'
                 '        b = t;\n'
                 '        System.out.println("after:  a = " + a + " b = " + b);\n'
                 '    }\n}'),
        "kotlin": ('fun main() {\n'
                   '    var a = 5\n'
                   '    var b = 9\n'
                   '    println("before: a = $a b = $b")\n'
                   '    val t = a\n'
                   '    a = b\n'
                   '    b = t\n'
                   '    println("after swap: a = $a b = $b")\n'
                   '}'),
        "javascript": ('let a = 5;\n'
                       'let b = 9;\n'
                       'console.log("before swap: a =", a, "b =", b);\n'
                       '[a, b] = [b, a];\n'
                       'console.log("after swap: a =", a, "b =", b);'),
    },
    "count_words": {
        "python": ('from collections import Counter\nimport re\n\n'
                   'with open("input.txt") as f:\n'
                   '    text = f.read()\n\n'
                   'words = re.findall(r"\\w+", text.lower())\n'
                   'print("total words:", len(words))\n'
                   'for word, count in Counter(words).most_common(10):\n'
                   '    print(word, count)'),
        "bash": '#!/usr/bin/env bash\nwc -w < "$1"',
    },
    "sort_numbers": {
        "python": ('numbers = [5, 3, 9, 1, 7]\n'
                   'numbers.sort()\n'
                   'print("sorted:", numbers)\n'
                   'print("descending:", sorted(numbers, reverse=True))'),
        "javascript": ('const numbers = [5, 3, 9, 1, 7];\n'
                       'const sorted = [...numbers].sort((a, b) => a - b);\n'
                       'console.log("sorted:", sorted.join(" "));'),
        "cpp": ('#include <algorithm>\n#include <iostream>\n#include <vector>\n\n'
                'int main() {\n'
                '    std::vector<int> numbers = {5, 3, 9, 1, 7};\n'
                '    std::sort(numbers.begin(), numbers.end());\n'
                '    for (int n : numbers) {\n'
                '        std::cout << n << " ";\n'
                '    }\n'
                '    std::cout << "\\n";\n'
                '    return 0;\n}'),
        "java": ('import java.util.Arrays;\n\n'
                 'public class Main {\n'
                 '    public static void main(String[] args) {\n'
                 '        int[] numbers = {5, 3, 9, 1, 7};\n'
                 '        Arrays.sort(numbers);\n'
                 '        System.out.println(Arrays.toString(numbers));\n'
                 '    }\n}'),
    },
    "add_two": {
        "python": 'a = 4\nb = 7\nprint("sum:", a + b)',
        "kotlin": ('fun addTwoNumbers(a: Int, b: Int): Int {\n'
                   '    return a + b\n'
                   '}\n\n'
                   'fun main() {\n'
                   '    println("sum: " + addTwoNumbers(4, 7))\n'
                   '}'),
        "java": ('public class Main {\n'
                 '    public static int addTwoNumbers(int a, int b) {\n'
                 '        return a + b;\n'
                 '    }\n\n'
                 '    public static void main(String[] args) {\n'
                 '        System.out.println("sum: " + addTwoNumbers(4, 7));\n'
                 '    }\n}'),
        "cpp": ('#include <iostream>\n\n'
                'int main() {\n'
                '    int a = 4, b = 7;\n'
                '    std::cout << "sum: " << a + b << "\\n";\n'
                '    return 0;\n}'),
        "c": ('#include <stdio.h>\n\n'
              'int main(void) {\n'
              '    int a = 4, b = 7;\n'
              '    printf("sum: %d\\n", a + b);\n'
              '    return 0;\n}'),
        "javascript": 'const a = 4, b = 7;\nconsole.log("sum:", a + b);',
        "bash": ('#!/usr/bin/env bash\n'
                 'a=4\nb=7\necho "sum: $((a + b))"'),
    },
    "sum_list": {
        "python": ('numbers = [4, 8, 15, 16, 23, 42]\n'
                   'print("sum:", sum(numbers))\n'
                   'print("average:", sum(numbers) / len(numbers))'),
        "javascript": ('const numbers = [4, 8, 15, 16, 23, 42];\n'
                       'const total = numbers.reduce((acc, n) => acc + n, 0);\n'
                       'console.log("sum:", total);\n'
                       'console.log("average:", total / numbers.length);'),
        "java": ('public class Main {\n'
                 '    public static void main(String[] args) {\n'
                 '        int[] numbers = {4, 8, 15, 16, 23, 42};\n'
                 '        int sum = 0;\n'
                 '        for (int n : numbers) {\n'
                 '            sum += n;\n'
                 '        }\n'
                 '        System.out.println("sum: " + sum);\n'
                 '    }\n}'),
        "kotlin": ('fun main() {\n'
                   '    val numbers = listOf(4, 8, 15, 16, 23, 42)\n'
                   '    println("sum: ${numbers.sum()}")\n'
                   '    println("average: ${numbers.average()}")\n'
                   '}'),
        "cpp": ('#include <iostream>\n#include <numeric>\n'
                '#include <vector>\n\n'
                'int main() {\n'
                '    std::vector<int> numbers = {4, 8, 15, 16, 23, 42};\n'
                '    int sum = 0;\n'
                '    for (int n : numbers) {\n'
                '        sum += n;\n'
                '    }\n'
                '    std::cout << "sum: " << sum << "\\n";\n'
                '    return 0;\n}'),
    },
    "multiplication_table": {
        "python": ('n = 7\n'
                   'for i in range(1, 11):\n'
                   '    print(f"{n} x {i} = {n * i}")'),
        "java": ('public class Main {\n'
                 '    public static void main(String[] args) {\n'
                 '        int n = 7;\n'
                 '        for (int i = 1; i <= 10; i++) {\n'
                 '            System.out.println(n + " x " + i + " = " + (n * i));\n'
                 '        }\n    }\n}'),
        "cpp": ('#include <iostream>\n\n'
                'int main() {\n'
                '    int n = 7;\n'
                '    for (int i = 1; i <= 10; i++) {\n'
                '        std::cout << n << " x " << i << " = " << n * i << "\\n";\n'
                '    }\n'
                '    return 0;\n}'),
        "bash": ('#!/usr/bin/env bash\n'
                 'n=7\n'
                 'for i in $(seq 1 10); do\n'
                 '    echo "$n x $i = $((n * i))"\ndone'),
    },
    "palindrome": {
        "python": ('def is_palindrome(text):\n'
                   '    clean = "".join(c.lower() for c in text if c.isalnum())\n'
                   '    return clean == clean[::-1]\n\n\n'
                   'for word in ("racecar", "hello"):\n'
                   '    print(word, "->", is_palindrome(word))'),
        "java": ('public class Main {\n'
                 '    public static boolean isPalindrome(String s) {\n'
                 '        String clean = s.toLowerCase().replaceAll("[^a-z0-9]", "");\n'
                 '        return clean.equals(new StringBuilder(clean).reverse().toString());\n'
                 '    }\n\n'
                 '    public static void main(String[] args) {\n'
                 '        for (String word : new String[]{"racecar", "hello"}) {\n'
                 '            System.out.println(word + " -> " + isPalindrome(word));\n'
                 '        }\n    }\n}'),
        "cpp": ('#include <algorithm>\n#include <cctype>\n'
                '#include <iostream>\n#include <string>\n\n'
                'bool isPalindrome(std::string s) {\n'
                '    std::string clean;\n'
                '    for (char c : s) {\n'
                '        if (std::isalnum((unsigned char)c)) clean += std::tolower((unsigned char)c);\n'
                '    }\n'
                '    std::string rev = clean;\n'
                '    std::reverse(rev.begin(), rev.end());\n'
                '    return clean == rev;\n'
                '}\n\n'
                'int main() {\n'
                '    for (std::string w : {"racecar", "hello"}) {\n'
                '        std::cout << w << " -> " << (isPalindrome(w) ? "true" : "false") << "\\n";\n'
                '    }\n'
                '    return 0;\n}'),
        "javascript": ('function isPalindrome(word) {\n'
                       '  return word === word.split("").reverse().join("");\n'
                       '}\n\n'
                       'console.log(isPalindrome("racecar"));'),
        "kotlin": ('fun isPalindrome(word: String): Boolean {\n'
                   '    return word == word.reversed()\n'
                   '}\n\n'
                   'fun main() {\n'
                   '    for (word in listOf("racecar", "hello")) {\n'
                   '        println("$word -> ${isPalindrome(word)}")\n'
                   '    }\n}'),
    },
    "fibonacci": {
        "python": ('def fibonacci(n):\n'
                   '    a, b = 0, 1\n'
                   '    for _ in range(n):\n'
                   '        a, b = b, a + b\n'
                   '    return a\n\n\n'
                   'print([fibonacci(i) for i in range(10)])'),
        "java": ('public class Main {\n'
                 '    public static int fibonacci(int n) {\n'
                 '        int a = 0, b = 1;\n'
                 '        for (int i = 0; i < n; i++) {\n'
                 '            int t = a + b;\n'
                 '            a = b;\n'
                 '            b = t;\n'
                 '        }\n'
                 '        return a;\n'
                 '    }\n\n'
                 '    public static void main(String[] args) {\n'
                 '        for (int i = 0; i < 10; i++) System.out.print(fibonacci(i) + " ");\n'
                 '        System.out.println();\n'
                 '    }\n}'),
        "javascript": ('function fibonacci(n) {\n'
                       '  let a = 0, b = 1;\n'
                       '  for (let i = 0; i < n; i++) [a, b] = [b, a + b];\n'
                       '  return a;\n'
                       '}\n\n'
                       'console.log(Array.from({ length: 10 }, (_, i) => fibonacci(i)).join(" "));'),
        "cpp": ('#include <iostream>\n\n'
                'int fibonacci(int n) {\n'
                '    int a = 0, b = 1;\n'
                '    for (int i = 0; i < n; i++) {\n'
                '        int t = a + b;\n'
                '        a = b;\n'
                '        b = t;\n'
                '    }\n'
                '    return a;\n'
                '}\n\n'
                'int main() {\n'
                '    for (int i = 0; i < 10; i++) std::cout << fibonacci(i) << " ";\n'
                '    std::cout << "\\n";\n'
                '    return 0;\n}'),
        "kotlin": ('fun fibonacci(n: Int): Int {\n'
                   '    var a = 0\n'
                   '    var b = 1\n'
                   '    repeat(n) {\n'
                   '        val t = a + b\n'
                   '        a = b\n'
                   '        b = t\n'
                   '    }\n'
                   '    return a\n'
                   '}\n\n'
                   'fun main() {\n'
                   '    for (i in 0 until 10) println(fibonacci(i))\n'
                   '}'),
    },
    "leap_year": {
        "python": ('def is_leap_year(year):\n'
                   '    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)\n\n\n'
                   'for y in (2024, 2025, 2000, 1900):\n'
                   '    print(y, "->", is_leap_year(y))'),
        "cpp": ('#include <iostream>\n\n'
                'bool isLeapYear(int y) {\n'
                '    return y % 4 == 0 && (y % 100 != 0 || y % 400 == 0);\n'
                '}\n\n'
                'int main() {\n'
                '    for (int y : {2024, 2025, 2000, 1900}) {\n'
                '        std::cout << y << " -> " << (isLeapYear(y) ? "true" : "false") << "\\n";\n'
                '    }\n'
                '    return 0;\n}'),
    },
    "largest_of": {
        "python": ('numbers = [12, 45, 7, 89, 23]\n'
                   'print("largest:", max(numbers))\n'
                   'print("smallest:", min(numbers))'),
        "javascript": ('const numbers = [12, 45, 7, 89, 23];\n'
                       'console.log("largest:", Math.max(...numbers));\n'
                       'console.log("smallest:", Math.min(...numbers));'),
        "java": ('public class Main {\n'
                 '    public static void main(String[] args) {\n'
                 '        int[] numbers = {12, 45, 7, 89, 23};\n'
                 '        int largest = numbers[0];\n'
                 '        for (int n : numbers) {\n'
                 '            if (n > largest) {\n'
                 '                largest = n;\n'
                 '            }\n'
                 '        }\n'
                 '        System.out.println("largest: " + largest);\n'
                 '    }\n}'),
        "kotlin": ('fun main() {\n'
                   '    val numbers = listOf(12, 45, 7, 89, 23)\n'
                   '    println("largest: ${numbers.max()}")\n'
                   '    println("smallest: ${numbers.min()}")\n'
                   '}'),
        "cpp": ('#include <algorithm>\n#include <iostream>\n'
                '#include <vector>\n\n'
                'int main() {\n'
                '    std::vector<int> numbers = {12, 45, 7, 89, 23};\n'
                '    std::cout << "largest: "\n'
                '              << *std::max_element(numbers.begin(), numbers.end())\n'
                '              << "\\n";\n'
                '    return 0;\n}'),
        "c": ('#include <stdio.h>\n\n'
              'int main(void) {\n'
              '    int numbers[] = {12, 45, 7, 89, 23};\n'
              '    int n = 5, largest = numbers[0];\n'
              '    for (int i = 1; i < n; i++) {\n'
              '        if (numbers[i] > largest) {\n'
              '            largest = numbers[i];\n'
              '        }\n'
              '    }\n'
              '    printf("largest: %d\\n", largest);\n'
              '    return 0;\n}'),
    },
    "vowels": {
        "python": ('text = "Hello from TenSeiAi"\n'
                   'vowels = "aeiou"\n'
                   'found = [c for c in text.lower() if c in vowels]\n'
                   'print("vowels:", len(found), "->", "".join(found))'),
    },
    "list_files": {
        "python": ('import os\n\n'
                   'folder = "."\n'
                   'for name in sorted(os.listdir(folder)):\n'
                   '    print(name)'),
        "bash": ('#!/usr/bin/env bash\n'
                 'folder="${1:-.}"\n'
                 'ls -lah "$folder"'),
    },
    "make_dir": {
        "python": ('import os\n\n'
                   'os.makedirs("Tensei", exist_ok=True)\n'
                   'print("created ./Tensei")'),
        "java": ('import java.nio.file.Files;\n'
                 'import java.nio.file.Paths;\n\n'
                 'public class Main {\n'
                 '    public static void main(String[] args) throws Exception {\n'
                 '        Files.createDirectories(Paths.get("Tensei"));\n'
                 '        System.out.println("created ./Tensei");\n'
                 '    }\n}'),
        "kotlin": ('import java.io.File\n\n'
                   'fun main() {\n'
                   '    val dir = File("Tensei")\n'
                   '    if (dir.exists()) {\n'
                   '        println("already exists: ./Tensei")\n'
                   '    } else {\n'
                   '        dir.mkdirs()\n'
                   '        println("created ./Tensei")\n'
                   '    }\n}'),
        "cpp": ('#include <filesystem>\n#include <iostream>\n\n'
                'int main() {\n'
                '    std::filesystem::create_directories("Tensei");\n'
                '    std::cout << "created ./Tensei\\n";\n'
                '    return 0;\n}'),
        "c": ('#include <stdio.h>\n#include <sys/stat.h>\n\n'
              'int main(void) {\n'
              '    if (mkdir("Tensei", 0755) == 0) {\n'
              '        printf("created ./Tensei\\n");\n'
              '    } else {\n'
              '        printf("already exists: ./Tensei\\n");\n'
              '    }\n'
              '    return 0;\n}'),
        "javascript": ('const fs = require("fs");\n\n'
                       'fs.mkdirSync("Tensei", { recursive: true });\n'
                       'console.log("created ./Tensei");'),
        "bash": ('#!/usr/bin/env bash\n'
                 'mkdir -p "Tensei"\n'
                 'echo "created ./Tensei"'),
    },
    "recursion": {
        "python": ('def factorial(n):\n'
                   '    if n <= 1:\n'
                   '        return 1\n'
                   '    return n * factorial(n - 1)\n\n\n'
                   'for i in range(1, 11):\n'
                   '    print(i, "! =", factorial(i))'),
        "java": ('public class Main {\n'
                 '    static long factorial(int n) {\n'
                 '        if (n <= 1) {\n'
                 '            return 1;\n'
                 '        }\n'
                 '        return n * factorial(n - 1);\n'
                 '    }\n\n'
                 '    public static void main(String[] args) {\n'
                 '        for (int i = 1; i <= 10; i++) {\n'
                 '            System.out.println(i + "! = " + factorial(i));\n'
                 '        }\n'
                 '    }\n}'),
        "kotlin": ('fun factorial(n: Int): Long {\n'
                   '    return if (n <= 1) 1L else n * factorial(n - 1)\n'
                   '}\n\n'
                   'fun main() {\n'
                   '    for (i in 1..10) {\n'
                   '        println("$i! = ${factorial(i)}")\n'
                   '    }\n}'),
        "cpp": ('#include <iostream>\n\n'
                'long long factorial(int n) {\n'
                '    if (n <= 1) {\n'
                '        return 1;\n'
                '    }\n'
                '    return n * factorial(n - 1);\n'
                '}\n\n'
                'int main() {\n'
                '    for (int i = 1; i <= 10; i++) {\n'
                '        std::cout << i << "! = " << factorial(i) << "\\n";\n'
                '    }\n'
                '    return 0;\n}'),
        "c": ('#include <stdio.h>\n\n'
              'long long factorial(int n) {\n'
              '    if (n <= 1) {\n'
              '        return 1;\n'
              '    }\n'
              '    return n * factorial(n - 1);\n'
              '}\n\n'
              'int main(void) {\n'
              '    for (int i = 1; i <= 10; i++) {\n'
              '        printf("%d! = %lld\\n", i, factorial(i));\n'
              '    }\n'
              '    return 0;\n}'),
        "javascript": ('function factorial(n) {\n'
                       '  if (n <= 1) return 1;\n'
                       '  return n * factorial(n - 1);\n'
                       '}\n\n'
                       'for (let i = 1; i <= 10; i++) {\n'
                       '  console.log(i + "! =", factorial(i));\n'
                       '}'),
        "bash": ('#!/usr/bin/env bash\n'
                 'factorial() {\n'
                 '    if [ "$1" -le 1 ]; then\n'
                 '        echo 1\n'
                 '    else\n'
                 '        local prev\n'
                 '        prev=$(factorial $(( $1 - 1 )))\n'
                 '        echo $(( $1 * prev ))\n'
                 '    fi\n'
                 '}\n'
                 'for n in 1 2 3 4 5; do\n'
                 '    echo "$n! = $(factorial $n)"\n'
                 'done'),
    },
}


_TASK_DETAILS = {
    "anagram": (
        "### Algorithm Step-by-Step Explanation:\n"
        "1. **Frequency Counting via Hash Map:** Instead of sorting characters ($O(n \\log n)$), we count character occurrences in linear time ($O(n)$) using a frequency hash map.\n"
        "2. **Normalization (Case & Whitespace Handling):** We convert characters to lowercase (`c.lower()`) to achieve case-insensitivity, and filter out whitespace characters (`c.isspace()`).\n"
        "3. **Tallying & Verification:** We iterate through the first string and increment character counts, then iterate through the second string and decrement counts. If any character in the second string is missing or exceeds the tally, the strings cannot be anagrams.\n"
        "4. **Final State Check:** If all counts balance out to zero (or the hash map is empty), the two strings are guaranteed anagrams.\n\n"
        "### Big O Complexity Analysis:\n"
        "- **Time Complexity:** $O(n + m)$ where $n$ and $m$ are the lengths of the two strings - visits each character once.\n"
        "- **Space Complexity:** $O(k)$ where $k$ is the number of distinct characters (at most $O(1)$ constant memory for fixed alphabets)."
    ),
    "second_largest": (
        "### Algorithm Step-by-Step Explanation:\n"
        "1. **Initialization:** Initialize two tracking variables `first` and `second` to negative infinity ($-\\infty$).\n"
        "2. **Single-Pass Scan ($O(n)$):** Iterate through each number in the list once:\n"
        "   - If `num > first`: Update `second = first`, then `first = num`.\n"
        "   - Else if `first > num > second`: Update `second = num` (ensures uniqueness so duplicates of max are skipped).\n"
        "3. **Validation & Edge Case Handling:** If `second` remains $-\\infty$, it indicates the list has fewer than 2 elements or all elements are identical. The function safely returns `None`.\n\n"
        "### Big O Complexity Analysis:\n"
        "- **Time Complexity:** $O(n)$ linear time - inspects each element exactly once, completely avoiding sorting ($O(n \\log n)$).\n"
        "- **Space Complexity:** $O(1)$ constant auxiliary memory (only two scalar variables).\n\n"
        "### Test Verification:\n"
        "- `[5, 3, 9, 1, 7]` -> `7`\n"
        "- `[10, 10, 10, 9, 8]` -> `9` (correctly handles duplicate max)\n"
        "- `[42]` or `[7, 7, 7]` -> `None` (gracefully handles $< 2$ unique items)"
    ),
    "reverse_string_no_slice": (
        "### Algorithm Step-by-Step Explanation:\n"
        "1. **Negative Constraint Adherence:** Operates strictly without string slicing (`[::-1]`) or built-in functions (`reversed()`, `reverse()`).\n"
        "2. **Backward Loop Accumulation:** Iterates indices in reverse order from `len(s) - 1` down to `0`, appending characters to a list buffer in $O(1)$ amortized time per character.\n"
        "3. **Alternative In-Place Two-Pointer Method:** Converts the string to a mutable character list, swaps elements at `left` and `right` pointers moving towards the center, and joins back to a string.\n\n"
        "### Big O Complexity Analysis:\n"
        "- **Time Complexity:** $O(n)$ where $n$ is the length of the string.\n"
        "- **Space Complexity:** $O(n)$ auxiliary space for character buffers."
    ),
    "find_duplicates": (
        "### Algorithm Step-by-Step Explanation:\n"
        "1. **Hash Set Tracking:** We iterate through the list while maintaining two hash sets: `seen` to track all elements encountered so far, and `duplicates` to store elements that appear more than once.\n"
        "2. **Constant-Time Membership Test:** For each element, checking `if item in seen` runs in $O(1)$ average time via hash table lookups.\n"
        "3. **Insertion:** If an element is already in `seen`, it is added to `duplicates`. Otherwise, it is added to `seen`.\n"
        "4. **Output Conversion:** After completing the single pass, the `duplicates` set is returned as a list or array.\n\n"
        "### Big O Complexity Analysis:\n"
        "- **Time Complexity:** $O(n)$ where $n$ is the total number of elements in the input list. Every element is visited and hashed exactly once.\n"
        "- **Space Complexity:** $O(n)$ auxiliary space to store elements in `seen` and `duplicates` in the worst case (e.g., all elements unique or all elements duplicates).\n\n"
        "### Algorithmic Comparison:\n"
        "- **Hash Set Approach (Used Here):** $O(n)$ Time | $O(n)$ Space - Optimal runtime.\n"
        "- **In-Place Sorting Approach:** $O(n \\log n)$ Time | $O(1)$ Space - Sort the list first, then compare adjacent elements.\n"
        "- **Brute-Force Nested Loops:** $O(n^2)$ Time | $O(1)$ Space - Compare every pair of elements with two nested loops (slowest)."
    ),
    "is_prime": (
        "### Algorithm Step-by-Step Explanation:\n"
        "1. **Base Case Validation:** Non-positive numbers, 0, and 1 are not prime by definition and return `False`. Numbers 2 and 3 are prime and return `True`.\n"
        "2. **Elimination of Multiples of 2 and 3:** Numbers divisible by 2 or 3 are immediately eliminated in $O(1)$ time (`n % 2 == 0 or n % 3 == 0`).\n"
        "3. **Square Root Factor Bound:** If a composite number $n$ can be factored as $a \\cdot b = n$, at least one factor must satisfy $a \\le \\sqrt{n}$. Hence, we only need to test divisors up to $\\lfloor\\sqrt{n}\\rfloor$.\n"
        "4. **$6k \\pm 1$ Divisor Stepping:** All prime numbers greater than 3 take the form $6k \\pm 1$ (e.g. 5, 7, 11, 13, 17, 19, ...). Starting at $i = 5$, we test divisibility against $i$ and $i+2$, then increment $i$ by 6 in each loop iteration, skipping 66% of candidate divisors.\n\n"
        "### Big O Complexity Analysis:\n"
        "- **Time Complexity:** $O(\\sqrt{n})$ in the worst case (when $n$ is prime or has its prime factors close to $\\sqrt{n}$).\n"
        "- **Space Complexity:** $O(1)$ strictly constant auxiliary space (using only scalar variables `n`, `i`).\n\n"
        "### Example Input & Output:\n"
        "- `is_prime(2)`  -> `True` (smallest prime)\n"
        "- `is_prime(17)` -> `True` (prime)\n"
        "- `is_prime(20)` -> `False` ($20 = 2^2 \\times 5$)\n"
        "- `is_prime(97)` -> `True` (largest 2-digit prime)"
    ),
    "password_manager": (
        "### Security Architecture & Algorithm Explanation:\n"
        "1. **FIPS-197 AES-256 Block Cipher:** Operates on 128-bit blocks using a 256-bit key schedule across 14 iterative rounds consisting of `SubBytes` (non-linear S-box substitution), `ShiftRows` (cyclical row transposition), `MixColumns` (Galois Field matrix multiplication), and `AddRoundKey` (bitwise XOR with round keys).\n"
        "2. **Counter (CTR) Mode:** Converts the block cipher into a stream cipher by generating a keystream from successive counter blocks starting at a cryptographically random 16-byte initialization vector (`iv`). This eliminates block padding vulnerabilities and enables arbitrary data length encryption.\n"
        "3. **PBKDF2-HMAC-SHA256 Key Derivation:** Applies 100,000 iterations with a unique 16-byte CSPRNG salt (`os.urandom(16)`) to derive 64 bytes of key material, split into a 32-byte AES-256 encryption key and a 32-byte HMAC authentication key. This neutralizes rainbow table and dictionary attacks.\n"
        "4. **Authenticated Encryption (Encrypt-then-MAC):** Generates an HMAC-SHA256 authentication tag over `salt || iv || ciphertext`. Verification uses constant-time comparison (`hmac.compare_digest`) before decryption to prevent padding oracle, ciphertext bit-flipping, and timing side-channel attacks.\n"
        "5. **Input Validation & Error Handling:** Validates all parameters (non-empty master password, valid service names), protects against vault tampering with `PermissionError`, and operates with zero external dependencies on any Python 3 environment.\n\n"
        "### Big O Complexity Analysis:\n"
        "- **Key Derivation Time:** $O(K \\cdot L)$ where $K$ is iteration count (100,000) and $L$ is master password length.\n"
        "- **Encryption / Decryption Time:** $O(N)$ linear time in payload length $N$ (14 rounds per 16-byte block).\n"
        "- **Space Complexity:** $O(N)$ auxiliary memory for ciphertext buffers and JSON persistence."
    ),
    "lru_cache": (
        "### Algorithm Step-by-Step Explanation:\n"
        "1. **Dual Data Structure Design:** Combines a Hash Map (`dict`) for $O(1)$ key-to-node lookups and a Doubly Linked List for $O(1)$ node insertions, deletions, and relocations.\n"
        "2. **Sentinel Nodes:** Employs dummy `head` and `tail` sentinel nodes to eliminate boundary edge-case checks during node insertion and removal.\n"
        "3. **Get Operation:** If key is found in cache, detaches the node from its current position and re-inserts it directly after `head` (most recently used position) in $O(1)$ time, returning its value.\n"
        "4. **Put Operation:** If key already exists, updates the node value and moves it to the front. If new, evicts the least recently used node right before `tail` when capacity is reached, then inserts the new node at the front in $O(1)$ time.\n\n"
        "### Big O Complexity Analysis:\n"
        "- **Time Complexity:** $O(1)$ strictly constant time for both `get` and `put` operations.\n"
        "- **Space Complexity:** $O(C)$ where $C$ is the maximum capacity of the cache."
    ),
    "dijkstra": (
        "### Algorithm Step-by-Step Explanation:\n"
        "1. **Distance Initialization:** Initializes distance to `start` as 0 and all other nodes to $\\infty$, setting up a predecessor dictionary to trace paths.\n"
        "2. **Priority Queue (Min-Heap):** Pushes `(0, start)` to a binary min-heap (`heapq`).\n"
        "3. **Greedy Relaxation:** Iteratively extracts the unvisited node with smallest cumulative distance. For each neighbor, relaxes the edge if `curr_dist + weight < dist[neighbor]`, updating distance and predecessor, then pushing to heap.\n"
        "4. **Path Reconstruction:** Follows predecessors backwards from target to start, then reverses the list.\n\n"
        "### Big O Complexity Analysis:\n"
        "- **Time Complexity:** $O((V + E) \\log V)$ using a binary min-heap, where $V$ is number of vertices and $E$ is number of edges.\n"
        "- **Space Complexity:** $O(V + E)$ auxiliary memory for distances, predecessors, and the priority queue."
    ),
    "sieve": (
        "### Algorithm Step-by-Step Explanation:\n"
        "1. **Array Initialization:** Create a boolean array `is_prime` of size $n + 1$, initially setting all entries to `True`, except index 0 and 1 which are explicitly marked as `False` (neither 0 nor 1 is prime).\n"
        "2. **Iterative Sifting:** Iterate an integer variable $p$ starting from 2 up to $\\lfloor\\sqrt{n}\\rfloor$. If `is_prime[p]` remains `True`, $p$ is prime.\n"
        "3. **Multiples Elimination:** For each prime $p$, mark all of its multiples starting from $p^2$ (i.e. $p^2, p^2 + p, p^2 + 2p, \\dots \\le n$) as `False` (composite). Multiples smaller than $p^2$ have already been marked by smaller prime factors.\n"
        "4. **Result Collection:** Iterate through the remaining array and collect all indices $i$ where `is_prime[i]` is `True`.\n\n"
        "### Big O Complexity Analysis:\n"
        "- **Time Complexity:** $O(n \\log(\\log n))$ - strictly faster than trial division $O(n \\sqrt{n})$ because inner loop operations sum to the harmonic series of primes: $\\sum_{p \\le n} \\frac{n}{p} = O(n \\log \\log n)$.\n"
        "- **Space Complexity:** $O(n)$ - requires an $(n+1)$-element boolean array in memory.\n\n"
        "### Input Validation & Edge Cases:\n"
        "- Raises `TypeError` if input $n$ is not an integer.\n"
        "- Safely handles negative integers, zero, and one by returning an empty list `[]` (since no primes exist $< 2$).\n\n"
        "### Example Output:\n"
        "- Input: `n = 30` -> Output: `[2, 3, 5, 7, 11, 13, 17, 19, 23, 29]`\n"
        "- Input: `n = 10` -> Output: `[2, 3, 5, 7]`\n"
        "- Input: `n = 1`  -> Output: `[]`"
    ),
    "kth_largest": (
        "### Algorithm Step-by-Step Explanation:\n"
        "1. **Input Validation:** Intercepts invalid parameters early, throwing an `IllegalArgumentException` if the array is null/empty or if $k$ is out of bounds ($k \\le 0$ or $k > \\text{array.length}$).\n"
        "2. **Min-Heap Maintenance:** Uses a `PriorityQueue` configured as a Min-Heap with initial capacity $k$ to maintain the $k$ largest elements encountered during iteration.\n"
        "3. **Stream Processing:** Iterates through each element in the unsorted array and inserts it into the heap via `minHeap.offer(num)`.\n"
        "4. **Bounding Heap Size:** Whenever the heap size exceeds $k$, evicts the root (the minimum of the current $k+1$ elements) using `minHeap.poll()`.\n"
        "5. **K-th Largest Identification:** After scanning all $N$ elements, the top of the min-heap (`minHeap.peek()`) contains the smallest of the top $k$ elements, which is the $k$-th largest element in the array.\n\n"
        "### Big O Complexity Analysis:\n"
        "- **Time Complexity:** $O(N \\log k)$ - inserting and maintaining $N$ elements in a heap of fixed size $k$ costs $O(\\log k)$ per element. This avoids sorting the full array ($O(N \\log N)$), offering massive speedups when $k \\ll N$.\n"
        "- **Space Complexity:** $O(k)$ - auxiliary storage for the min-heap holding at most $k$ elements.\n\n"
        "### Duplicate & Edge Case Handling:\n"
        "- **Duplicates:** Handled correctly without special filtering because the min-heap retains each instance appropriately according to standard order statistics.\n"
        "- **Bounds Checking:** Rejects empty arrays and invalid $k$ values gracefully with meaningful exceptions.\n\n"
        "### Example Output:\n"
        "- Array: `[3, 2, 1, 5, 6, 4]`, `k = 2` -> Output: `5`\n"
        "- Array: `[3, 2, 3, 1, 2, 4, 5, 5, 6]`, `k = 4` -> Output: `4`\n"
        "- Array: `[7, 10, 4, 3, 20, 15]`, `k = 1` -> Output: `20`"
    ),
}


def _task_program(question, lang):
    ql = question.lower()
    kind = None
    if re.search(r"second[- ]?largest|2nd[- ]?largest", ql):
        kind = "second_largest"
    elif re.search(r"\b(?:check|is|test|whether|determine)\b.*\bprime\b|\bprime\s*(?:check|test|number\s+check)\b|\bis_prime\b", ql):
        kind = "is_prime"
    elif re.search(r"duplicate", ql):
        kind = "find_duplicates"
    elif "sieve" in ql:
        kind = "sieve"
    elif re.search(r"password\s*manager|aes[- ]?256|aes\s*encryption", ql):
        kind = "password_manager"
    elif re.search(r"lru\s*cache", ql):
        kind = "lru_cache"
    elif re.search(r"dijkstra|shortest\s+path", ql):
        kind = "dijkstra"
    elif re.search(r"k[- ]?th\s+largest|priorityqueue|min[- ]?heap|k\s+largest", ql):
        kind = "kth_largest"
    elif "binary search" in ql:
        kind = "binary_search"
    elif re.search(r"dockerfile", ql):
        kind = "dockerfile"
    elif re.search(r"two\s*sum", ql):
        kind = "two_sum"
    elif re.search(r"linked\s*list", ql) and re.search(r"revers", ql):
        kind = "reverse_linked_list"
    elif re.search(r"\brevers\w*", ql) and not re.search(r"linked\s*list", ql):
        if re.search(r"without\s*(?:using\s*)?(?:slic|built|reverse)|no\s*slic", ql) or _has_negative_constraint(ql, "slicing") or _has_negative_constraint(ql, "reverse"):
            kind = "reverse_string_no_slice"
        else:
            kind = "reverse_string"
    elif "password" in ql:
        kind = "password"
    elif "fizzbuzz" in ql or "fizz buzz" in ql:
        kind = "fizzbuzz"
    elif "calculator" in ql:
        kind = "calculator"
    elif "dice" in ql or "random number" in ql:
        kind = "dice"
    elif re.search(r'\brecursion|recursive\b', ql):
        kind = "recursion"
    elif re.search(r'\b(?:create|make)\s+(?:a\s+)?'
                   r'(?:directory|folder)|mkdir', ql):
        kind = "make_dir"
    elif re.search(r"\b(?:even|odd)\b", ql) and re.search(
            r"\b(number|check|function|program)", ql):
        kind = "even_check"
    elif "factorial" in ql:
        kind = "factorial"
    elif re.search(r"\bprimes?\b", ql) and "minister" not in ql:
        kind = "primes"
    elif re.search(r"\bswap\w*", ql):
        kind = "swap"
    elif re.search(r"count\w*\s+(?:the\s+)?words", ql):
        kind = "count_words"
    elif re.search(r"\bsort\w*", ql) and not _has_negative_constraint(ql, "sort"):
        kind = "sort_numbers"
    elif re.search(r"add\s+(?:two|2)\s+numbers?|sum\s+of\s+(?:two|2)\s+numbers?", ql):
        kind = "add_two"
    elif (re.search(r"\b(sum|average)\b|adds?\s+up", ql)
          and re.search(r"\b(numbers|list|array)\b", ql)):
        kind = "sum_list"
    elif "multiplication table" in ql or "times table" in ql:
        kind = "multiplication_table"
    elif "palindrome" in ql:
        kind = "palindrome"
    elif re.search(r"\banagrams?\b", ql):
        kind = "anagram"
    elif "fibonacci" in ql:
        kind = "fibonacci"
    elif re.search(r"leap\s+year", ql):
        kind = "leap_year"
    elif re.search(r"\b(largest|biggest|greatest|smallest|minimum|maximum)\b", ql) \
            and re.search(r"\b(numbers|list|array|of)\b", ql):
        kind = "largest_of"
    elif re.search(r"\bvowels?\b", ql):
        kind = "vowels"
    elif re.search(r"list\s+(?:all\s+)?files", ql):
        kind = "list_files"
    elif re.search(r"\bhello\s*,?\s*world\b", ql):
        return _hello_world(lang)
    if not kind:
        return None
    code = _TASKS.get(kind, {}).get(lang)
    if code is None and lang == "python":
        code = _TASKS.get(kind, {}).get("python")
    if not code:
        return None
    details = _TASK_DETAILS.get(kind)
    return code, "implements %s" % kind, details


def _full_program(lang):
    code = _FULL.get(lang)
    if not code:
        return None
    return code, "is a complete %s starter program (function, loop, and main)" % lang


_RUN = {
    "bash": ("demo.sh", "bash demo.sh"),
    "python": ("demo.py", "python3 demo.py"),
    "javascript": ("app.js", "node app.js"),
    "typescript": ("hello.ts", "npx ts-node hello.ts"),
    "java": ("Main.java", "javac Main.java && java Main"),
    "kotlin": ("main.kt", "kotlinc main.kt -include-runtime -d main.jar && java -jar main.jar"),
    "rust": ("main.rs", "rustc main.rs -o main && ./main"),
    "cpp": ("main.cpp", "g++ main.cpp -o main && ./main"),
    "c": ("main.c", "cc main.c -o main && ./main"),
    "dart": ("hello.dart", "dart run hello.dart"),
    "go": ("main.go", "go run main.go"),
    "ruby": ("hello.rb", "ruby hello.rb"),
    "php": ("hello.php", "php hello.php"),
    "swift": ("hello.swift", "swift hello.swift"),
    "csharp": ("Program.cs", "csc Program.cs && mono Program.exe (or: dotnet run)"),
    "lua": ("hello.lua", "lua hello.lua"),
}


def run_hint(lang):
    return _RUN.get(lang, ("demo.txt", "see your language's docs"))


def _hello_world(lang):
    code = _HELLO.get(lang)
    if not code:
        return None
    return code, "is a minimal %s starter script" % lang


def _strip_comments_python(code):
    """Remove # comments and docstrings from python source, keeping code intact."""
    import io
    import tokenize as _tk
    try:
        lines = code.split("\n")
        cut = {}
        for tok in _tk.generate_tokens(io.StringIO(code).readline):
            if tok.type == _tk.COMMENT:
                ln = tok.start[0]
                cur = cut.get(ln, 10 ** 9)
                cut[ln] = min(cur, tok.start[1])
        out = []
        for i, ln in enumerate(lines, 1):
            if i in cut:
                ln = ln[:cut[i]].rstrip()
            out.append(ln)
        code = "\n".join(out)
        # docstrings: bare string expressions right under module/def/class
        import ast as _ast
        tree = _ast.parse(code)
        spans = []

        def _collect(node):
            for child in _ast.walk(node):
                if isinstance(child, (_ast.FunctionDef, _ast.AsyncFunctionDef,
                                      _ast.ClassDef)):
                    body = child.body
                    if (body and isinstance(body[0], _ast.Expr)
                            and isinstance(body[0].value, _ast.Constant)
                            and isinstance(body[0].value.value, str)):
                        spans.append((body[0].lineno,
                                      body[0].end_lineno or body[0].lineno))

        _collect(tree)
        if (tree.body and isinstance(tree.body[0], _ast.Expr)
                and isinstance(tree.body[0].value, _ast.Constant)
                and isinstance(tree.body[0].value.value, str)):
            spans.append((tree.body[0].lineno,
                          tree.body[0].end_lineno or tree.body[0].lineno))
        if spans:
            drop = set()
            for a, b in spans:
                drop.update(range(a, b + 1))
            keep = [ln for i, ln in enumerate(code.split("\n"), 1)
                    if i not in drop]
            stripped = "\n".join(keep)
            try:
                _ast.parse(stripped)   # never ship code we just broke
                code = stripped
            except Exception:
                pass
        code = re.sub(r"\n{3,}", "\n\n", code).strip("\n")
        return code
    except Exception:
        return code


def strip_comments(code, lang):
    """Answer code should be clean: drop comments/docstrings from generated
    source (python tokenizer for python, safe line passes for other langs)."""
    try:
        if not code:
            return code
        if lang in ("python",):
            return _strip_comments_python(code)
        if lang in ("bash", "sh", "shell", "ruby", "lua", "php", "perl"):
            out = []
            for ln in code.split("\n"):
                st = ln.strip()
                if st.startswith("#") and not st.startswith("#!"):
                    continue
                if " #" in ln:
                    # inline comment outside quotes (best effort)
                    head, _, tail = ln.partition(" #")
                    if head.count('"') % 2 == 0 and head.count("'") % 2 == 0:
                        ln = head.rstrip()
                out.append(ln)
            return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip("\n")
        # C-style families: // line comments and /* block comments */
        code = re.sub(r"/\*.*?\*/", "", code, flags=re.S)
        out = []
        for ln in code.split("\n"):
            m = re.search(r"(?<!:)//[^\n]*$", ln)
            if m and ln[:m.start()].count('"') % 2 == 0:
                ln = ln[:m.start()].rstrip()
            out.append(ln)
        return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip("\n")
    except Exception:
        return code


def compose(question):
    """Return {lang, code, verified, check, explanation, details_md} or None."""
    lang = detect_lang(question)
    name = _target_name(question)
    if lang == "python":
        built = _python_script(question, name)
    elif lang == "bash":
        built = _bash_script(question, name)
    else:
        built = None
    if not built:
        built = _task_program(question, lang)
    if not built and re.search(r'\b(starter|boilerplate|template|hello\s*,?\s*world|skeleton)\b', question.lower()):
        if _wants_big(question):
            built = _full_program(lang)
        else:
            built = _hello_world(lang)
    if not built:
        return None
    code = built[0]
    note = built[1]
    details = built[2] if len(built) > 2 else None
    code = strip_comments(code, lang)     # clean answer: no comments/docstrings
    ok, checker = _syntax_check(lang, code)
    return {"lang": lang, "code": code, "verified": ok, "check": checker,
            "explanation": note, "details_md": details}