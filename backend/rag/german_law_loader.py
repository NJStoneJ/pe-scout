"""德国法原文加载器 — 从本地 PDF/EPUB 提取 PE 相关法律文本"""

import os, re, logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from config import GERMAN_LAW_DIR
LAW_DIR = Path(GERMAN_LAW_DIR)

# Clean filenames (primary). Place files in GERMAN_LAW_DIR with these names.
LAW_FILES = {
    "AO": "AO.pdf",
    "EStG": "EStG.pdf",
    "KStG": "KStG.pdf",
    "UStG": "UStG.pdf",
    "HGB": "HGB.epub",
    "AktG": "AktG.pdf",
    "GmbHG": "GmbHG.pdf",
    "InsO": "InsO.pdf",
    "PartGG": "PartGG.pdf",
    "UmwStG": "UmwStG.pdf",
}

# Fallback: alternative filenames for backward compatibility
_FALLBACK_NAMES = {
    "AO": ["Lehrbuch Abgabenordnung (Uta Hey, Christian Lehnert) (z-library.sk, 1lib.sk, z-lib.sk).pdf"],
    "EStG": ["EStG () (z-library.sk, 1lib.sk, z-lib.sk).pdf"],
    "KStG": ["Kommentar Körperschaftsteuer KStG (Arne Schnitger, Oliver Fehrenbacher) (z-library.sk, 1lib.sk, z-lib.sk).pdf"],
    "UStG": ["UStG (Christoph Wäger (editor)) (z-library.sk, 1lib.sk, z-lib.sk).pdf"],
    "HGB": ["HGB (Jost Scholl) (z-library.sk, 1lib.sk, z-lib.sk).epub"],
    "AktG": ["AktG  Kommentar zum Aktiengesetz (Thomas Wachter) (z-library.sk, 1lib.sk, z-lib.sk).pdf"],
    "GmbHG": ["GmbHG ( etc.) (z-library.sk, 1lib.sk, z-lib.sk).pdf"],
    "InsO": ["InsO Kommentar zur Insolvenzordnung (Marie Luise Graf-Schlicker (editor)) (z-library.sk, 1lib.sk, z-lib.sk).pdf"],
    "PartGG": ["PartGG (Volker Römermann) (z-library.sk, 1lib.sk, z-lib.sk).pdf"],
    "UmwStG": ["Das Umwandlungssteuerrecht der Mitunternehmerschaft Eine Analyse der § 6 Abs. 5 EStG, § 24 UmwStG und der Realteilung anhand… (Lisa Astrid Riedel) (z-library.sk, 1lib.sk, z-lib.sk).pdf"],
}

# Laws whose FULL text is indexed (small + core PE provisions).
# All other laws are filtered to PE-relevant pages only to keep the index focused.
KEEP_FULL = {"AO", "HGB"}

# Pre-extracted JSON directory (produced by offline extraction script).
# If {GERMAN_LAW_DIR}/extracted_law_pe/{label}.json exists, it is used directly
# (no source PDF needed at runtime). Otherwise the loader extracts from source.
EXTRACTED_JSON_DIR = LAW_DIR / "extracted_law_pe"


def _resolve_file(label: str) -> Path | None:
    """Resolve a law file path: try clean name first, then fallbacks."""
    primary = LAW_DIR / LAW_FILES[label]
    if primary.exists():
        return primary
    for alt_name in _FALLBACK_NAMES.get(label, []):
        alt_path = LAW_DIR / alt_name
        if alt_path.exists():
            logger.info(f"Using fallback filename for {label}")
            return alt_path
    return None

# PE-relevant German legal terms for filtering
PE_TERMS = re.compile(
    r'Betriebs?st(ä|a)tt|Betriebstätte|Betriebsstätte|Betriebstaette|'
    r'§\s*12\s*AO|§\s*13\s*AO|'
    r'fest.*Geschäftseinrichtung|Dauerhaft.*Einrichtung|'
    r'ständig.*Vertreter|Vertreter.*Vollmacht|'
    r'Bauausführung.*Montage|Montage.*Dauer|'
    r'beschränkt.*Steuerpflicht|unbeschränkt.*Steuerpflicht|'
    r'Doppelbesteuerung.*abkommen|DBA|OECD.*Musterabkommen|'
    r'Gewerbebetrieb.*Inland|Inland.*Gewerbebetrieb|'
    r'Buchführung.*pflicht|Aufzeichnung.*pflicht|§\s*238|§\s*242|'
    r'Jahresabschluss.*Pflicht|Bilanz.*Pflicht|'
    r'Gewerbesteuer|Körperschaftsteuer.*beschränkt|'
    r'Umsatzsteuer.*ausländ|ausländ.*Unternehmer|'
    r'Veranlagung.*beschränkt|Quellensteuer|Abzugsteuer|'
    r'Verständigungsverfahren|Advance.*Pricing|APA|'
    r'Funktionsverlagerung|Transfer.*Pricing|Verrechnungspreis|'
    r'Dienstleistung.*DBA|Bauleistung.*DBA|'
    r'Lohnsteuer.*ausländ|Arbeitnehmer.*Entsendung',
    re.IGNORECASE
)


