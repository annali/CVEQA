from flask import Flask, render_template, request, jsonify
from langchain_nvidia_ai_endpoints import ChatNVIDIA, NVIDIAEmbeddings
import chromadb
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os

app = Flask(__name__)

# 配置NVIDIA API
os.environ["NVIDIA_API_KEY"] = "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"

# 初始化模型和DB
llm = ChatNVIDIA(model="meta/llama3-70b-instruct", temperature=0.7, max_tokens=512)
embedder = NVIDIAEmbeddings(model="NV-Embed-QA")
client = chromadb.PersistentClient("./cve_db")
collection = client.get_collection("cve_2025_jan")


def rag_answer(question: str) -> str:
    # 檢索邏輯
    results = collection.query(
        query_texts=[question],
        n_results=5,
        include=["documents", "metadatas"]
    )

    context = [
        f"{doc} (來源: {meta.get('source', '未知')})"
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]

    prompt = ChatPromptTemplate.from_messages([
        ("system", "基於上下文的內容請使用中文答覆，需注明來源:"),
        ("user", "上下文:\n{context}\n\n問題: {input}")
    ])

    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"input": question, "context": "\n".join(context)})


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.json
    try:
        answer = rag_answer(data['question'])
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5100, debug=True)
