import json
import openai
from pinecone.grpc import PineconeGRPC as Pinecone
import uuid
from tqdm import tqdm

# ✅ Step 1: Load your cleaned clauses
with open("chunks_v3_cleaned_normalized.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)

# ✅ Step 2: OpenAI & Pinecone config
# openai.api_key = ""
# pc = Pinecone(api_key="")

index = pc.Index("zurich-bond-clauses")


# ✅ Step 3: Embed + upsert
def embed_text(text):
    response = openai.embeddings.create(input=[text], model="text-embedding-3-small")
    return response.data[0].embedding


batch_size = 20
to_upsert = []

for chunk in tqdm(chunks):
    vector = embed_text(chunk["text"])
    to_upsert.append(
        (chunk["id"], vector, {"source": chunk["source"], "text": chunk["text"]})
    )

    # Upload in batches
    if len(to_upsert) >= batch_size:
        index.upsert(vectors=to_upsert)
        to_upsert = []

# Final batch
if to_upsert:
    index.upsert(vectors=to_upsert)

print("✅ Done: All chunks embedded and upserted to Pinecone.")
