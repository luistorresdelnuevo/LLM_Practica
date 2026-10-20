"""RAG sobre ``data/TENERIFE.pdf``.

Traslada las celdas validadas del notebook sin cambiar su comportamiento:
carga por página con ``pypdf``, ``RecursiveCharacterTextSplitter``,
embeddings con OpenAI, similitud coseno con NumPy, ``RAG_INSTRUCTIONS``,
``format_context_with_sources`` y ``answer_with_rag``.

La única novedad es una caché de embeddings en disco para no repetir la
indexación (y su coste) cada vez que se arranca la API.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from .config import (
    CACHE_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    INSUFFICIENT_INFO,
    PDF_PATH,
    SELECTED_EXPERIMENT,
    Settings,
)

logger = logging.getLogger(__name__)

RAG_INSTRUCTIONS = f"""
Eres un asistente turístico especializado en Tenerife.

Responde en español utilizando únicamente la información incluida
en el contexto recuperado.

Reglas obligatorias:

1. No utilices conocimiento externo.
2. No inventes datos que no aparezcan en el contexto.
3. Incluye después de cada afirmación relevante la referencia
   correspondiente con el formato [Fuente N].
4. Si el contexto no contiene la respuesta, responde exactamente:
   "{INSUFFICIENT_INFO}".
5. Si solo existe información parcial, indica claramente qué parte
   no puede responderse.
