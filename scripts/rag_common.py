from __future__ import annotations

import ast
import hashlib
import json
import keyword
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from call_chain_common import PROJECT_ROOT, load_json, normalize_slashes


RAG_INDEX_SCHEMA_VERSION = "rag-index-v1"
RAG_RETRIEVAL_SCHEMA_VERSION = "rag-retrieval-v1"
RAG_EVAL_SCHEMA_VERSION = "rag-retrieval-eval-v1"

DEFAULT_CODE_SUFFIXES = {".py", ".pyi"}
DEFAULT_IGNORE_DIRS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
    "site-packages",
    "venv",
}

STOP_TERMS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "class",
    "def",
    "for",
    "from",
    "if",
    "in",
    "is",
    "it",
    "method",
    "of",
    "on",
    "or",
    "return",
    "self",
    "the",
    "to",
    "with",
}
PYTHON_KEYWORDS = set(keyword.kwlist)
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
DOTTED_SYMBOL_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\b")
CAMEL_SPLIT_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def project_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSONL record: {exc}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"{path}:{line_no}: JSONL record must be an object")
            records.append(payload)
    return records


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_test_path(rel_path: str) -> bool:
    parts = rel_path.lower().split("/")
    name = parts[-1]
    return "tests" in parts or "test" in parts or name.startswith("test_") or name.endswith("_test.py")


def iter_indexable_files(
    repo_path: Path,
    *,
    suffixes: set[str],
    include_tests: bool,
    ignore_dirs: set[str] | None = None,
    max_file_bytes: int | None = None,
) -> tuple[list[Path], list[dict[str, Any]]]:
    ignored = ignore_dirs or DEFAULT_IGNORE_DIRS
    selected: list[Path] = []
    skipped: list[dict[str, Any]] = []
    for path in sorted(repo_path.rglob("*")):
        if not path.is_file():
            continue
        try:
            rel_path = path.resolve().relative_to(repo_path.resolve()).as_posix()
        except ValueError:
            continue
        parts = set(rel_path.split("/"))
        if parts & ignored:
            skipped.append({"file": rel_path, "reason": "ignored_dir"})
            continue
        if path.suffix.lower() not in suffixes:
            continue
        if not include_tests and is_test_path(rel_path):
            skipped.append({"file": rel_path, "reason": "test_path"})
            continue
        if max_file_bytes is not None:
            try:
                size = path.stat().st_size
            except OSError:
                skipped.append({"file": rel_path, "reason": "stat_error"})
                continue
            if size > max_file_bytes:
                skipped.append({"file": rel_path, "reason": "max_file_bytes", "bytes": size})
                continue
        selected.append(path)
    return selected, skipped


def module_name_from_path(rel_path: str) -> str:
    normalized = normalize_slashes(rel_path)
    without_suffix = re.sub(r"\.(pyi?|py)$", "", normalized)
    parts = [part for part in without_suffix.split("/") if part]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def split_identifier(value: str) -> list[str]:
    pieces: list[str] = []
    for dotted_part in re.split(r"[./\\:\-\s]+", value):
        if not dotted_part:
            continue
        for snake_part in dotted_part.split("_"):
            if not snake_part:
                continue
            pieces.extend(part for part in CAMEL_SPLIT_RE.split(snake_part) if part)
    return pieces


def tokenize(text: str, *, max_terms: int | None = None) -> list[str]:
    counts: Counter[str] = Counter()
    for token in TOKEN_RE.findall(text):
        for piece in split_identifier(token):
            term = piece.lower()
            if len(term) < 2:
                continue
            if term in STOP_TERMS or term in PYTHON_KEYWORDS:
                continue
            counts[term] += 1
    terms = [term for term, _ in counts.most_common(max_terms)]
    return terms


def query_terms(text: str) -> list[str]:
    terms = tokenize(text)
    seen: set[str] = set()
    ordered: list[str] = []
    for term in terms:
        if term not in seen:
            seen.add(term)
            ordered.append(term)
    return ordered


def extract_dotted_symbols(text: str) -> list[str]:
    seen: set[str] = set()
    symbols: list[str] = []
    for match in DOTTED_SYMBOL_RE.finditer(text):
        symbol = match.group(0)
        if symbol not in seen:
            seen.add(symbol)
            symbols.append(symbol)
    return symbols


def extract_python_definitions(text: str, rel_path: str) -> list[dict[str, Any]]:
    module = module_name_from_path(rel_path)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    definitions: list[dict[str, Any]] = []

    def visit_body(body: list[ast.stmt], scope: list[str]) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                symbol = ".".join(part for part in [module, *scope, node.name] if part)
                definitions.append(_definition_record(node, symbol, "class"))
                visit_body(node.body, [*scope, node.name])
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbol = ".".join(part for part in [module, *scope, node.name] if part)
                kind = "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function"
                definitions.append(_definition_record(node, symbol, kind))
                visit_body(node.body, [*scope, node.name])

    visit_body(tree.body, [])
    return definitions