class GermanLawLoader:
    """从本地德国法 PDF/EPUB 加载文本并提取 PE 相关段落"""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or (Path(__file__).parent.parent.parent / "data")

    def load_all(self) -> list[dict]:
        """加载所有可用的德国法文件，返回文档列表"""
        documents = []
        for label in LAW_FILES:
            # 1) 优先使用预提取 JSON（运行时无需源 PDF）
            json_path = EXTRACTED_JSON_DIR / f"{label}.json"
            if json_path.exists():
                docs = self._load_json(label, json_path)
                documents.extend(docs)
                logger.info(f"  {label}: {len(docs)} chunks (pre-extracted JSON)")
                continue

            # 2) 回退到源 PDF/EPUB
            filepath = _resolve_file(label)
            if filepath is None:
                logger.info(f"{label}: file not found in {LAW_DIR} (place {LAW_FILES[label]} there)")
                continue

            logger.info(f"Loading {label}: {filepath.name[:60]}...")

            fname = filepath.name
            if fname.endswith('.pdf'):
                docs = self._load_pdf(label, filepath)
            elif fname.endswith('.epub'):
                docs = self._load_epub(label, filepath)
            else:
                continue

            documents.extend(docs)
            logger.info(f"  {label}: {len(docs)} chunks extracted")

        return documents

    def _load_json(self, label: str, filepath: Path) -> list[dict]:
        """Load pre-extracted chunks from JSON (written by offline extraction)."""
        try:
            import json
            raw = json.load(open(filepath, "r", encoding="utf-8"))
            for d in raw:
                d.setdefault("type", "german_law_fulltext")
                d.setdefault("law", label)
            return raw
        except Exception as e:
            logger.warning(f"Failed to load JSON {filepath}: {e}")
            return []

    def _load_pdf(self, label: str, filepath: Path) -> list[dict]:
        """Extract PE-relevant text chunks from PDF"""
        try:
            import fitz
        except ImportError:
            logger.warning("pymupdf not installed, skipping PDF")
            return []

        docs = []
        doc = fitz.open(str(filepath))

        current_chunk = []
        current_chunk_chars = 0
        chunk_start_page = 0
        TARGET_CHUNK_SIZE = 2000
        CHUNK_OVERLAP = 200

        for page_num in range(doc.page_count):
            text = doc[page_num].get_text()
            if not text or len(text.strip()) < 20:
                continue

            # Clean: remove excessive whitespace, fix line breaks
            text = re.sub(r'\s+', ' ', text).strip()

            # For large books, filter to PE-relevant pages only (AO/HGB kept full)
            if label not in KEEP_FULL:
                if not PE_TERMS.search(text):
                    continue

            paragraphs = re.split(r'(?<=[.!?])\s+(?=[A-ZÄÖÜ])', text)

            for para in paragraphs:
                para = para.strip()
                if len(para) < 30:
                    continue

                if current_chunk_chars + len(para) > TARGET_CHUNK_SIZE:
                    chunk_text = ' '.join(current_chunk)
                    docs.append({
                        "id": f"de_law_{label}_{chunk_start_page}_{len(docs)}",
                        "text": chunk_text,
                        "source": f"{label} (page {chunk_start_page + 1}-{page_num + 1})",
                        "type": "german_law_fulltext",
                        "law": label,
                        "page_range": f"{chunk_start_page + 1}-{page_num + 1}",
                    })
                    # Keep overlap
                    overlap_text = current_chunk[-min(len(current_chunk), 3):]
                    current_chunk = overlap_text + [para]
                    current_chunk_chars = sum(len(p) for p in current_chunk)
                    chunk_start_page = page_num
                else:
                    if not current_chunk:
                        chunk_start_page = page_num
                    current_chunk.append(para)
                    current_chunk_chars += len(para)

        # Last chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            docs.append({
                "id": f"de_law_{label}_{chunk_start_page}_{len(docs)}",
                "text": chunk_text,
                "source": f"{label} (page {chunk_start_page + 1}-{doc.page_count})",
                "type": "german_law_fulltext",
                "law": label,
                "page_range": f"{chunk_start_page + 1}-{doc.page_count}",
            })

        doc.close()
        return docs

    def _load_epub(self, label: str, filepath: Path) -> list[dict]:
        """Extract text chunks from EPUB"""
        try:
            from ebooklib import epub
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("ebooklib/beautifulsoup4 not installed, skipping EPUB")
            return []

        docs = []
        try:
            book = epub.read_epub(str(filepath))
        except Exception as e:
            logger.warning(f"Failed to read EPUB {filepath}: {e}")
            return []

        chapters = []
        for item in book.get_items():
            if item.get_type() == 9:  # ITEM_DOCUMENT
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                text = soup.get_text()
                text = re.sub(r'\s+', ' ', text).strip()
                if len(text) > 100:
                    chapters.append(text)

        full_text = ' '.join(chapters)

        # Chunk
        TARGET_CHUNK_SIZE = 2000
        words = full_text.split()
        current_chunk = []
        current_size = 0

        for word in words:
            current_chunk.append(word)
            current_size += len(word) + 1
            if current_size >= TARGET_CHUNK_SIZE:
                docs.append({
                    "id": f"de_law_{label}_epub_{len(docs)}",
                    "text": ' '.join(current_chunk),
                    "source": f"{label} (EPUB)",
                    "type": "german_law_fulltext",
                    "law": label,
                })
                current_chunk = current_chunk[-50:]  # overlap
                current_size = sum(len(w) + 1 for w in current_chunk)

        if current_chunk:
            docs.append({
                "id": f"de_law_{label}_epub_{len(docs)}",
                "text": ' '.join(current_chunk),
                "source": f"{label} (EPUB)",
                "type": "german_law_fulltext",
                "law": label,
            })

        return docs

    def get_stats(self, documents: list[dict]) -> dict:
        """统计加载的文档"""
        laws = {}
        total_chars = 0
        for doc in documents:
            law = doc.get("law", "unknown")
            if law not in laws:
                laws[law] = 0
            laws[law] += 1
            total_chars += len(doc.get("text", ""))

        return {
            "total_documents": len(documents),
            "total_chars": total_chars,
            "by_law": laws,
        }