6. No cites una fuente que no respalde la afirmación.
""".strip()


def load_pdf_documents(pdf_path: Path = PDF_PATH) -> list[Document]:
    """Carga un ``Document`` por página con metadatos citables."""
    if not pdf_path.exists():
        raise FileNotFoundError(f"No se encontró el PDF en {pdf_path}")

    reader = PdfReader(str(pdf_path))
    docs = []
    for page_number, page in enumerate(reader.pages):
        page_text = (page.extract_text() or "").strip()
        docs.append(
            Document(
                page_content=page_text,
                metadata={
                    "source": str(pdf_path),
                    "page": page_number,
                    "page_label": reader.page_labels[page_number],
                    "total_pages": len(reader.pages),
                },
            )
        )
    return docs


def split_documents(
    docs: list[Document],
    *,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    experiment_name: str = SELECTED_EXPERIMENT,
    source_name: str = PDF_PATH.name,
) -> list[Document]:
    """Divide las páginas con texto y añade ``chunk_id`` y ``source_name``."""
    valid_docs = [doc for doc in docs if doc.page_content]
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )
    chunks = splitter.split_documents(valid_docs)
    for chunk_number, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = f"{experiment_name}-{chunk_number}"
        chunk.metadata["source_name"] = source_name
    return chunks


def embed_texts(client: Any, texts: list[str], *, model: str) -> np.ndarray:
    """Genera embeddings para una lista de textos (celda 15 del notebook)."""
    response = client.embeddings.create(model=model, input=texts)
    vectors = [item.embedding for item in response.data]
    return np.array(vectors, dtype=np.float32)


def cosine_similarity_matrix(
    query_vector: np.ndarray,
    matrix: np.ndarray,
) -> np.ndarray:
    """Similitud coseno entre una pregunta y todos los embeddings."""
    query_norm = np.linalg.norm(query_vector)
    matrix_norms = np.linalg.norm(matrix, axis=1)
    denominator = np.maximum(query_norm * matrix_norms, 1e-12)
    return (matrix @ query_vector) / denominator


def format_context_with_sources(retrieval_results: list[dict]) -> str:
    """Construye el contexto con una etiqueta verificable por fragmento."""
    blocks = []
    for number, result in enumerate(retrieval_results, start=1):
        header = (
            f"[Fuente {number}: {result['source']}, "
            f"página {result['page']}, chunk {result['chunk_id']}]"
        )
        blocks.append(f"{header}\n{result['text']}")
    return "\n\n".join(blocks)


def build_sources(retrieval_results: list[dict]) -> list[dict[str, Any]]:
    """Construye las referencias exclusivamente desde los metadatos."""
    return [
        {
            "reference": f"Fuente {number}",
            "source": result["source"],
            "page": result["page"],
            "chunk_id": result["chunk_id"],
            "score": result["score"],
        }
        for number, result in enumerate(retrieval_results, start=1)
    ]


@dataclass
class RagIndex:
    """Índice vectorial en memoria: la fila ``i`` corresponde a ``splits[i]``."""

    client: Any
    settings: Settings
    splits: list[Document]
    embeddings: np.ndarray

    @classmethod
    def build(
        cls,
        client: Any,
        settings: Settings,
        *,
        pdf_path: Path = PDF_PATH,
        cache_dir: Path | None = CACHE_DIR,
    ) -> "RagIndex":
        """Carga el PDF, lo fragmenta y genera o reutiliza los embeddings."""
        splits = split_documents(load_pdf_documents(pdf_path))
        if not splits:
            raise ValueError("No hay chunks disponibles para indexar.")

        texts = [chunk.page_content for chunk in splits]
        cache_file = None
        if cache_dir is not None:
            fingerprint = settings.embedding_model + "\n" + "\n".join(texts)
            digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16]
            cache_file = cache_dir / f"embeddings_{digest}.npy"
            if cache_file.exists():
                logger.info("Embeddings cargados de caché (%d chunks)", len(splits))
                return cls(client, settings, splits, np.load(cache_file))

        embeddings = embed_texts(client, texts, model=settings.embedding_model)
        if cache_file is not None:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            np.save(cache_file, embeddings)
        logger.info("Índice creado con %d chunks", len(splits))
        return cls(client, settings, splits, embeddings)

    def retrieve_chunks(self, query: str, *, k: int | None = None) -> list[dict]:
        """Recupera los ``k`` chunks más próximos a la consulta."""
        k = self.settings.top_k if k is None else k
        if not query.strip():
            raise ValueError("La consulta no puede estar vacía.")
        if k <= 0:
            raise ValueError("El valor de k debe ser mayor que cero.")

        query_embedding = embed_texts(
            self.client, [query], model=self.settings.embedding_model
        )[0]
        scores = cosine_similarity_matrix(query_embedding, self.embeddings)
        top_indices = np.argsort(scores)[::-1][:k]

        results = []
        for rank, index in enumerate(top_indices, start=1):
            chunk = self.splits[int(index)]
            results.append(
                {
                    "rank": rank,
                    "score": float(scores[int(index)]),
                    "chunk_id": chunk.metadata["chunk_id"],
                    "source": chunk.metadata["source_name"],
                    "page": chunk.metadata["page_label"],
                    "text": chunk.page_content,
                }
            )
        return results

    def answer_with_rag(self, question: str, *, k: int | None = None,
                        style: str | None = None) -> dict:
        """Recupera evidencias y genera una respuesta basada solo en ellas.

        ``style`` añade instrucciones de tono sin modificar las reglas del RAG.
        """
        if not question.strip():
            raise ValueError("La pregunta no puede estar vacía.")

        retrieval_results = self.retrieve_chunks(question, k=k)
        context = format_context_with_sources(retrieval_results)
        user_input = (
            f"Pregunta:\n{question}\n\n"
            f"Contexto recuperado:\n{context}\n\n"
            "Respuesta:"
        )
        response = self.client.responses.create(
            model=self.settings.generation_model,
            instructions=RAG_INSTRUCTIONS if not style else f"{RAG_INSTRUCTIONS}\n\n{style}",
            input=user_input,
            temperature=self.settings.temperature,
            top_p=self.settings.top_p,
            max_output_tokens=self.settings.max_output_tokens,
        )
        return {
            "question": question,
            "answer": response.output_text,
            "sources": build_sources(retrieval_results),
            "retrieved_context": retrieval_results,
            "response_id": response.id,
        }
