class DocumentIndexingError(Exception):
    """Errore generico durante l'indicizzazione dei documenti."""


class PDFExtractionError(DocumentIndexingError):
    """Impossibile estrarre testo da un file PDF."""


class EmbeddingError(DocumentIndexingError):
    """Errore durante la creazione degli embeddings OpenAI."""


class QdrantIndexingError(DocumentIndexingError):
    """Errore durante il salvataggio degli embeddings in Qdrant."""


class RAGError(Exception):
    """Errore durante la generazione di una risposta RAG."""


class RetrievalError(RAGError):
    """Errore durante il recupero dei chunk da Qdrant."""


class ChatCompletionError(RAGError):
    """Errore durante la chiamata al modello GPT."""


class ProductError(Exception):
    """Errore generico relativo ai prodotti."""


class ProductNotFoundError(ProductError):
    """Prodotto non trovato nel database."""


class ProductImportError(ProductError):
    """Errore durante l'importazione prodotti da Excel."""


class CompatibilityError(ProductError):
    """Errore relativo ai collegamenti di compatibilità tra prodotti."""


class OrderImportError(ProductError):
    """Errore durante l'importazione dello storico ordini."""


class CopilotError(Exception):
    """Errore durante l'analisi Commercial Copilot."""


class AuthenticationError(Exception):
    """Credenziali EasyOne non valide o sessione scaduta."""


def is_authentication_error(exc: BaseException) -> bool:
    """
    Riconosce AuthenticationError anche con PyInstaller (modulo duplicato).
  """
    if isinstance(exc, AuthenticationError):
        return True
    return exc.__class__.__name__ == "AuthenticationError"


class AuthorizationError(Exception):
    """Permesso insufficiente per l'operazione richiesta."""


class MailError(Exception):
    """Errore integrazione posta (OAuth, lettura o invio)."""


class CalendarError(Exception):
    """Errore integrazione calendario (EasyOne o Outlook)."""
