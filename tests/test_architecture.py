import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1] / "closer"
FORBIDDEN_ALL = {"anthropic", "openai", "google", "requests", "urllib", "http", "socket", "subprocess", "httpx"}


def imports(path):
    tree = ast.parse(path.read_text())
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out += [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom) and n.module:
            out.append(n.module)
    return out


def files(layer):
    return [p for p in (ROOT / layer).rglob("*.py")]


def test_domain_and_application_have_no_llm_or_network_imports():
    for layer in ("domain", "application"):
        for p in files(layer):
            for m in imports(p):
                assert m.split(".")[0] not in FORBIDDEN_ALL, (p, m)


def test_dependency_direction():
    rules = {"domain": ["closer.application", "closer.adapters", "closer.infrastructure"],
             "application": ["closer.adapters", "closer.infrastructure"],
             "adapters": ["closer.infrastructure"]}
    for layer, banned in rules.items():
        for p in files(layer):
            for m in imports(p):
                assert not any(m.startswith(b) for b in banned), (p, m)
