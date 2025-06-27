import openai
from pinecone.grpc import PineconeGRPC as Pinecone

# ✅ Config
openai.api_key = ""
pc = Pinecone(api_key="")
index = pc.Index("zurich-bond-clauses")

# ✅ Your test clause
query_text = "Sollte eine Bestimmung dieser Bürgschaft unwirksam oder nicht durchführbar sein oder werden oder sollte sich in dieser Bürgschaft eine Lücke herausstellen, so hat dies keinen Einfluss auf die übrigen Bestimmungen dieser Bürgschaft.     ,den     UnterschriftWF PL1124A/Ausgabe: 1848-22WF PL1124A/Ausgabe: 1848-22"

# ✅ Embed it
# Using the same model as the one for uploading embeddings
embed_response = openai.embeddings.create(
    input=[query_text], model="text-embedding-3-small"
)
query_vector = embed_response.data[0].embedding

# ✅ Query Pinecone
result = index.query(vector=query_vector, top_k=3, include_metadata=True)

# ✅ Show results
print(f"Query: '{query_text}'\n")
print("Top 3 matches:")
for match in result["matches"]:
    print(f"\nScore: {match['score']:.4f}")
    print(f"Source: {match['metadata'].get('source', 'N/A')}")
    print(f"Match text: {match['metadata'].get('text', 'Text not found in metadata.')}")