def _definition_record(node: ast.AST, symbol: str, kind: str) -> dict[str, Any]:
    start = int(getattr(node, "lineno", 1) or 1)
    end = int(getattr(node, "end_lineno", start) or start)
    return {"symbol": symbol, "kind": kind, "start_line": start, "end_line": end}


def build_chunks_for_file(
    *,
    repo_key: str,
    commit: str,
    repo_path: Path,
    file_path: Path,
    chunk_lines: int,
    overlap_lines: int,
    max_terms: int,
) -> list[dict[str, Any]]:
    rel_path = file_path.resolve().relative_to(repo_path.resolve()).as_posix()
    raw = file_path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    if not lines:
        return []

    definitions = extract_python_definitions(text, rel_path) if file_path.suffix.lower() in {".py", ".pyi"} else []
    file_hash = sha256_bytes(raw)
    chunks: list[dict[str, Any]] = []
    start_idx = 0
    overlap = max(0, min(overlap_lines, chunk_lines - 1))
    while start_idx < len(lines):
        end_idx = min(start_idx + chunk_lines, len(lines))
        start_line = start_idx + 1
        end_line = end_idx
        chunk_text = "\n".join(lines[start_idx:end_idx])
        overlapping_defs = [
            item for item in definitions if item["start_line"] <= end_line and item["end_line"] >= start_line
        ]
        local_symbols = extract_dotted_symbols(chunk_text)
        defined_symbols = [item["symbol"] for item in overlapping_defs]
        symbol_set = list(dict.fromkeys([*defined_symbols, *local_symbols]))
        lexical_terms = tokenize(chunk_text, max_terms=max_terms)
        chunk_hash = sha256_text(f"{repo_key}\n{commit}\n{rel_path}\n{start_line}\n{end_line}\n{chunk_text}")
        chunk_id = f"{repo_key}:{rel_path}:{start_line}-{end_line}:{chunk_hash[:12]}"
        chunks.append(
            {
                "chunk_id": chunk_id,
                "repo_key": repo_key,
                "commit": commit,
                "file": rel_path,
                "start_line": start_line,
                "end_line": end_line,
                "language": "python" if file_path.suffix.lower() in {".py", ".pyi"} else "text",
                "line_count": end_line - start_line + 1,
                "char_count": len(chunk_text),
                "file_sha256": file_hash,
                "chunk_sha256": chunk_hash,
                "text": chunk_text,
                "symbols": symbol_set,
                "defined_symbols": defined_symbols,
                "symbol_spans": overlapping_defs,
                "lexical_terms": lexical_terms,
            }
        )
        if end_idx >= len(lines):
            break
        start_idx = end_idx - overlap
    return chunks


@dataclass
class LoadedIndex:
    index_dir: Path
    manifest: dict[str, Any]
    chunks: list[dict[str, Any]]


def load_index(index_dir: str | Path) -> LoadedIndex:
    root = project_path(index_dir).resolve()
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"index manifest not found: {manifest_path}")
    manifest = load_json(manifest_path)
    chunk_file = str(manifest.get("chunk_file") or "chunks.jsonl")
    chunks = read_jsonl(root / chunk_file)
    return LoadedIndex(index_dir=root, manifest=manifest, chunks=chunks)


