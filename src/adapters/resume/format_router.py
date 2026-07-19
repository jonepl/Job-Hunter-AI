"""ResumeFormatRouter — dispatch resume bytes to the right parser by format.

W5 accepts both ``.pdf`` and ``.docx`` uploads, but ``ResumeParserPort`` trades in
raw bytes with no filename, and ``ResumeService`` holds a single injected parser.
This router *is* that single parser: it sniffs the leading **magic bytes** and
delegates to the PDF or DOCX parser, so the port signature and the service stay
unchanged. Sniffing content (not the filename extension, which can lie) is the
robust choice — a misnamed ``.pdf`` that is really a Word doc still routes right.
"""

from src.core.ports.resume_parser_port import ResumeParserPort

# PDF files start with "%PDF"; .docx (a ZIP container) starts with the ZIP local
# file header "PK\x03\x04".
_PDF_MAGIC = b"%PDF"
_ZIP_MAGIC = b"PK\x03\x04"


class ResumeFormatRouter(ResumeParserPort):
    """Route resume bytes to a PDF or DOCX parser by sniffing magic bytes."""

    def __init__(self, pdf_parser: ResumeParserPort, docx_parser: ResumeParserPort) -> None:
        """Wire the format-specific parsers this router dispatches to.

        Args:
            pdf_parser: Parser for ``.pdf`` bytes.
            docx_parser: Parser for ``.docx`` bytes.
        """
        self._pdf_parser = pdf_parser
        self._docx_parser = docx_parser

    def extract_text(self, data: bytes) -> str:
        """Detect the format from the leading bytes and extract its text.

        Args:
            data: The raw uploaded file contents.

        Returns:
            The extracted, whitespace-stripped text corpus.

        Raises:
            ValueError: When the bytes are neither a PDF nor a ``.docx`` (or the
                delegated parser finds no extractable text).
        """
        if data.startswith(_PDF_MAGIC):
            return self._pdf_parser.extract_text(data)
        if data.startswith(_ZIP_MAGIC):
            return self._docx_parser.extract_text(data)
        raise ValueError("Unsupported resume format — upload a PDF or DOCX file.")
