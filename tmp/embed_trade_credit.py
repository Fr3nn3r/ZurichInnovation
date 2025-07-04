import os
import re
import uuid
from dotenv import load_dotenv
import openai
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec
import tiktoken
from tqdm.auto import tqdm

# --- CONFIGURATION ---
# Load environment variables from .env file
load_dotenv()

# OpenAI & Pinecone config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
if not OPENAI_API_KEY or not PINECONE_API_KEY:
    raise ValueError("OPENAI_API_KEY and PINECONE_API_KEY must be set in the .env file")

openai.api_key = OPENAI_API_KEY

# Embedding model config
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536  # Dimension for text-embedding-3-small

# Pinecone config
PINECONE_INDEX_NAME = "trade-credit"

# Data config
DATA_DIR = "Data"
CHUNK_SIZE = 512  # tokens
CHUNK_OVERLAP = 50  # tokens
BATCH_SIZE = 100  # vectors to upsert at a time

# --- INITIALIZATION ---
print("Initializing clients...")
# Initialize Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)

# Initialize tiktoken encoder
tokenizer = tiktoken.get_encoding("cl100k_base")  # Encoder for text-embedding-3-small

# --- HELPER FUNCTIONS ---


def create_pinecone_index_if_not_exists():
    """Create the Pinecone index if it doesn't exist."""
    if PINECONE_INDEX_NAME not in pc.list_indexes().names():
        print(f"Creating serverless index '{PINECONE_INDEX_NAME}'...")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud="gcp", region="europe-west4"),
        )
        print("Index created successfully.")
    else:
        print(f"Index '{PINECONE_INDEX_NAME}' already exists.")
    return pc.Index(PINECONE_INDEX_NAME)


def get_text_chunks(text):
    """Splits text into chunks of a specified size with overlap."""
    tokens = tokenizer.encode(text)
    chunks = []
    for i in range(0, len(tokens), CHUNK_SIZE - CHUNK_OVERLAP):
        chunk_tokens = tokens[i : i + CHUNK_SIZE]
        chunk_text = tokenizer.decode(chunk_tokens)
        chunks.append(chunk_text)
    return chunks


def embed_texts(texts):
    """Embeds a list of texts using OpenAI's embedding model."""
    response = openai.embeddings.create(input=texts, model=EMBEDDING_MODEL)
    return [item.embedding for item in response.data]


# --- MAIN SCRIPT ---


def main():
    """Main function to process files, create embeddings, and upsert to Pinecone."""
    print("Starting embedding process...")

    index = create_pinecone_index_if_not_exists()

    # Get subdirectories in the data directory
    case_dirs = [
        d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))
    ]

    if not case_dirs:
        print(f"No case directories found in '{DATA_DIR}'. Exiting.")
        return

    for case_dir in tqdm(case_dirs, desc="Processing cases"):
        namespace_match = re.match(r"(Case \d+)", case_dir)
        if not namespace_match:
            print(f"Skipping directory, does not match 'Case X' pattern: {case_dir}")
            continue

        namespace = namespace_match.group(1)
        print(f"\nProcessing namespace: '{namespace}'")

        case_path = os.path.join(DATA_DIR, case_dir)

        # Find all .txt files in the subdirectory
        files_to_process = [f for f in os.listdir(case_path) if f.endswith(".txt")]

        if not files_to_process:
            print(f"No .txt files found in '{case_path}'.")
            continue

        all_chunks_for_namespace = []
        for filename in tqdm(
            files_to_process, desc=f"Reading files in {namespace}", leave=False
        ):
            file_path = os.path.join(case_path, filename)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                chunks = get_text_chunks(content)

                for i, chunk_text in enumerate(chunks):
                    chunk_id = str(uuid.uuid4())
                    metadata = {
                        "source": filename,
                        "text": chunk_text,
                        "chunk_number": i + 1,
                        "namespace": namespace,
                    }
                    all_chunks_for_namespace.append(
                        {"id": chunk_id, "text": chunk_text, "metadata": metadata}
                    )

            except Exception as e:
                print(f"Error processing file {file_path}: {e}")

        if not all_chunks_for_namespace:
            print(f"No text chunks generated for namespace '{namespace}'.")
            continue

        print(
            f"Generated {len(all_chunks_for_namespace)} chunks for namespace '{namespace}'."
        )
        print("Embedding and upserting chunks to Pinecone...")

        # Embed and upsert in batches
        for i in tqdm(
            range(0, len(all_chunks_for_namespace), BATCH_SIZE),
            desc=f"Upserting to {namespace}",
            leave=False,
        ):
            batch_chunks = all_chunks_for_namespace[i : i + BATCH_SIZE]

            texts_to_embed = [chunk["text"] for chunk in batch_chunks]

            try:
                embeddings = embed_texts(texts_to_embed)

                vectors_to_upsert = []
                for j, chunk in enumerate(batch_chunks):
                    vectors_to_upsert.append(
                        (chunk["id"], embeddings[j], chunk["metadata"])
                    )

                index.upsert(vectors=vectors_to_upsert, namespace=namespace)

            except Exception as e:
                print(
                    f"Error embedding or upserting batch for namespace {namespace}: {e}"
                )

    print("\n✅ Done: All chunks have been embedded and upserted to Pinecone.")


if __name__ == "__main__":
    main()
