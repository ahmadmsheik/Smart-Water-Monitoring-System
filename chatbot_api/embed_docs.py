from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import TextLoader, PyPDFLoader
import os

def load_and_split_documents(data_dir="data"):
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    docs = []

    for fname in os.listdir(data_dir):
        path = os.path.join(data_dir, fname)
        if fname.endswith(".txt"):
            loader = TextLoader(path)
        elif fname.endswith(".pdf"):
            loader = PyPDFLoader(path)
        else:
            continue

        try:
            raw_docs = loader.load()
            split_docs = splitter.split_documents(raw_docs)
            for i, doc in enumerate(split_docs):
                docs.append((doc.page_content.strip(), f"{fname}_chunk_{i}"))
        except Exception as e:
            print(f"❌ Skipped {fname} due to error: {e}")
            
    return docs