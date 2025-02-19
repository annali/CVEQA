from flask import Flask, render_template, request, jsonify
from langchain_nvidia_ai_endpoints import ChatNVIDIA, NVIDIAEmbeddings
import chromadb
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os

app = Flask(__name__)

# 配置NVIDIA API
os.environ["NVIDIA_API_KEY"] = "your api key"

# 初始化模型和DB
llm = ChatNVIDIA(model="meta/llama3-70b-instruct", temperature=0.7, max_tokens=512)
embedder = NVIDIAEmbeddings(model="NV-Embed-QA")
client = chromadb.PersistentClient("./cve_db")
collection = client.get_collection("cve_2025_jan")


def is_daily_language(text: str) -> bool:
    # 假設用一些關鍵詞來驗證是否為日常用語
    daily_phrases = ["你好", "謝謝", "再見", "今天怎麼樣？", "我很好"]
    return any(phrase in text for phrase in daily_phrases)


def rag_answer(question: str) -> dict:
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
    answer = chain.invoke({"input": question, "context": "\n".join(context)})

    # 根據回答的情況構建 JSON 輸出
    if is_daily_language(answer):
        result_json = {"msg": "hello", "content": ""}
    elif results["documents"]:  # 如果有匹配的結果
        result_json = {"msg": answer, "content": answer}
    else:
        result_json = {"msg": "未找到相關信息", "content": ""}

    # 打印 JSON 輸出
    print(result_json)
    
    return result_json


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.json
    try:
        result = rag_answer(data['question'])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='127.0
