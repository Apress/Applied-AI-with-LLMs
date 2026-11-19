from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.services.vector_store import SearchResult


class RAGService:
    def __init__(self, retrieval_service: RetrievalService, llm_service: LLMService):
        self.retrieval_service = retrieval_service
        self.llm_service = llm_service

    def ask(self, question: str, top_k: int = 5) -> dict[str, str | list[SearchResult]]:
        sources = self.retrieval_service.search(question, top_k=top_k)
        if not sources:
            return {
                "answer": "There is not enough context to answer this question.",
                "sources": [],
            }

        context = "\n\n".join(
            f"Source: {source['filename']} chunk {source['chunk_index']}\n{source['text']}" for source in sources
        )
        prompt = (
            "You are a helpful assistant that answers questions using only the provided context.\n\n"
            "Rules:\n"
            "- Use only the information in the context.\n"
            "- If the answer is not present in the context, say that you do not know.\n"
            "- Do not invent facts.\n"
            "- Mention the sources used.\n\n"
            f"Context:\n{context}\n\n"
            f"Question:\n{question}\n\n"
            "Answer:"
        )
        return {"answer": self.llm_service.generate(prompt), "sources": sources}

