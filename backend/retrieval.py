"""
Knowledge Retrieval node.

In production this node would call Azure AI Search (vector + semantic
ranking) over an index populated from Azure Blob-ingested documents. For
the local build, it embeds documents with Azure OpenAI when configured,
falling back to a small built-in TF-IDF implementation (numpy only, no
sklearn dependency) so the pipeline runs without any cloud dependency.

Documents are no longer a fixed, load-once list: `documents.py` is the
document store, and new (e.g. user-uploaded) documents can be added at
runtime. This module rebuilds its index automatically whenever the store
changes (see `invalidate_cache`, called by documents.py).
"""
import re
import numpy as np
import config
import documents as doc_store

_client = None
if config.AZURE_CONFIGURED:
    from openai import AzureOpenAI
    _client = AzureOpenAI(
        api_key=config.AZURE_OPENAI_API_KEY,
        api_version=config.AZURE_OPENAI_API_VERSION,
        azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
    )

# ---- Azure embeddings cache (invalidated whenever documents change) ----
_doc_embeddings = None
_embedded_doc_ids = None

# ---- Local TF-IDF index (rebuilt lazily whenever documents change) ----
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "to", "of", "in", "on", "for", "and", "or", "with", "at", "by", "from",
    "about", "as", "into", "through", "our", "your", "their", "its", "it",
    "do", "does", "did", "what", "which", "who", "whom", "this", "that",
    "these", "those", "i", "we", "you", "they", "he", "she", "can", "could",
    "should", "would", "will", "shall", "may", "might", "must", "have",
    "has", "had", "not", "no", "so", "if", "then", "than", "there", "here",
}
_token_re = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")

# Small suffix-stripping stemmer (not a full Porter stemmer, just enough to
# collapse common word variants onto the same root) so e.g. a query for
# "apply" still matches a document that only says "applicants" or
# "applying", and "requirements" matches "required". Longest suffixes are
# checked first so e.g. "-ational" is stripped before the shorter "-tion".
_SUFFIXES = [
    "ational", "tional", "ization", "ities", "ments", "ing", "ies",
    "ied", "tion", "sion", "ment", "ness", "ity", "ers", "er", "ed",
    "es", "s",
]


def _stem(word: str) -> str:
    for suf in _SUFFIXES:
        if word.endswith(suf) and len(word) - len(suf) >= 3:
            return word[: -len(suf)]
    return word


_tfidf_vocab = None          # token -> index
_tfidf_doc_vectors = None    # np.array [num_docs, vocab_size]
_tfidf_doc_ids = None        # list of doc ids matching row order


def _tokenize(text: str):
    return [_stem(t) for t in _token_re.findall(text.lower()) if t not in _STOPWORDS and len(t) > 1]


def _build_tfidf_index():
    """(Re)build the local TF-IDF index from the current document store."""
    global _tfidf_vocab, _tfidf_doc_vectors, _tfidf_doc_ids

    docs = doc_store.list_documents()
    tokenized = [_tokenize(d["text"]) for d in docs]

    vocab = {}
    for tokens in tokenized:
        for tok in set(tokens):
            if tok not in vocab:
                vocab[tok] = len(vocab)

    n_docs = len(docs)
    n_vocab = max(len(vocab), 1)
    tf = np.zeros((n_docs, n_vocab), dtype=np.float64)
    for row, tokens in enumerate(tokenized):
        for tok in tokens:
            tf[row, vocab[tok]] += 1
        if tokens:
            tf[row] /= len(tokens)

    df = (tf > 0).sum(axis=0)
    idf = np.log((1 + n_docs) / (1 + df)) + 1.0

    _tfidf_vocab = vocab
    _tfidf_doc_vectors = tf * idf
    _tfidf_doc_ids = [d["id"] for d in docs]


def _vectorize_query(query: str):
    vec = np.zeros(max(len(_tfidf_vocab), 1), dtype=np.float64)
    for tok in _tokenize(query):
        idx = _tfidf_vocab.get(tok)
        if idx is not None:
            vec[idx] += 1
    return vec


def _cosine_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-8)
    b_norm = b / (np.linalg.norm(b) + 1e-8)
    return a_norm @ b_norm


def invalidate_cache():
    """Called by documents.py whenever documents are added/removed."""
    global _tfidf_vocab, _doc_embeddings, _embedded_doc_ids
    _tfidf_vocab = None
    _doc_embeddings = None
    _embedded_doc_ids = None


def _embed(texts):
    resp = _client.embeddings.create(model=config.AZURE_OPENAI_EMBED_DEPLOYMENT, input=texts)
    return np.array([e.embedding for e in resp.data])


def retrieve(query: str, top_k: int = None):
    """Returns the top_k most relevant documents regardless of access —
    RBAC filtering happens later in the Condition/Branch node, matching
    the governed 'retrieve then authorize' pattern from the workflow."""
    top_k = top_k or config.TOP_K
    docs = doc_store.list_documents()
    if not docs:
        return []

    if _client is not None:
        global _doc_embeddings, _embedded_doc_ids
        current_ids = [d["id"] for d in docs]
        if _doc_embeddings is None or _embedded_doc_ids != current_ids:
            _doc_embeddings = _embed([d["text"] for d in docs])
            _embedded_doc_ids = current_ids
        query_vec = _embed([query])[0]
        scores = _cosine_matrix(_doc_embeddings, query_vec)
        ordered_docs = docs
        min_score = 1e-9  # Azure embeddings rarely produce spurious overlap
    else:
        if _tfidf_vocab is None:
            _build_tfidf_index()
        query_vec = _vectorize_query(query)
        scores = _cosine_matrix(_tfidf_doc_vectors, query_vec)
        by_id = {d["id"]: d for d in docs}
        ordered_docs = [by_id[i] for i in _tfidf_doc_ids if i in by_id]
        min_score = config.MIN_RELEVANCE_SCORE

    ranked_idx = np.argsort(scores)[::-1][:top_k]
    results = []
    for i in ranked_idx:
        if scores[i] <= min_score:
            continue
        doc = ordered_docs[i]
        results.append({**doc, "score": float(scores[i])})
    return results
