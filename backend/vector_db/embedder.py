from typing import Optional

from sentence_transformers import SentenceTransformer

from .config import EMBEDDING_MODEL_NAME

_model: Optional[SentenceTransformer] = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"Loading embedding model '{EMBEDDING_MODEL_NAME}' (first run downloads it)...")
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def embedding_dimension() -> int:
    return get_model().get_embedding_dimension()


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_model()
    return model.encode(texts, show_progress_bar=False, convert_to_numpy=True).tolist()


def embed_query(text: str) -> list[float]:
    return get_model().encode(text, show_progress_bar=False, convert_to_numpy=True).tolist()
