"""TenSeiAi Python client (stdlib only). Run the model first: ./TenSeiAi.pyz

    python3 tensei_client.py "what is gravity"     # one question
"""
import json
import time
import urllib.request


class TenSei:
    def __init__(self, base="http://127.0.0.1:8765"):
        self.base = base.rstrip("/")

    def _post(self, path, obj, timeout=60):
        req = urllib.request.Request(
            self.base + path, data=json.dumps(obj).encode(),
            headers={"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(req, timeout=timeout))

    def _get(self, path, timeout=30):
        return json.load(urllib.request.urlopen(self.base + path, timeout=timeout))

    def ask(self, q, timeout=300):
        job = self._post("/api/ask", {"q": q})
        t0 = time.time()
        while time.time() - t0 < timeout:
            j = self._get("/api/job?id=" + job["id"])
            if j.get("status") in ("done", "error"):
                return j
            time.sleep(0.5)
        raise TimeoutError("TenSeiAi did not answer in time")

    def chat(self, messages):
        return self._post("/v1/chat/completions",
                          {"model": "tensei-1", "messages": messages})

    def stats(self):
        return self._get("/api/stats")


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "hello"
    res = TenSei().ask(q)
    print(res.get("result", {}).get("answer", res))
