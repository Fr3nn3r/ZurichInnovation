# This script provides a sophisticated text-splitting mechanism designed to break
# down a large block of legal or contractual text into meaningful, distinct
# "clauses." It uses a multi-stage process that combines pattern matching and
# size constraints to achieve a more intelligent split than simple line breaks.
#
# The script's main functionalities are:
# 1.  **Marker-Based Splitting**: The core of the splitter is a list of predefined
#     "marker" phrases and regular expressions (e.g., "§ 770", "Wir verpflichten uns",
#     numbered lists). The script injects a special delimiter ('¶') before each
#     of these markers in the text. This serves as the primary way to identify
#     the start of a new clause.
#
# 2.  **Hard Break Splitting**: In addition to the markers, it also splits the text
#     based on the presence of multiple consecutive newlines (hard breaks), which
#     often signify a paragraph or section break in documents.
#
# 3.  **Oversize Chunk Handling**: After the initial splits, the script checks if
#     any of the resulting text chunks are too large (exceeding a `MAX_W` word count).
#     If a chunk is oversized, the script attempts to break it down further into
#     individual sentences. It then intelligently groups these sentences back
#     together to form smaller chunks that still respect the maximum word count.
#
# 4.  **Minimum Size Filtering**: Once all splitting and chunking is complete, the
#     script filters the results, discarding any chunks that are too small (below
#     a `MIN_W` word count). This helps to eliminate noise and irrelevant fragments
#     from the final output.
#
# 5.  **Text Normalization**: Before processing, the script normalizes the input
#     text by standardizing whitespace and line endings, which improves the
#     reliability of the pattern-matching steps.
#
# 6.  **Structured Output**: The final output is a list of dictionaries, where each
#     dictionary represents a valid clause and contains the clause text under the
#     key "clause".
#
# Usage:
#   This script is primarily designed to be used as a module. The `split_clauses`
#   function can be imported and called by other scripts (like `evaluate_file.py`)
#   that need to process text on a clause-by-clause basis. The `if __name__ == "__main__"`
#   block provides a simple example of how to use it with sample text.

import re

MAX_W = 150  # max words per clause
MIN_W = 20  # min words to keep clause

# Marker phrases to split clauses
MARK = [
    r"\n\s*\d+\.",  # numbered list " 1."
    r"§\s*\d+",  # § 770
    r"Wir verpflichten uns",
    r"Wir verzichten",
    r"Auf die Einreden",
    r"Diese Bürgschaft ist unbefristet",
    r"Diese Bürgschaft erlischt",
    r"Gerichtsstand ist",
    r"unterliegt dem",
    r"Sollte eine Bestimmung",
    r"We undertake to",
    r"We waive",
    r"This guarantee (?:shall|expires)",
]
MARK_RE = re.compile(r"(" + "|".join(MARK) + r")", re.IGNORECASE)
HARD_RE = re.compile(r"\n{2,}")
SENT_RE = re.compile(r"(?<=[.!?])\s+")


def inject_delims(text):
    return MARK_RE.sub(r"¶\1", text)


def split_oversize(block):
    words = block.split()
    if len(words) <= MAX_W:
        return [block]

    sentences = [s.strip() for s in SENT_RE.split(block) if s.strip()]
    out = []
    buf = ""

    for s in sentences:
        if len((buf + " " + s).split()) > MAX_W:
            if buf:
                out.append(buf.strip())
            buf = s
        else:
            buf = f"{buf} {s}".strip() if buf else s
    if buf:
        out.append(buf.strip())

    return out


