import json
from pathlib import Path
import sys

from .engine import analyze, benchmark, observe

ROOT = Path(__file__).resolve().parent
MESSAGES = {
    "fr": {"help": "Utilisation : python -m fab_discovery demo|analyze dossier.json|observe dossier.json essai résultat preuve|benchmark|serve [port] [--lang fr|en|es]", "error": "Entrée non valide", "ready": "Laboratoire local"},
    "en": {"help": "Usage: python -m fab_discovery demo|analyze case.json|observe case.json design outcome evidence|benchmark|serve [port] [--lang fr|en|es]", "error": "Invalid input", "ready": "Local laboratory"},
    "es": {"help": "Uso: python -m fab_discovery demo|analyze caso.json|observe caso.json ensayo resultado prueba|benchmark|serve [puerto] [--lang fr|en|es]", "error": "Entrada no válida", "ready": "Laboratorio local"},
}


def example():
    return json.loads((ROOT / "examples/process-window.json").read_text())


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    lang = "en"
    if "--lang" in args:
        i = args.index("--lang")
        if i + 1 < len(args) and args[i + 1] in MESSAGES:
            lang = args[i + 1]
        del args[i:i + 2]
    message = MESSAGES[lang]
    try:
        if not args or args[0] in ("--help", "help"):
            print(message["help"])
            return 0
        command = args.pop(0)
        if command == "demo":
            result = analyze(example())
        elif command == "analyze" and len(args) == 1:
            result = analyze(json.loads(Path(args[0]).read_text()))
        elif command == "observe" and len(args) == 4:
            result = observe(json.loads(Path(args[0]).read_text()), *args[1:])
        elif command == "benchmark":
            result = benchmark(example())
        elif command == "serve":
            from .server import serve
            port = int(args[0]) if args else 8765
            print(f'{message["ready"]}: http://127.0.0.1:{port}/?lang={lang}', flush=True)
            serve(port)
            return 0
        else:
            print(message["help"], file=sys.stderr)
            return 2
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (ValueError, TypeError, KeyError, OSError) as error:
        code = str(error) if isinstance(error, ValueError) and str(error).startswith("invalid_") else "invalid_input"
        print(json.dumps({"error": code, "message": message["error"]}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