def latest_index_dir(base_dir: str | Path | None = None) -> Path:
    root = project_path(base_dir or PROJECT_ROOT / "runs" / "indexes")
    candidates = [path for path in root.glob("*") if path.is_dir() and (path / "manifest.json").exists()]
    if not candidates:
        raise FileNotFoundError(f"no index manifest found under {root}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


class BM25Index:
    def __init__(self, chunks: list[dict[str, Any]], *, k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.doc_terms: list[list[str]] = []
        self.term_counts: list[Counter[str]] = []
        self.doc_lengths: list[int] = []
        self.document_frequency: Counter[str] = Counter()
        for chunk in chunks:
            terms = list(chunk.get("lexical_terms") or tokenize(str(chunk.get("text", ""))))
            self.doc_terms.append(terms)
            counts = Counter(terms)
            self.term_counts.append(counts)
            doc_length = sum(counts.values())
            self.doc_lengths.append(doc_length)
            self.document_frequency.update(counts.keys())
        self.doc_count = len(chunks)
        self.avgdl = sum(self.doc_lengths) / self.doc_count if self.doc_count else 0.0

    def score(self, terms: list[str], doc_index: int) -> float:
        if not terms or not self.doc_count:
            return 0.0
        counts = self.term_counts[doc_index]
        doc_length = self.doc_lengths[doc_index] or 1
        score = 0.0
        for term in terms:
            tf = counts.get(term, 0)
            if tf <= 0:
                continue
            df = self.document_frequency.get(term, 0)
            idf = math.log(1 + (self.doc_count - df + 0.5) / (df + 0.5))
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_length / (self.avgdl or 1.0))
            score += idf * ((tf * (self.k1 + 1)) / denominator)
        return score

    def stats(self) -> dict[str, Any]:
        return {
            "doc_count": self.doc_count,
            "avg_doc_length": round(self.avgdl, 6),
            "unique_terms": len(self.document_frequency),
        }


def keyword_score(chunk: dict[str, Any], terms: list[str], symbols: list[str]) -> float:
    text = str(chunk.get("text", ""))
    text_lower = text.lower()
    chunk_terms = set(chunk.get("lexical_terms") or tokenize(text))
    chunk_symbols = set(str(symbol) for symbol in chunk.get("symbols") or [])
    score = 0.0
    for term in terms:
        if term in chunk_terms:
            score += 1.0
        if term and term in text_lower:
            score += 0.25
    for symbol in symbols:
        if not symbol:
            continue
        if symbol in chunk_symbols:
            score += 6.0
        elif symbol in text:
            score += 4.0
        else:
            tail = symbol.split(".")[-1]
            if tail and re.search(rf"\b{re.escape(tail)}\b", text):
                score += 1.5
    return score


def build_case_query(case: dict[str, Any]) -> dict[str, Any]:
    target = str(case.get("target") or "")
    target_parts = split_identifier(target)
    query_text = " ".join(
        str(value)
        for value in [
            case.get("task_type"),
            case.get("direction"),
            case.get("target_type"),
            target,
            " ".join(target_parts),
            " ".join(str(item) for item in case.get("features", []) or []),
        ]
        if value
    )
    symbols = [target]
    dotted_prefixes = target.split(".")
    if len(dotted_prefixes) > 1:
        symbols.append(".".join(dotted_prefixes[:-1]))
    return {"text": query_text, "terms": query_terms(query_text), "symbols": list(dict.fromkeys(symbols))}


EMBEDDING_PROVIDER_REGISTRY = {
    "qwen3": {
        "name": "Qwen/Qwen3-Embedding-0.6B",
        "dimension": 1024,
        "notes": "Future local provider; use an instruction tuned for call-chain code retrieval.",
    },
    "jina_code": {
        "name": "jinaai/jina-embeddings-v2-base-code",
        "dimension": None,
        "notes": "Future lightweight code embedding baseline provider.",
    },
    "bge_m3": {
        "name": "BAAI/bge-m3",
        "dimension": None,
        "notes": "Future dense/sparse/multi-vector reference provider.",
    },
}


class EmbeddingProvider:
    provider_key = "base"

    def available(self) -> bool:
        return False

    def metadata(self) -> dict[str, Any]:
        return {"provider_key": self.provider_key, "available": self.available()}

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError("embedding provider is not implemented yet")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("embedding provider is not implemented yet")


class PlaceholderEmbeddingProvider(EmbeddingProvider):
    def __init__(self, provider_key: str):
        if provider_key not in EMBEDDING_PROVIDER_REGISTRY:
            known = ", ".join(sorted(EMBEDDING_PROVIDER_REGISTRY))
            raise KeyError(f"unknown embedding provider {provider_key!r}; known providers: {known}")
        self.provider_key = provider_key
        self.config = EMBEDDING_PROVIDER_REGISTRY[provider_key]

    def metadata(self) -> dict[str, Any]:
        return {
            "provider_key": self.provider_key,
            "model_name": self.config["name"],
            "dimension": self.config.get("dimension"),
            "available": False,
            "status": "placeholder",
            "notes": self.config.get("notes"),
        }


def resolve_embedding_provider(provider_key: str) -> EmbeddingProvider:
    return PlaceholderEmbeddingProvider(provider_key)


def dense_variant_provider(variant: str) -> str | None:
    if variant.startswith("qwen3_dense"):
        return "qwen3"
    if variant.startswith("jina_code"):
        return "jina_code"
    if variant.startswith("bge_m3"):
        return "bge_m3"
    return None


def result_public_view(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "rank": result["rank"],
        "chunk_id": result["chunk_id"],
        "repo_key": result["repo_key"],
        "file": result["file"],
        "start_line": result["start_line"],
        "end_line": result["end_line"],
        "score": result["score"],
        "bm25_score": result.get("bm25_score"),
        "keyword_score": result.get("keyword_score"),
        "embedding_score": result.get("embedding_score"),
        "symbols": result.get("symbols", [])[:20],
        "lexical_terms": result.get("lexical_terms", [])[:30],
        "text_preview": result.get("text_preview", ""),
    }
