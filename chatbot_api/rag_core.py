from langchain_ollama import OllamaEmbeddings, OllamaLLM
import chromadb
import os
from sentence_transformers import SentenceTransformer

llm_model = "llama3.2"

chroma_client = chromadb.PersistentClient(path=os.path.join(os.getcwd(), "chroma_db"))

# Commenting out the old ChromaDBEmbeddingFunction as it's no longer used with SentenceTransformer directly in this setup.
# class ChromaDBEmbeddingFunction:
#     def __init__(self, langchain_embeddings):
#         self.langchain_embeddings = langchain_embeddings
#
#     def __call__(self, input):
#         if isinstance(input, str):
#             input = [input]
#         return self.langchain_embeddings.embed_documents(input)
#     def name(self):
#         return "ollama_langchain_embeddings"

# # embedding = ChromaDBEmbeddingFunction(
# #     OllamaEmbeddings(model=llm_model, base_url="http://localhost:11434")
# # )

# Instantiate the SentenceTransformer model
sentence_transformer_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# Define a new embedding function compatible with ChromaDB's expectations
# when a SentenceTransformer model is used directly.
# ChromaDB can often use sentence-transformers directly if they are passed,
# but we can also create a wrapper for clarity or future customization.
class SentenceTransformerEmbeddingFunction(chromadb.EmbeddingFunction):
    def __init__(self, model):
        self.model = model

    def __call__(self, texts: chromadb.Documents) -> chromadb.Embeddings:
        return self.model.encode(list(texts), convert_to_tensor=False).tolist()

embedding_function = SentenceTransformerEmbeddingFunction(sentence_transformer_model)

collection_name = "rag_collection"
collection = chroma_client.get_or_create_collection(
    name=collection_name,
    metadata={"description": "A collection for RAG with SentenceTransformer - all-MiniLM-L6-v2"},
    embedding_function=embedding_function
)

def add_documents_to_collection(docs_with_ids):
    documents, ids = zip(*docs_with_ids)
    collection.add(documents=list(documents), ids=list(ids))

def query_chromadb(query_text, n_results=3):
    results = collection.query(query_texts=[query_text], n_results=n_results)
    return results["documents"], results["metadatas"]

def query_ollama(prompt):
    llm = OllamaLLM(model=llm_model)
    return llm.invoke(prompt)

def rag_pipeline(query_text):
    retrieved_docs, _ = query_chromadb(query_text)
    context = " ".join(retrieved_docs[0]) if retrieved_docs else "No relevant documents found."

    augmented_prompt = f"""You are an intelligent assistant that only answers based on the given context.

                        Context:
                        {context}

                        Question:
                        {query_text}

                        Instructions:
                        - If the context is not relevant to the question, respond with natural language.    
                        - If the context is relevant, answer concisely and accurately based only on the context.

                        Answer:"""
    print("######## Augmented Prompt ########\n", augmented_prompt)
    return query_ollama(augmented_prompt)
