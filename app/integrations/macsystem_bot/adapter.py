"""Adapter Hub Maxy → motore bot_manuali (ChromaDB + Claude)."""

from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from functools import lru_cache, wraps
from pathlib import Path
from typing import Any

from app.config.settings import Settings, get_settings
from app.integrations.macsystem_bot.paths import MultiRootManualDir

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TechnicalChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class TechnicalAssistantResult:
    answer: str
    sources: list[str]
    found: bool


def _manual_roots(settings: Settings) -> list[Path]:
    roots: list[Path] = []
    for value in (
        settings.documents_network_manual_path,
        settings.documents_network_datasheet_path,
        settings.macsystem_local_manual_path,
    ):
        text = (value or "").strip()
        if text:
            roots.append(Path(text))
    return roots


def _configure_process_env(settings: Settings) -> None:
    if settings.anthropic_api_key:
        os.environ["ANTHROPIC_KEY"] = settings.anthropic_api_key
    if settings.chroma_dir:
        os.environ["CHROMA_DIR"] = str(settings.chroma_dir)
    roots = _manual_roots(settings)
    if roots:
        os.environ["MANUALI_DIR"] = str(roots[0])
    os.environ.setdefault("BOT_TOKEN", "maxy-hub-technical")


@lru_cache(maxsize=1)
def _load_engine():
    settings = get_settings()
    _configure_process_env(settings)

    import app.integrations.macsystem_bot.bot_engine as engine

    roots = _manual_roots(settings)
    if roots:
        engine.MANUALI_DIR = MultiRootManualDir(roots)  # type: ignore[assignment]

    if settings.chroma_dir:
        chroma_path = Path(settings.chroma_dir)
        engine.CHROMA_DIR = chroma_path
        try:
            import chromadb
            from chromadb.utils import embedding_functions

            engine.chroma_client = chromadb.PersistentClient(path=str(chroma_path))
            engine.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="paraphrase-multilingual-MiniLM-L12-v2"
            )
            engine.collection = engine.chroma_client.get_or_create_collection(
                name="manuali",
                embedding_function=engine.embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as exc:
            logger.error("ChromaDB non disponibile: %s", exc)

    if settings.anthropic_api_key:
        engine.ANTHROPIC_KEY = settings.anthropic_api_key

    _apply_maxy_performance_patches(engine)
    return engine


def _apply_maxy_performance_patches(engine: Any) -> None:
    """Riduce latenza Hub senza saltare linee guida/datasheet (necessari per risposte corrette)."""

    _orig_estrai = engine.estrai_testo_file

    @lru_cache(maxsize=512)
    def _estrai_testo_cached(path_str: str) -> str:
        return _orig_estrai(Path(path_str))

    def estrai_testo_file_cached(path: Path) -> str:
        try:
            key = str(path.resolve())
        except OSError:
            key = str(path)
        return _estrai_testo_cached(key)

    engine.estrai_testo_file = estrai_testo_file_cached  # type: ignore[assignment]

    orig_pertinente = engine._modello_dahua_pertinente_domanda

    @wraps(orig_pertinente)
    def modello_pertinente_migliorato(codice: str, domanda_low: str) -> bool:
        codice_up = codice.upper()
        if any(
            k in domanda_low
            for k in ("audio", "bidirez", "two-way", "two way", "speaker", "parlare", "talk")
        ):
            if codice_up.startswith("HAC-") or "HAC-HDW" in codice_up or "HAC-HFW" in codice_up:
                return False
        return orig_pertinente(codice, domanda_low)

    engine._modello_dahua_pertinente_domanda = modello_pertinente_migliorato  # type: ignore[assignment]

    @wraps(engine.carica_datasheet_per_dimensionamento)
    def carica_datasheet_parallelo(
        domanda: str,
        linee_guida: str,
        max_modelli: int = 10,
        max_chars_total: int = 12000,
    ) -> tuple[str, set]:
        sezioni = engine.seleziona_sezioni_linee_guida(domanda, linee_guida)
        codici = engine.estrai_codici_modello_da_testo(sezioni)
        if len(codici) < 3:
            codici = list(
                dict.fromkeys(
                    codici + engine.estrai_codici_modello_da_testo(linee_guida[:20000])
                )
            )

        domanda_low = domanda.lower()
        codici = [
            c for c in codici if engine._modello_dahua_pertinente_domanda(c, domanda_low)
        ]
        codici.sort(key=lambda c: engine._priorita_modello_dimensionamento(c, domanda_low))

        per_modello = max(1500, max_chars_total // max(max_modelli, 1))
        candidati = codici[: max(max_modelli + 4, 12)]

        def _carica_codice(codice: str) -> tuple[str, str, str] | None:
            pdf = engine.trova_datasheet_dahua(codice)
            if not pdf:
                logger.info("Datasheet non trovato per candidato linee guida: %s", codice)
                return None
            testo = engine.estrai_testo_file(pdf)
            if not testo:
                return None
            estratto = engine.estrai_sezioni_rilevanti_datasheet(testo, domanda, per_modello)
            return codice, pdf.name, estratto

        caricati: list[tuple[str, str, str]] = []
        ordine = {c: i for i, c in enumerate(candidati)}
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(_carica_codice, codice): codice for codice in candidati}
            for future in as_completed(futures):
                row = future.result()
                if row:
                    caricati.append(row)

        caricati.sort(key=lambda row: ordine.get(row[0], 999))

        contesto = ""
        fonti: set = set()
        chars = 0
        for codice, nome_pdf, estratto in caricati:
            if len(fonti) >= max_modelli or chars >= max_chars_total:
                break
            contesto += f"\n=== DATASHEET {codice} ({nome_pdf}) ===\n{estratto}\n"
            fonti.add(nome_pdf)
            chars += len(estratto)
            logger.info("Datasheet dimensionamento caricato: %s -> %s", codice, nome_pdf)

        return contesto, fonti

    engine.carica_datasheet_per_dimensionamento = carica_datasheet_parallelo  # type: ignore[assignment]


def warmup_technical_engine() -> None:
    """Precarica ChromaDB e modello embedding all'avvio Hub (evita attesa alla prima domanda)."""
    settings = get_settings()
    if not (settings.anthropic_api_key or "").strip():
        return
    try:
        engine = _load_engine()
        count = int(engine.collection.count())
        logger.info("Warmup assistente tecnico: ChromaDB %s chunk", count)
        if count > 0:
            engine.collection.query(query_texts=["telecamera dahua"], n_results=1)
    except Exception as exc:
        logger.warning("Warmup assistente tecnico non completato: %s", exc)


class TechnicalAssistantAdapter:
    """Espone genera_risposta del bot Telegram come servizio sincrono per l'Hub."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def is_configured(self) -> bool:
        return bool((self.settings.anthropic_api_key or "").strip())

    def chroma_ready(self) -> bool:
        try:
            engine = _load_engine()
            return int(engine.collection.count()) > 0
        except Exception as exc:
            logger.warning("ChromaDB non pronto: %s", exc)
            return False

    def ask(
        self,
        question: str,
        history: list[TechnicalChatMessage] | None = None,
    ) -> TechnicalAssistantResult:
        if not self.is_configured():
            raise RuntimeError(
                "ANTHROPIC_API_KEY non configurata in hub.env — richiesta per la modalità tecnica."
            )

        engine = _load_engine()
        storia = [
            {"role": msg.role, "content": msg.content}
            for msg in (history or [])
            if msg.role in ("user", "assistant") and msg.content.strip()
        ]

        try:
            risultato: dict[str, Any] = asyncio.run(
                engine.genera_risposta(question.strip(), storia or None)
            )
        except Exception as exc:
            logger.exception("Errore motore tecnico Mac System")
            raise RuntimeError(f"Errore assistente tecnico: {exc}") from exc

        return TechnicalAssistantResult(
            answer=str(risultato.get("testo", "")).strip(),
            sources=[str(s) for s in risultato.get("fonti", [])],
            found=bool(risultato.get("trovato", False)),
        )
