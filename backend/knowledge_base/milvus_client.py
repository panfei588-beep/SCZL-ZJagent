"""
Milvus 向量数据库客户端
用于质量案例的存储和相似性检索
"""

from langchain_community.vectorstores import Milvus
from langchain_community.embeddings import DashScopeEmbeddings
from langchain.docstore.document import Document
from core.config import get_settings

settings = get_settings()

_vectorstore = None


def get_vectorstore() -> Milvus:
    global _vectorstore
    if _vectorstore is None:
        embeddings = DashScopeEmbeddings(
            model="text-embedding-v2",
            dashscope_api_key=settings.dashscope_api_key,
        )
        _vectorstore = Milvus(
            embedding_function=embeddings,
            collection_name="quality_cases",
            connection_args={
                "host": settings.milvus_host,
                "port": str(settings.milvus_port),
            },
        )
    return _vectorstore


def search_cases(query: str, top_k: int = 3) -> list[dict]:
    vs = get_vectorstore()
    docs = vs.similarity_search_with_score(query, k=top_k)

    results = []
    for doc, score in docs:
        results.append(
            {
                "case_id": doc.metadata.get("case_id", ""),
                "title": doc.metadata.get("title", ""),
                "problem": doc.metadata.get("problem", ""),
                "root_cause": doc.metadata.get("root_cause", ""),
                "solution": doc.metadata.get("solution", ""),
                "category": doc.metadata.get("category", ""),
                "similarity": round(1 - score, 3),
            }
        )

    return results


def build_knowledge_base(cases: list[dict]) -> int:
    embeddings = DashScopeEmbeddings(
        model="text-embedding-v2",
        dashscope_api_key=settings.dashscope_api_key,
    )

    documents = []
    for case in cases:
        doc = Document(
            page_content=(
                f"{case['title']} {case['problem']} {case['root_cause']} {case['solution']}"
            ),
            metadata={
                "case_id": case["case_id"],
                "title": case["title"],
                "problem": case["problem"],
                "root_cause": case["root_cause"],
                "solution": case["solution"],
                "category": case["category"],
            },
        )
        documents.append(doc)

    global _vectorstore
    _vectorstore = Milvus.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name="quality_cases",
        connection_args={
            "host": settings.milvus_host,
            "port": str(settings.milvus_port),
        },
        drop_old=True,
    )

    return len(documents)