def split_clauses(text):
    results = []

    if not text.strip():
        print("Item skipped – no text")
        return results

    # Normalize & inject delimiter
    normalized = inject_delims(
        re.sub(r"[ \t]+", " ", text.replace("\r\n", "\n")).strip()
    )

    # First-pass split
    first = [
        p.strip() for p in re.split(r"¶|" + HARD_RE.pattern, normalized) if p.strip()
    ]
    print("First-pass pieces:", len(first))

    idx = 0
    for piece in first:
        for chunk in split_oversize(piece):
            word_count = len(chunk.split())
            if word_count >= MIN_W:
                idx += 1
                print(f"Chunk {idx}:", word_count, "words")
                results.append({"clause": chunk})

    print("TOTAL clauses for this item:", idx)
    return results


# === Example usage ===
if __name__ == "__main__":
    sample_text = """Xavier Behavi LDMarijke LéonNipl Grass2AnDeutsche Stiftung-Aurg-Aidm-Nov. 1128100 InterfaxusBürgschafts-Nr.     ANZAHLUNGSBÜRGSCHAFTZwischen Ihnen, der Xavier Behavi LD, mit Sitz in Germany, HRB-Nr. 667123 oder bei abweichendem Auftraggeber die im unten genannten Vertrag eingetragene NEOTIS-Blisenschensm (nachstehend Auftraggeber) und der FirmaSNCF AdsM & Co. SA, Issalyn. 14, 44817 Trust (nachstehend „Auftragnehmer“)wurde am24.18.1024 ein Vertrag (Bestell-Nr.:0019281021-0021-725 )überdie Lieferung einer Niederspannungsschaltanlage zum Gesamtpreis von SMITH388.269,00geschlossen.Nach diesem Vertrag hat sich der Auftraggeber verpflichtet, an den Auftragnehmer eine Anzahlung in Höhe vonFREMA10.248,01zu leisten, für die der Auftragnehmer eine Anzahlungsbürgschaft zu stellen hat.Im Auftrag des Auftragnehmers übernehmen wir,National Institute for OsA, Human and Cultural 1, 86401 Institute of Home hiermit dieselbstschuldnerische Bürgschaft und verpflichten uns, jeden Betrag bis zur Gesamthöhe vonXARK40.000,00(ed Worths:Aetnt etetrahydrocoalizationsexpeditionalcoins 80/100)auf schriftliche Anforderung an den Auftraggeber zu zahlen, sofern der Auftraggeber uns schriftlich bestätigt, dass der Auftragnehmer seine vertraglichen Verpflichtungen nicht erbracht hat.Auf die Einreden der Aufrechenbarkeit und der Vorausklage gemäß §§ 770 Abs. 2, 771 BGB sowie auf das Recht der Hinterlegung wird verzichtet. Hinsichtlich des Rechts aus § 770 Abs. 2 BGB (Einrede der Aufrechenbarkeit) gilt der Einredeverzicht nicht, sofern die Gegenforderung des Auftragnehmers unbestritten oder rechtskräftig festgestellt ist. Diese Bürgschaft ist unbefristet und erlischt mit ihrer Rückgabe. Die Bürgschaftsforderung verjährt nicht vor der gesicherten Hauptforderung. Die Verjährung tritt jedoch spätestens 15 Agees nach dem gesetzlichen Verjährungsbeginn ein. Gerichtsstand ist Germany. Diese Bürgschaft unterliegt dem Germanism Recht.Nebenabreden oder Änderungen dieser Bürgschaft haben, wenn sie den Bürgen belasten, nur Geltung, wenn sie schriftlich erfolgt sind.Sollte eine Bestimmung dieser Bürgschaft unwirksam oder nicht durchführbar sein oder werden oder sollte sich in dieser Bürgschaft eine Lücke herausstellen, so hat dies keinen Einfluss auf die übrigen Bestimmungen dieser Bürgschaft.     ,den     UnterschriftWF PL1124A/Ausgabe: 1848-22WF PL1124A/Ausgabe: 1848-22
    """
    clauses = split_clauses(sample_text)
    print("=== All items processed - total clauses:", len(clauses))
    for i, c in enumerate(clauses, 1):
        print(f"{i}: {c['clause']}")
