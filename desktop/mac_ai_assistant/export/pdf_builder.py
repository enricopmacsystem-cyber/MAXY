from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from fpdf import FPDF

from mac_ai_assistant.branding import APP_DISPLAY_NAME, ORGANIZATION_NAME

_FONT_REGULAR: Path | None = None
_FONT_BOLD: Path | None = None
if sys.platform == "win32":
    _win_fonts = Path(r"C:\Windows\Fonts")
    _arial = _win_fonts / "arial.ttf"
    _arial_bold = _win_fonts / "arialbd.ttf"
    if _arial.is_file():
        _FONT_REGULAR = _arial
        _FONT_BOLD = _arial_bold if _arial_bold.is_file() else _arial


@dataclass
class QuoteLine:
    code: str
    description: str
    quantity: str = "1"
    unit_price: str = "0.00"

    @property
    def line_total(self) -> Decimal:
        try:
            qty = Decimal(str(self.quantity).replace(",", "."))
            price = Decimal(str(self.unit_price).replace(",", "."))
            return qty * price
        except (InvalidOperation, ValueError):
            return Decimal("0")


@dataclass
class QuoteDocument:
    quote_number: str
    quote_date: date
    customer_name: str = ""
    customer_code: str = ""
    customer_email: str = ""
    customer_phone: str = ""
    notes: str = ""
    lines: list[QuoteLine] = field(default_factory=list)
    title: str = "PREVENTIVO"

    @property
    def subtotal(self) -> Decimal:
        return sum((line.line_total for line in self.lines), Decimal("0"))


def _escape_html(text: str) -> str:
    normalized = (
        text.replace("—", "-")
        .replace("–", "-")
        .replace("'", "'")
        .replace("'", "'")
        .replace(""", '"')
        .replace(""", '"')
        .replace("…", "...")
    )
    return (
        normalized.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _create_pdf() -> FPDF:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    if _FONT_REGULAR:
        pdf.add_font("AppFont", "", str(_FONT_REGULAR))
        pdf.add_font("AppFont", "B", str(_FONT_BOLD or _FONT_REGULAR))
        pdf.set_font("AppFont", size=11)
    return pdf


def _write_html_pdf(pdf: FPDF, html: str) -> None:
    pdf.add_page()
    if _FONT_REGULAR:
        pdf.write_html(html, font_family="AppFont")
    else:
        pdf.write_html(html)


def build_quote_pdf(document: QuoteDocument, output_path: Path) -> Path:
    rows_html = ""
    for line in document.lines:
        total = line.line_total
        rows_html += (
            "<tr>"
            f"<td>{_escape_html(line.code)}</td>"
            f"<td>{_escape_html(line.description)}</td>"
            f"<td align='right'>{_escape_html(line.quantity)}</td>"
            f"<td align='right'>{_escape_html(line.unit_price)}</td>"
            f"<td align='right'>{total:.2f}</td>"
            "</tr>"
        )
    if not rows_html:
        rows_html = (
            "<tr><td colspan='5' align='center'>"
            "<i>Nessuna riga articolo</i></td></tr>"
        )

    notes_block = ""
    if document.notes.strip():
        notes_block = (
            f"<p><b>Note:</b><br>{_escape_html(document.notes).replace(chr(10), '<br>')}</p>"
        )

    html = f"""
    <h1 align="center">{_escape_html(document.title)}</h1>
    <p align="center"><b>{_escape_html(ORGANIZATION_NAME)}</b> — {_escape_html(APP_DISPLAY_NAME)}</p>
    <hr>
    <p>
    <b>N.</b> {_escape_html(document.quote_number)}<br>
    <b>Data:</b> {document.quote_date.strftime("%d/%m/%Y")}<br>
    <b>Cliente:</b> {_escape_html(document.customer_name or "—")}<br>
    <b>Codice cliente:</b> {_escape_html(document.customer_code or "—")}<br>
    <b>Email:</b> {_escape_html(document.customer_email or "—")}<br>
    <b>Telefono:</b> {_escape_html(document.customer_phone or "—")}
    </p>
    <table border="1" width="100%" cellpadding="4">
    <thead>
    <tr bgcolor="#e8eef5">
    <th width="15%">Codice</th>
    <th width="40%">Descrizione</th>
    <th width="10%">Q.tà</th>
    <th width="15%">Prezzo unit.</th>
    <th width="20%">Importo</th>
    </tr>
    </thead>
    <tbody>
    {rows_html}
    </tbody>
    </table>
    <p align="right"><b>Totale: EUR {document.subtotal:.2f}</b></p>
    {notes_block}
    <hr>
    <p align="center"><font size="9">Documento generato automaticamente da {_escape_html(APP_DISPLAY_NAME)}</font></p>
    """

    pdf = _create_pdf()
    _write_html_pdf(pdf, html)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    return output_path


def build_text_pdf(
    *,
    title: str,
    body: str,
    output_path: Path,
    subtitle: str | None = None,
) -> Path:
    safe_body = _escape_html(body).replace("\n", "<br>")
    subtitle_html = ""
    if subtitle:
        subtitle_html = f"<p align='center'>{_escape_html(subtitle)}</p>"
    html = f"""
    <h1 align="center">{_escape_html(title)}</h1>
    <p align="center"><b>{_escape_html(ORGANIZATION_NAME)}</b></p>
    {subtitle_html}
    <hr>
    <p>{safe_body}</p>
    <hr>
    <p align="center"><font size="9">Esportato da {_escape_html(APP_DISPLAY_NAME)}</font></p>
    """
    pdf = _create_pdf()
    _write_html_pdf(pdf, html)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    return output_path
