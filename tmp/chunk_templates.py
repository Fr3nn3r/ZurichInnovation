import re
from typing import List, Dict
import uuid
import os
from docx import Document
import json


# Define helper to chunk paragraphs semantically
def chunk_paragraphs(paragraphs: List[str], max_words: int = 150) -> List[Dict]:
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len((current_chunk + " " + para).split()) > max_words:
            chunks.append({"id": str(uuid.uuid4()), "text": current_chunk.strip()})
            current_chunk = para
        else:
            current_chunk += " " + para

    if current_chunk.strip():
        chunks.append({"id": str(uuid.uuid4()), "text": current_chunk.strip()})

    return chunks


# Path to the folder containing the DOCX files
folder_path = "Data/Standard Guarantee texts (Updated)/"
all_chunks = []

# Iterate over all files in the folder
for filename in os.listdir(folder_path):
    if filename.endswith(".docx"):
        file_path = os.path.join(folder_path, filename)
        try:
            doc = Document(file_path)
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

            # Chunk paragraphs from this file
            chunks = chunk_paragraphs(paragraphs)

            # Add source information to each chunk
            for chunk in chunks:
                chunk["source"] = filename

            all_chunks.extend(chunks)
        except Exception as e:
            print(f"Error processing file {filename}: {e}")

# Save all chunks to a single JSON file
output_path = "chunks.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(all_chunks, f, indent=4, ensure_ascii=False)

print(
    f"Successfully processed all files and saved {len(all_chunks)} chunks to {output_path}"
)
