import fitz  # PyMuPDF
import re
from typing import List, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.logger import get_logger
import config

logger = get_logger(__name__)

class Chunk:
    def __init__(self, title: str, text: str, start_page: int, end_page: int):
        self.title = title
        self.text = text
        self.start_page = start_page
        self.end_page = end_page

    def __repr__(self):
        return f"Chunk(title={self.title}, pages={self.start_page}-{self.end_page}, length={len(self.text)})"


def extract_text_from_pdf(path: str) -> List[Dict]:
    """Extracts raw text per page from a PDF."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"PDF not found at {path}")
        
    doc = fitz.open(path)
    pages = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        pages.append({"page_num": page_num + 1, "text": text})
        
    return pages

def chunk_by_sections(pages: List[Dict]) -> List[Chunk]:
    """
    Splits text logically by section headers.
    Assumes section headers might look like "1. Introduction" or "4.1 Access Control"
    or are just in ALL CAPS. This is a heuristic that can be adjusted.
    """
    full_text = ""
    page_map = [] # list mapping character index to page number
    
    for p in pages:
        start_idx = len(full_text)
        full_text += p["text"] + "\n"
        end_idx = len(full_text)
        page_map.append((start_idx, end_idx, p["page_num"]))
        
    def get_page_num(char_idx):
        for start, end, pnum in page_map:
            if start <= char_idx <= end:
                return pnum
        return page_map[-1][2] if page_map else 1

    # Simple heuristic: Lines that are ALL CAPS, optionally starting with a section number like "1. " or "1.1 "
    # We will split on lines matching this.
    header_pattern = re.compile(r"^(?:\d+\.\s*)?[A-Z][A-Z\s]+$", re.MULTILINE)
    
    matches = list(header_pattern.finditer(full_text))
    
    if not matches:
        # If no headers found, treat the whole document as one chunk
        return [Chunk("Document", full_text, pages[0]["page_num"], pages[-1]["page_num"])]

    chunks = []
    
    # Text before the first header
    if matches[0].start() > 0:
        pre_text = full_text[0:matches[0].start()].strip()
        if pre_text:
            chunks.append(Chunk("Preamble", pre_text, get_page_num(0), get_page_num(matches[0].start())))

    for i, match in enumerate(matches):
        title = match.group().strip()
        start_idx = match.end()
        end_idx = matches[i+1].start() if i + 1 < len(matches) else len(full_text)
        
        text = full_text[start_idx:end_idx].strip()
        if len(text) > 50: # Ignore empty or extremely short sections
            start_page = get_page_num(start_idx)
            end_page = get_page_num(end_idx)
            chunks.append(Chunk(title, text, start_page, end_page))
            
    return chunks

def split_oversized_chunks(chunks: List[Chunk], max_tokens: int = config.MAX_CHUNK_TOKENS) -> List[Chunk]:
    """
    Sub-splits chunks that exceed the token budget.
    We approximate 1 token ≈ 4 characters.
    """
    max_chars = max_tokens * 4
    result = []
    
    for chunk in chunks:
        if len(chunk.text) <= max_chars:
            result.append(chunk)
        else:
            logger.info(f"Chunk '{chunk.title}' exceeds budget ({len(chunk.text)} chars). Sub-splitting.")
            paragraphs = chunk.text.split("\n\n")
            
            current_text = ""
            part_num = 1
            for p in paragraphs:
                if len(current_text) + len(p) > max_chars and current_text:
                    result.append(Chunk(f"{chunk.title} (Part {part_num})", current_text.strip(), chunk.start_page, chunk.end_page))
                    current_text = p + "\n\n"
                    part_num += 1
                else:
                    current_text += p + "\n\n"
                    
            if current_text.strip():
                result.append(Chunk(f"{chunk.title} (Part {part_num})", current_text.strip(), chunk.start_page, chunk.end_page))
                
    return result

def ingest_pdf(path: str) -> List[Chunk]:
    pages = extract_text_from_pdf(path)
    logger.info(f"Extracted {len(pages)} pages from {path}")
    chunks = chunk_by_sections(pages)
    logger.info(f"Found {len(chunks)} logical sections.")
    final_chunks = split_oversized_chunks(chunks)
    logger.info(f"Produced {len(final_chunks)} final chunks after sub-splitting.")
    return final_chunks
