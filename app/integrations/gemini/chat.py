import json
import re

from google.genai import types

from app.config.settings import Settings, get_settings
from app.core.exceptions import ChatCompletionError
from app.core.logging import get_logger
from app.integrations.gemini.client import get_gemini_client
from app.integrations.qdrant.retriever import RetrievedChunk

logger = get_logger(__name__)

_MAXY_IDENTITY = (
    "Il tuo nome è sempre Maxy: non dire di essere Gemini, Google, ChatGPT o altro modello."
)


_QUOTA_MARKERS = ("quota", "resource_exhausted", "rate limit", "too many requests")
_INVALID_KEY_MARKERS = ("api key", "api_key", "invalid", "unauthorized", "permission denied")

# Modelli con quote gratuite più ampie, provati in ordine se il principale è esaurito.
_FALLBACK_CHAT_MODELS = (
    "gemini-2.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
)


def _is_quota_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in _QUOTA_MARKERS)


def _format_gemini_error(exc: Exception) -> str:
    message = str(exc).lower()
    if _is_quota_error(exc):
        return (
            "Quota Gemini esaurita. Soluzioni:\n"
            "• Attendere il reset (di solito entro 24 ore)\n"
            "• In hub.env usare GEMINI_CHAT_MODEL=gemini-2.5-flash-lite\n"
            "• Creare una nuova chiave su https://aistudio.google.com/apikey\n"
            "• Verificare limiti su https://aistudio.google.com/"
        )
    if any(marker in message for marker in _INVALID_KEY_MARKERS) and "key" in message:
        return (
            "Chiave Gemini non valida. Aggiornare GEMINI_API_KEY in hub.env "
            "(https://aistudio.google.com/apikey)."
        )
    return f"Errore servizio AI Maxy: {exc}"


def _rag_system_prompt(assistant_name: str) -> str:
    return f"""Sei {assistant_name}, assistente tecnico per magazzinieri di un distributore tecnologico.
{_MAXY_IDENTITY}

Regole obbligatorie:
1. Rispondi SOLO usando le informazioni presenti nei documenti forniti nel contesto.
2. Se la risposta non è contenuta nei documenti, rispondi esattamente:
   "Non ho trovato informazioni sufficienti nei documenti indicizzati per rispondere a questa domanda."
3. Non inventare dati, specifiche tecniche o procedure non presenti nel contesto.
4. Rispondi in italiano, in modo chiaro e operativo.
5. Cita sempre le fonti alla fine della risposta, una per riga, nel formato:
   [Fonte: NOME_PDF | Pagina: N | Sezione: TITOLO_SEZIONE]
6. Usa solo le fonti effettivamente utilizzate per costruire la risposta.

Formato di output richiesto (JSON valido):
{{
  "answer": "testo della risposta in italiano",
  "sources": [
    {{
      "pdf_name": "nome.pdf",
      "page": 1,
      "section": "Titolo sezione"
    }}
  ]
}}
"""


def _commercial_system_prompt(assistant_name: str) -> str:
    return f"""Sei {assistant_name}, assistente commerciale e di magazzino per un distributore di prodotti tecnologici.
{_MAXY_IDENTITY}

Il tuo interlocutore è personale commerciale o magazziniere che ha bisogno di risposte rapide, precise e operative.

Regole obbligatorie:
1. Usa SOLO le informazioni presenti nel contesto fornito (catalogo, disponibilità, PDF, compatibilità, storico ordini).
2. Non inventare prezzi, giacenze, specifiche tecniche o codici articolo.
3. Se mancano dati per rispondere, indicalo chiaramente senza inventare.
4. Rispondi sempre in italiano, tono professionale e diretto.
5. Per le informazioni tecniche dai PDF, cita la fonte nel testo (nome PDF, pagina, sezione).
6. Evidenzia azioni utili per commerciale/magazzino (disponibilità, alternative, upsell, accessori).
7. Se ci sono scorte basse o esaurimento, segnalalo con priorità.

Formato di output richiesto (JSON valido):
{{
  "answer": "Risposta operativa strutturata in testo (max 300 parole). Usa elenco puntato se utile.",
  "technical_summary": "Solo informazioni tecniche estratte dai PDF. Stringa vuota se nessun PDF rilevante."
}}
"""


