import os
import json
from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

# --------------------------------------------------------
# Load Environment Variables
# --------------------------------------------------------

load_dotenv()

# --------------------------------------------------------
# Configuration
# --------------------------------------------------------

JSON_FILE = "data.json"
VECTOR_DB = "./vectordb"

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
LLM_MODEL = "gpt-5"

# --------------------------------------------------------
# Load JSON
# --------------------------------------------------------

def load_json_documents(file_path):

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    documents = []

    for item in data:

        documents.append(
            Document(
                page_content=json.dumps(item, indent=2),
                metadata=item
            )
        )

    return documents

# --------------------------------------------------------
# Create Vector Database
# --------------------------------------------------------

def build_vector_database():

    print("Loading JSON...")

    documents = load_json_documents(JSON_FILE)

    print(f"Loaded {len(documents)} JSON records")

    embeddings = OpenAIEmbeddings(
        model=EMBEDDING_MODEL
    )

    vectordb = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=VECTOR_DB
    )

    print("Vector Database Created Successfully")

    return vectordb

# --------------------------------------------------------
# Load Existing Vector Database
# --------------------------------------------------------

def load_vector_database():

    embeddings = OpenAIEmbeddings(
        model=EMBEDDING_MODEL
    )

    db = Chroma(
        persist_directory=VECTOR_DB,
        embedding_function=embeddings
    )

    return db

# --------------------------------------------------------
# Retrieve Documents
# --------------------------------------------------------

def retrieve_documents(question, db, k=5):

    retriever = db.as_retriever(
        search_kwargs={"k": k}
    )

    docs = retriever.invoke(question)

    return docs

# --------------------------------------------------------
# Ask LLM
# --------------------------------------------------------

def ask_llm(question, docs):

    llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=0
    )

    context = "\n\n".join(
        doc.page_content for doc in docs
    )

    prompt = f"""
You are an intelligent RAG assistant.

Below is the retrieved JSON data.

{context}

User Question:
{question}

Instructions:

1. Answer ONLY from the retrieved JSON.
2. Do not make up information.
3. If the answer is unavailable, return

{{
    "error":"Information not found"
}}

4. Return ONLY valid JSON.
5. Do NOT return markdown.
"""

    response = llm.invoke(prompt)

    return response.content

# --------------------------------------------------------
# Main
# --------------------------------------------------------

def main():

    if not os.path.exists(VECTOR_DB):

        db = build_vector_database()

    else:

        db = load_vector_database()

    print("\nJSON RAG Ready")
    print("Type 'exit' to quit.\n")

    while True:

        question = input("Question: ")

        if question.lower() == "exit":
            break

        docs = retrieve_documents(question, db)

        print("\nRetrieved Documents:\n")

        for i, doc in enumerate(docs, start=1):
            print("=" * 60)
            print(f"Document {i}")
            print(doc.page_content)

        print("\nGenerating Response...\n")

        answer = ask_llm(question, docs)

        print(answer)
        print("\n")

if __name__ == "__main__":
    main()