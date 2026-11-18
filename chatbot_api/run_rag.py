from embed_docs import load_and_split_documents
from rag_core import add_documents_to_collection, rag_pipeline, collection


if collection.count() == 0:
    docs_with_ids = load_and_split_documents("data")
    add_documents_to_collection(docs_with_ids)
    
print(f"Count :{collection.count()}") 


query = "How do I detect a leak in a wall?"
response = rag_pipeline(query)

print("######## LLM Response ########\n", response)