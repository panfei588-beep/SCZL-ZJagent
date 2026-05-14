"""
Milvus 向量数据库客户端（双库版）
诊断知识库 (diagnosis_cases) — 用于根因分析检索
改善知识库 (improvement_cases) — 用于改进方案检索
"""

from langchain_community.vectorstores import Milvus
from langchain_community.embeddings import DashScopeEmbeddings
from langchain.docstore.document import Document
from core.config import get_settings

settings = get_settings()

_diagnosis_vectorstore = None
_improvement_vectorstore = None


def _get_embeddings() -> DashScopeEmbeddings:
    return DashScopeEmbeddings(
        model="text-embedding-v2",
        dashscope_api_key=settings.dashscope_api_key,
    )


def _connection_args() -> dict:
    return {
        "host": settings.milvus_host,
        "port": str(settings.milvus_port),
    }


# ---- 诊断知识库 ----

def get_diagnosis_vectorstore() -> Milvus:
    """获取诊断知识库向量存储"""
    global _diagnosis_vectorstore
    if _diagnosis_vectorstore is None:
        _diagnosis_vectorstore = Milvus(
            embedding_function=_get_embeddings(),
            collection_name="diagnosis_cases",
            connection_args=_connection_args(),
        )
    return _diagnosis_vectorstore


def search_diagnosis_cases(query: str, top_k: int = 5) -> list[dict]:
    """检索诊断知识库（异常诊断案例）"""
    try:
        vs = get_diagnosis_vectorstore()
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
    except Exception as e:
        return [{"error": f"诊断知识库检索失败: {str(e)}"}]


# ---- 改善知识库 ----

def get_improvement_vectorstore() -> Milvus:
    """获取改善知识库向量存储"""
    global _improvement_vectorstore
    if _improvement_vectorstore is None:
        _improvement_vectorstore = Milvus(
            embedding_function=_get_embeddings(),
            collection_name="improvement_cases",
            connection_args=_connection_args(),
        )
    return _improvement_vectorstore


def search_improvement_cases(query: str, top_k: int = 5) -> list[dict]:
    """检索改善知识库（质量改善方案）"""
    try:
        vs = get_improvement_vectorstore()
        docs = vs.similarity_search_with_score(query, k=top_k)
        results = []
        for doc, score in docs:
            results.append(
                {
                    "case_id": doc.metadata.get("case_id", ""),
                    "title": doc.metadata.get("title", ""),
                    "problem": doc.metadata.get("problem", ""),
                    "solution": doc.metadata.get("solution", ""),
                    "effect": doc.metadata.get("effect", ""),
                    "category": doc.metadata.get("category", ""),
                    "similarity": round(1 - score, 3),
                }
            )
        return results
    except Exception as e:
        return [{"error": f"改善知识库检索失败: {str(e)}"}]


# ---- 向后兼容 ----

def get_vectorstore() -> Milvus:
    """向后兼容：返回诊断知识库"""
    return get_diagnosis_vectorstore()


def search_cases(query: str, top_k: int = 3) -> list[dict]:
    """向后兼容：搜索诊断知识库"""
    return search_diagnosis_cases(query, top_k)


# ---- 构建知识库 ----

def build_diagnosis_kb(cases: list[dict]) -> int:
    """构建诊断知识库：从案例中提取 title + problem + root_cause"""
    embeddings = _get_embeddings()
    documents = []
    for case in cases:
        doc = Document(
            page_content=f"{case['title']} {case['problem']} {case['root_cause']}",
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

    global _diagnosis_vectorstore
    _diagnosis_vectorstore = Milvus.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name="diagnosis_cases",
        connection_args=_connection_args(),
        drop_old=True,
    )
    return len(documents)


def build_improvement_kb(cases: list[dict]) -> int:
    """构建改善知识库：从案例中提取 title + solution + effect"""
    embeddings = _get_embeddings()
    documents = []
    for case in cases:
        doc = Document(
            page_content=f"{case['title']} 解决方案:{case['solution']} 效果:{case['effect']}",
            metadata={
                "case_id": case["case_id"],
                "title": case["title"],
                "problem": case["problem"],
                "solution": case["solution"],
                "effect": case["effect"],
                "category": case["category"],
            },
        )
        documents.append(doc)

    global _improvement_vectorstore
    _improvement_vectorstore = Milvus.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name="improvement_cases",
        connection_args=_connection_args(),
        drop_old=True,
    )
    return len(documents)


def build_knowledge_base(cases: list[dict]) -> int:
    """向后兼容：同时构建两个知识库"""
    d_count = build_diagnosis_kb(cases)
    i_count = build_improvement_kb(cases)
    return d_count + i_count
