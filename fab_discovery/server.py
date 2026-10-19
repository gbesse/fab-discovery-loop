import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .__main__ import ROOT, example
from .engine import analyze, observe, simulated_outcome


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, code, data, kind="application/json"):
        content = data if isinstance(data, bytes) else json.dumps(data, allow_nan=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/example":
            case = example()
            return self.reply(200, {"case": case, "report": analyze(case)})
        if path in ("/", "/app.js", "/style.css"):
            file = "index.html" if path == "/" else path[1:]
            kind = {"index.html": "text/html", "app.js": "text/javascript", "style.css": "text/css"}[file]
            return self.reply(200, (ROOT / "web" / file).read_bytes(), kind)
        return self.reply(404, {"error": "not_found"})

    def do_POST(self):
        origin = self.headers.get("Origin")
        if origin and origin != f"http://127.0.0.1:{self.server.server_port}":
            return self.reply(403, {"error": "origin_denied"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 500_000:
                raise ValueError("invalid_size")
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise ValueError("invalid_input")
            case = body["case"]
            if self.path == "/api/analyze":
                report = analyze(case, body.get("strategy", "information"))
            elif self.path == "/api/observe":
                case = observe(case, body["design"], body["outcome"], body.get("evidence_id"))
                report = analyze(case)
            elif self.path == "/api/simulate":
                report = analyze(case)
                design = report["recommendation"]
                if design is None:
                    raise ValueError("invalid_no_recommendation")
                seed = body.get("seed", 7)
                if type(seed) is not int:
                    raise ValueError("invalid_seed")
                attempt = sum(o["design"] == design for o in case.get("observations", []))
                outcome = simulated_outcome(case, design, body["true_hypothesis"], seed, attempt)
                case = observe(case, design, outcome, f"simulation:{seed}:{design}:{attempt}")
                report = analyze(case)
            else:
                return self.reply(404, {"error": "not_found"})
            self.reply(200, {"case": case, "report": report})
        except (ValueError, KeyError, TypeError) as error:
            self.reply(400, {"error": str(error) if str(error).startswith("invalid_") else "invalid_input",
                             "messages": ["Entrée non valide", "Invalid input", "Entrada no válida"]})


def serve(port=8765):
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