class ChatService:
    """Genera risposte Maxy tramite Google Gemini."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = get_gemini_client(self.settings)
        self.model = self.settings.gemini_chat_model
        self.temperature = self.settings.gemini_chat_temperature

    def _model_chain(self) -> list[str]:
        models: list[str] = []
        for name in (self.model, *_FALLBACK_CHAT_MODELS):
            if name and name not in models:
                models.append(name)
        return models

    def _generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        last_exc: Exception | None = None
        for model in self._model_chain():
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=self.temperature,
                        response_mime_type="application/json",
                    ),
                )
            except Exception as exc:
                last_exc = exc
                if _is_quota_error(exc) and model != self._model_chain()[-1]:
                    logger.warning(
                        "Quota esaurita per modello %s, provo fallback Gemini",
                        model,
                    )
                    continue
                raise ChatCompletionError(_format_gemini_error(exc)) from exc

            if model != self.model:
                logger.info("Maxy usa modello Gemini di fallback: %s", model)

            raw = (response.text or "").strip()
            if not raw:
                raise ChatCompletionError("Risposta Maxy vuota")
            return raw

        raise ChatCompletionError(_format_gemini_error(last_exc or RuntimeError("Nessun modello Gemini disponibile")))

    def _generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        last_exc: Exception | None = None
        for model in self._model_chain():
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=self.temperature,
                    ),
                )
            except Exception as exc:
                last_exc = exc
                if _is_quota_error(exc) and model != self._model_chain()[-1]:
                    logger.warning(
                        "Quota esaurita per modello %s, provo fallback Gemini",
                        model,
                    )
                    continue
                raise ChatCompletionError(_format_gemini_error(exc)) from exc

            if model != self.model:
                logger.info("Maxy usa modello Gemini di fallback: %s", model)
            return (response.text or "").strip()

        raise ChatCompletionError(_format_gemini_error(last_exc or RuntimeError("Nessun modello Gemini disponibile")))

    def generate_rag_answer(
        self,
        question: str,
        chunks: list[RetrievedChunk],
    ) -> dict:
        if not chunks:
            logger.warning("generate_rag_answer chiamato senza chunk")
            return {
                "answer": (
                    "Non ho trovato informazioni sufficienti nei documenti indicizzati "
                    "per rispondere a questa domanda."
                ),
                "sources": [],
            }

        context = self._build_context(chunks)
        user_prompt = (
            f"DOMANDA:\n{question.strip()}\n\n"
            f"DOCUMENTI DISPONIBILI:\n{context}\n\n"
            "Genera la risposta rispettando rigorosamente le regole del system prompt."
        )

        logger.info(
            "Invio richiesta Maxy/Gemini (modello=%s, chunk=%d)",
            self.model,
            len(chunks),
        )

        raw_content = self._generate_json(
            system_prompt=_rag_system_prompt(self.settings.ai_assistant_name),
            user_prompt=user_prompt,
        )

        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            logger.warning("JSON non valido da Gemini, fallback testuale: %s", exc)
            parsed = self._fallback_parse(raw_content, chunks)

        answer = str(parsed.get("answer", "")).strip()
        sources = self._normalize_sources(parsed.get("sources", []), chunks)

        if not answer:
            raise ChatCompletionError("Risposta Maxy priva del campo 'answer'")

        return {"answer": answer, "sources": sources}

    def generate_commercial_answer(
        self,
        question: str,
        context: object,
    ) -> dict:
        from app.services.commercial_assistant_service import _GatheredContext

        if not isinstance(context, _GatheredContext):
            raise ChatCompletionError("Contesto commerciale non valido")

        prompt_context = self._build_commercial_context(context)
        user_prompt = (
            f"DOMANDA DEL OPERATORE:\n{question.strip()}\n\n"
            f"DATI RACCOLTI DAL SISTEMA:\n{prompt_context}\n\n"
            "Genera la risposta operativa per commerciale/magazzino rispettando le regole."
        )

        logger.info("Invio richiesta Maxy commerciale (modello=%s)", self.model)

        raw_content = self._generate_json(
            system_prompt=_commercial_system_prompt(self.settings.ai_assistant_name),
            user_prompt=user_prompt,
        )

        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError:
            return {"answer": raw_content.strip(), "technical_summary": ""}

        answer = str(parsed.get("answer", "")).strip()
        if not answer:
            return self._commercial_fallback(context)

        return {
            "answer": answer,
            "technical_summary": str(parsed.get("technical_summary", "")).strip(),
        }

    @staticmethod
    def _build_commercial_context(context: object) -> str:
        from app.schemas.product import ProductResponse
        from app.services.commercial_assistant_service import _GatheredContext
        from app.utils.availability import availability_info

        if not isinstance(context, _GatheredContext):
            return ""

        blocks: list[str] = []

        if context.catalog_hits:
            blocks.append("=== CATALOGO PRODOTTI ===")
            for index, hit in enumerate(context.catalog_hits, start=1):
                product = hit.product
                avail = availability_info(ProductResponse.model_validate(product))
                blocks.append(
                    "\n".join(
                        [
                            f"[PRODOTTO {index}]",
                            f"Codice: {product.internal_code}",
                            f"Produttore: {product.manufacturer}",
                            f"Categoria: {product.category}",
                            f"Descrizione: {product.description}",
                            f"Prezzo: {product.price} EUR",
                            f"Disponibilità: {avail.status_label}",
                            f"Manuale: {product.manual_url or 'N/D'}",
                            f"Scheda tecnica: {product.datasheet_url or 'N/D'}",
                        ]
                    )
                )
        else:
            blocks.append("=== CATALOGO ===\nNessun prodotto trovato nel catalogo.")

        if context.pdf_chunks:
            blocks.append("\n=== DOCUMENTI PDF ===")
            for index, chunk in enumerate(context.pdf_chunks, start=1):
                blocks.append(
                    "\n".join(
                        [
                            f"[PDF {index}]",
                            f"File: {chunk.source_file}",
                            f"Pagina: {chunk.page_number}",
                            f"Sezione: {chunk.section}",
                            f"Contenuto: {chunk.content}",
                        ]
                    )
                )
        else:
            blocks.append("\n=== DOCUMENTI PDF ===\nNessun estratto PDF rilevante.")

        if context.compatibility:
            blocks.append("\n=== COMPATIBILITÀ ===")
            compat = context.compatibility
            for label, items in [
                ("Accessori", compat.accessories),
                ("Alternative", compat.alternatives),
                ("Ricambi", compat.spare_parts),
                ("Complementari", compat.complementary),
            ]:
                if items:
                    codes = ", ".join(
                        f"{item.product.internal_code} ({item.notes or '—'})"
                        for item in items
                    )
                    blocks.append(f"{label}: {codes}")
                else:
                    blocks.append(f"{label}: nessuno")

        if context.bought_together:
            blocks.append("\n=== ACQUISTATI INSIEME (STORICO ORDINI) ===")
            for item in context.bought_together:
                blocks.append(
                    f"- {item.internal_code}: {item.description} — {item.reason}"
                )
        else:
            blocks.append("\n=== ACQUISTATI INSIEME ===\nNessun dato storico ordini.")

        return "\n".join(blocks)

    @staticmethod
    def _commercial_fallback(context: object) -> dict:
        from app.services.commercial_assistant_service import _GatheredContext

        if not isinstance(context, _GatheredContext):
            return {
                "answer": "Non ho trovato informazioni sufficienti per rispondere.",
                "technical_summary": "",
            }

        if context.primary_product:
            product = context.primary_product
            return {
                "answer": (
                    f"Articolo {product.internal_code} — {product.description}\n"
                    f"Produttore: {product.manufacturer}\n"
                    f"Prezzo: {product.price} EUR\n"
                    f"Disponibilità: {product.availability} pezzi"
                ),
                "technical_summary": "",
            }

        return {
            "answer": (
                "Non ho trovato un articolo corrispondente nel catalogo. "
                "Prova a indicare il codice interno o una descrizione più specifica."
            ),
            "technical_summary": "",
        }

    @staticmethod
    def _build_context(chunks: list[RetrievedChunk]) -> str:
        blocks: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            blocks.append(
                "\n".join(
                    [
                        f"[DOCUMENTO {index}]",
                        f"PDF: {chunk.source_file}",
                        f"Pagina: {chunk.page_number}",
                        f"Sezione: {chunk.section}",
                        f"Rilevanza: {chunk.score:.3f}",
                        "Contenuto:",
                        chunk.content,
                    ]
                )
            )
        return "\n\n---\n\n".join(blocks)

    @staticmethod
    def _normalize_sources(
        raw_sources: list | None,
        chunks: list[RetrievedChunk],
    ) -> list[dict]:
        normalized: list[dict] = []
        seen: set[tuple[str, int, str]] = set()

        if isinstance(raw_sources, list):
            for item in raw_sources:
                if not isinstance(item, dict):
                    continue
                pdf_name = str(item.get("pdf_name", "")).strip()
                page = item.get("page")
                section = str(item.get("section", "Generale")).strip() or "Generale"
                if not pdf_name or page is None:
                    continue
                key = (pdf_name, int(page), section)
                if key in seen:
                    continue
                seen.add(key)
                normalized.append(
                    {
                        "pdf_name": pdf_name,
                        "page": int(page),
                        "section": section,
                    }
                )

        if normalized:
            return normalized

        for chunk in chunks:
            key = (chunk.source_file, chunk.page_number, chunk.section)
            if key in seen:
                continue
            seen.add(key)
            normalized.append(
                {
                    "pdf_name": chunk.source_file,
                    "page": chunk.page_number,
                    "section": chunk.section,
                }
            )

        return normalized

    def generate_copilot_summary(self, bundle: object, analysis: object) -> str:
        from app.integrations.easyone.adapter import EasyOneProductBundle
        from app.services.commercial_copilot_service import _CopilotAnalysis

        if not isinstance(bundle, EasyOneProductBundle) or not isinstance(
            analysis, _CopilotAnalysis
        ):
            raise ChatCompletionError("Contesto Commercial Copilot non valido")

        product = bundle.product
        prompt = (
            "Analizza i dati Commercial Copilot e produci una sintesi operativa "
            "per un commerciale (max 150 parole, italiano, elenco puntato).\n\n"
            f"ARTICOLO: {product.internal_code} — {product.description}\n"
            f"PRODUTTORE: {product.manufacturer}\n"
            f"CATEGORIA: {product.category}\n"
            f"DISPONIBILITÀ: {bundle.availability.status_label}\n"
            f"STORICO ORDINI: {bundle.sales_history.order_count}\n"
            f"COMPATIBILITÀ: {[i.internal_code for i in analysis.compatibility]}\n"
            f"ALTERNATIVE: {[i.internal_code for i in analysis.alternatives]}\n"
            f"ACQUISTATI INSIEME: {[i.internal_code for i in analysis.bought_together]}\n"
            f"SIMILI: {[i.internal_code for i in analysis.similar_products]}\n"
            f"COMPLEMENTARI: {[i.internal_code for i in analysis.complementary]}\n"
            f"MARGINE SUPERIORE: {[i.internal_code for i in analysis.higher_margin]}\n"
            f"CROSS-SELL: {[i.internal_code for i in analysis.cross_selling]}\n"
        )

        return self._generate_text(
            system_prompt=(
                f"Sei {self.settings.ai_assistant_name}, copilota commerciale "
                f"per un distributore tecnologico. {_MAXY_IDENTITY} "
                "Suggerisci azioni concrete di vendita senza inventare dati."
            ),
            user_prompt=prompt,
        )

    def generate_simple_completion(self, *, system_prompt: str, user_prompt: str) -> str:
        return self._generate_text(system_prompt=system_prompt, user_prompt=user_prompt)

    def search_documents_online(self, query: str) -> dict:
        """Ricerca documentazione tecnica sul web tramite Gemini + Google Search."""
        cleaned = query.strip()
        if not cleaned:
            return {"answer": "Inserire una query di ricerca.", "results": []}

        assistant = self.settings.ai_assistant_name
        user_prompt = (
            f"Trova manuali, schede tecniche e datasheet ufficiali per: {cleaned}\n"
            "Elenca i risultati più utili con titolo, link e tipo documento."
        )
        last_exc: Exception | None = None
        response = None
        for model in self._model_chain():
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=(
                            f"Sei {assistant}, assistente tecnico per un distributore. "
                            f"{_MAXY_IDENTITY} Cerca documentazione ufficiale sul web. "
                            "Rispondi in italiano, in modo conciso."
                        ),
                        temperature=0.2,
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                    ),
                )
                break
            except Exception as exc:
                last_exc = exc
                if _is_quota_error(exc) and model != self._model_chain()[-1]:
                    logger.warning("Ricerca web: fallback modello %s", model)
                    continue
                raise ChatCompletionError(_format_gemini_error(exc)) from exc

        if response is None:
            raise ChatCompletionError(_format_gemini_error(last_exc or RuntimeError("Ricerca web non disponibile")))

        answer = (response.text or "").strip()
        results: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        for candidate in response.candidates or []:
            metadata = getattr(candidate, "grounding_metadata", None)
            if not metadata:
                continue
            for chunk in getattr(metadata, "grounding_chunks", None) or []:
                web = getattr(chunk, "web", None)
                if not web:
                    continue
                uri = getattr(web, "uri", None) or ""
                if not uri or uri in seen_urls:
                    continue
                seen_urls.add(uri)
                title = getattr(web, "title", None) or uri
                results.append(
                    {
                        "title": str(title),
                        "url": str(uri),
                        "doc_type": "web",
                    }
                )

        url_pattern = re.compile(r"https?://[^\s\]>]+")
        for match in url_pattern.finditer(answer):
            uri = match.group(0).rstrip(".,)")
            if uri not in seen_urls:
                seen_urls.add(uri)
                results.append({"title": uri, "url": uri, "doc_type": "web"})

        return {"answer": answer, "results": results[:12]}

    @staticmethod
    def _fallback_parse(raw_content: str, chunks: list[RetrievedChunk]) -> dict:
        sources: list[dict] = []
        pattern = re.compile(
            r"\[Fonte:\s*(?P<pdf>[^|\]]+)\|\s*Pagina:\s*(?P<page>\d+)\|\s*Sezione:\s*(?P<section>[^\]]+)\]",
            re.IGNORECASE,
        )
        for match in pattern.finditer(raw_content):
            sources.append(
                {
                    "pdf_name": match.group("pdf").strip(),
                    "page": int(match.group("page")),
                    "section": match.group("section").strip(),
                }
            )

        if not sources and chunks:
            sources = [
                {
                    "pdf_name": chunk.source_file,
                    "page": chunk.page_number,
                    "section": chunk.section,
                }
                for chunk in chunks
            ]

        return {"answer": raw_content.strip(), "sources": sources}
