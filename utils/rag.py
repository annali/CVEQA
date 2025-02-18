from langchain_nvidia_ai_endpoints import ChatNVIDIA, NVIDIAEmbeddings
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from typing import Dict
import os


class RAGHandler:
    def __init__(self):
        # 初始化模型
        self.llm = ChatNVIDIA(
            model="meta/llama3-70b-instruct",
            temperature=0.5,
            max_tokens=512
        )
        self.embedder = NVIDIAEmbeddings(model="NV-Embed-QA")

        # 连接 ChromaDB
        self.client = chromadb.PersistentClient(path="./cve_db")
        self.collection = self.client.get_collection(
            "cve_2025_jan",
            embedding_function=self.embedder
        )

    async def get_answer(self, question: str) -> Dict:
        """异步处理问答逻辑"""
        # 检索上下文
        results = self.collection.query(
            query_texts=[question],
            n_results=5,
            where={"source": "internal_db"},
            include=["documents", "metadatas", "distances"]
        )

        # 空结果处理
        if not results["ids"] or results["distances"][0][0] < 0.75:
            return {
                "answer": "查無此資料",
                "sources": [],
                "confidence": 0.0
            }

        # 构建可信上下文
        context = []
        sources = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            source = meta.get("source", "未知來源")
            context.append(f"{doc} (來源: {source})")
            sources.append(source)

        # 生成回答
        prompt = ChatPromptTemplate.from_messages([
            ("system", "嚴格基於以下來自內部資料庫的上下文回答，禁止引用外部知識:"),
            ("user", "可信上下文:\n{context}\n\n問題: {input}")
        ])

        chain = prompt | self.llm | StrOutputParser()
        answer = await chain.ainvoke({
            "input": question,
            "context": "\n".join(context)
        })

        return {
            "answer": answer,
            "sources": list(set(sources)),
            "confidence": float(results["distances"][0][0])  # 使用最高相似度作为置信度
        }