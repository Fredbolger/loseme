import re
from typing import List, Tuple

from loseme_core.models import Chunk, DocumentPart
from loseme_core.ids import make_chunk_id


# Regex that splits on sentence-ending punctuation followed by whitespace or end-of-string.
# Keeps the delimiter attached to the preceding sentence (positive lookbehind).
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


class SentenceAwareChunker:
    """
    Sentence-boundary-aware text chunker.

    Splits text into sentences using punctuation heuristics, then greedily
    groups sentences into chunks that stay within `max_chars`. Adjacent chunks
    share `overlap_sentences` sentences so context is not lost at boundaries.

    Advantages over SimpleTextChunker:
    - Never cuts mid-sentence, so chunks are always readable units.
    - Overlap is sentence-aligned, not byte-aligned.
    - No ML model required (unlike SemanticChunker).

    Parameters
    ----------
    max_chars : int
        Soft upper limit on chunk character length. A single sentence that
        exceeds this limit is emitted as its own chunk rather than dropped.
    overlap_sentences : int
        Number of sentences from the end of the previous chunk to prepend to
        the next chunk.
    min_chars : int
        Chunks shorter than this are merged into the next one (avoids tiny
        trailing chunks). Set to 0 to disable.
    """
    
    name = "sentence"
    version = "1.0"


    def __init__(
        self,
        max_chars: int = 800,
        overlap_sentences: int = 1,
        min_chars: int = 100,
    ):
        if overlap_sentences < 0:
            raise ValueError("overlap_sentences must be >= 0")
        self.max_chars = max_chars
        self.overlap_sentences = overlap_sentences
        self.min_chars = min_chars

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chunk(self, part: DocumentPart) -> Tuple[List[Chunk], List[str]]:
        sentences = self._split_sentences(part.text)
        if not sentences:
            return [], []

        groups = self._group_sentences(sentences)
        chunks: List[Chunk] = []
        chunk_texts: List[str] = []

        for index, group in enumerate(groups):
            text = " ".join(group)
            chunk_id = make_chunk_id(
                document_part_id=part.document_part_id,
                document_checksum=part.checksum,
                index=index,
            )
            chunks.append(
                Chunk(
                    id=chunk_id,
                    source_type=part.source_type,
                    source_path=part.source_path,
                    document_part_id=part.document_part_id,
                    document_checksum=part.checksum,
                    device_id=part.device_id,
                    unit_locator=part.unit_locator,
                    index=index,
                    text=text,
                    metadata={
                        "char_len": len(text),
                        "sentence_count": len(group),
                    },
                )
            )
            chunk_texts.append(text)

        return chunks, chunk_texts

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences on punctuation boundaries.
        Paragraphs (double newlines) always force a split regardless of
        punctuation, so structure like bullet lists is preserved.
        """
        # Normalise line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Split on paragraph breaks first, then on sentence endings within
        # each paragraph.
        sentences: List[str] = []
        for paragraph in text.split("\n\n"):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            for sent in _SENTENCE_SPLIT_RE.split(paragraph):
                sent = sent.strip()
                if sent:
                    sentences.append(sent)

        return sentences

    def _group_sentences(self, sentences: List[str]) -> List[List[str]]:
        """
        Greedily pack sentences into groups bounded by `max_chars`, with
        sentence-level overlap between adjacent groups.
        """
        groups: List[List[str]] = []
        current: List[str] = []
        current_len = 0

        i = 0
        while i < len(sentences):
            sent = sentences[i]
            sent_len = len(sent)

            fits = current_len + (1 if current else 0) + sent_len <= self.max_chars

            if fits or not current:
                # Always accept if current is empty (avoids infinite loop on
                # single sentences longer than max_chars).
                current.append(sent)
                current_len += (1 if len(current) > 1 else 0) + sent_len
                i += 1
            else:
                # Flush current group
                groups.append(current)
                # Seed next group with overlap tail of the flushed group
                overlap = current[-self.overlap_sentences:] if self.overlap_sentences else []
                current = list(overlap)
                current_len = sum(len(s) for s in current) + max(0, len(current) - 1)
                # Do NOT advance i — re-evaluate the same sentence in the new group

        # Flush the last group
        if current:
            # Merge tiny trailing chunks into the previous group
            if groups and self.min_chars and len(" ".join(current)) < self.min_chars:
                groups[-1].extend(
                    s for s in current if s not in groups[-1][-self.overlap_sentences:]
                )
            else:
                groups.append(current)

        return groups
