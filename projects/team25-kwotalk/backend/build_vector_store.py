import json
import os
from typing import List, Dict

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

law = "law.json"
dbvector = "dbvector"
model = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
law_index_faiss= "law_index.faiss"
law_metadata_json = "law_metadata.json"


def load_documents(path: str) -> List[Dict]:
    """
    local 파일 로드
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def prepare_text(doc: Dict) -> str:
    """
    파일에서 text 로드
    """
    fields = [
        doc.get("law", ""),
        doc.get("article", ""),
        doc.get("title", ""),
        doc.get("text", ""),
        doc.get("summary", ""),
    ]
    return "\n".join([part.strip() for part in fields if part])


def build_embeddings(documents: List[Dict], model_name: str) -> np.ndarray:
    """
    embedding 생성
    """
    model = SentenceTransformer(model_name)
    texts = [prepare_text(doc) for doc in documents]
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
    return embeddings


def normalize_embeddings(vectors: np.ndarray) -> np.ndarray:
    """
    embedding 일반화
    """
    
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def save_metadata(documents: List[Dict], output_dir: str) -> None:
    """
    메타데이터 저장
    """
    
    metadata = []
    for idx, doc in enumerate(documents):
        metadata.append({
            "id": idx,
            "type": doc.get("type", "법령"),
            "law": doc.get("law"),
            "article": doc.get("article"),
            "title": doc.get("title"),
            "summary": doc.get("summary"),
            "topic": doc.get("topic"),
            "keywords": doc.get("keywords", []),
        })
    with open(os.path.join(output_dir, "law_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def build_faiss_index(embeddings: np.ndarray, output_dir: str) -> None:
    """
    faiss index 생성
    """
    
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    faiss.write_index(index, os.path.join(output_dir, "law_index.faiss"))


def main():
    input_path = os.path.join(os.path.dirname(__file__), law)
    output_dir = os.path.join(os.path.dirname(__file__), dbvector)
    os.makedirs(output_dir, exist_ok=True)

    documents = load_documents(input_path)
    if not documents:
        raise ValueError("law.json을 발견하지 못함")

    embeddings = build_embeddings(documents, model)
    embeddings = normalize_embeddings(embeddings)

    print("Saving FAISS index and metadata...")
    build_faiss_index(embeddings, output_dir)
    save_metadata(documents, output_dir)

    print(f"Index 저장: {os.path.join(output_dir, law_index_faiss)}")
    print(f"Metadata 저장: {os.path.join(output_dir, law_metadata_json)}")


if __name__ == "__main__":
    main()