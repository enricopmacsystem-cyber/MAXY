from dataclasses import dataclass
from pathlib import Path

import tiktoken

from app.core.logging import get_logger
from app.utils.pdf_parser import PDFPage
from app.utils.section_detector import detect_section_from_text

logger = get_logger(__name__)


@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    source_file: str
    page_number: int
    chunk_index: int
    section: str
    content: str
    token_count: int


def _get_encoder(model_name: str = "cl100k_base"):
    return tiktoken.get_encoding(model_name)


def _split_text_by_tokens(
    text: str,
    encoder: tiktoken.Encoding,
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    tokens = encoder.encode(text)
    if not tokens:
        return []

    if len(tokens) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(encoder.decode(chunk_tokens))

        if end >= len(tokens):
            break

        start = max(end - chunk_overlap, start + 1)

    return chunks


def chunk_pages(
    pdf_path: Path,
    pages: list[PDFPage],
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> list[TextChunk]:
    """
    Suddivide il contenuto delle pagine PDF in chunk con overlap e sezione.
    """
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap deve essere minore di chunk_size")

    encoder = _get_encoder()
    chunks: list[TextChunk] = []
    global_index = 0

    logger.info(
        "Chunking di %s: %d pagine, size=%d, overlap=%d",
        pdf_path.name,
        len(pages),
        chunk_size,
        chunk_overlap,
    )

    for page in pages:
        page_section = detect_section_from_text(page.content)
        page_chunks = _split_text_by_tokens(
            text=page.content,
            encoder=encoder,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        for local_index, content in enumerate(page_chunks):
            section = detect_section_from_text(content, fallback=page_section)
            token_count = len(encoder.encode(content))
            chunk = TextChunk(
                chunk_id=f"{pdf_path.stem}-p{page.page_number}-c{local_index}",
                source_file=pdf_path.name,
                page_number=page.page_number,
                chunk_index=global_index,
                section=section,
                content=content,
                token_count=token_count,
            )
            chunks.append(chunk)
            global_index += 1

            logger.debug(
                "Creato chunk %s (%d token, pagina %d, sezione=%s)",
                chunk.chunk_id,
                token_count,
                page.page_number,
                section,
            )

    logger.info("Generati %d chunk da %s", len(chunks), pdf_path.name)
    return chunks
