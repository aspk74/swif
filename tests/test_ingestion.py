import fitz
import os
import tempfile
from pipeline.ingestion import extract_text_from_pdf, chunk_by_sections, split_oversized_chunks, Chunk

def test_chunk_by_sections():
    pages = [
        {"page_num": 1, "text": "Compliance Policy\n\n1. INTRODUCTION\nThis is the introduction. It must be longer than fifty characters to avoid being filtered out.\n\n2. NETWORK SECURITY\nFirewalls must be on at all times to prevent unauthorized access across the perimeter network."},
        {"page_num": 2, "text": "3. ACCESS CONTROL\nPasswords must be long and complex, requiring at least fourteen characters, uppercase letters, and special symbols."}
    ]
    
    chunks = chunk_by_sections(pages)
    
    assert len(chunks) == 4
    assert chunks[0].title == "Preamble"
    assert chunks[1].title == "1. INTRODUCTION"
    assert chunks[2].title == "2. NETWORK SECURITY"
    assert chunks[3].title == "3. ACCESS CONTROL"

def test_split_oversized_chunks():
    # max_tokens = 10 -> max_chars = 40
    chunk1 = Chunk("Short", "This is short.", 1, 1) # 14 chars
    
    # 52 chars total. Will split on paragraph \n\n
    long_text = "This is a very long paragraph that exceeds limit.\n\nHere is another one."
    chunk2 = Chunk("Long", long_text, 1, 2) 
    
    result = split_oversized_chunks([chunk1, chunk2], max_tokens=10)
    
    assert len(result) == 3
    assert result[0].title == "Short"
    assert result[1].title == "Long (Part 1)"
    assert result[2].title == "Long (Part 2)"
    
    assert "exceeds limit" in result[1].text
    assert "Here is another" in result[2].text
