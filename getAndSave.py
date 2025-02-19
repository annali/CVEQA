import requests
import chromadb

# 定義取得CVE數據
def fetch_cves(start_date, end_date):
    url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    params = {
        'pubStartDate': f"{start_date}T00:00:00.000",
        'pubEndDate': f"{end_date}T23:59:59.999",
        'resultsPerPage': 2000
    }

    try:
        response = requests.get(url, params=params)
        if response.status_code!= 200:
            raise Exception(f"API請求失敗: {response.status_code}")

        cve_data = response.json()
        print(f"取得{cve_data['totalResults']}筆CVE記錄")
        return parse_cves(cve_data)

    except Exception as e:
        print(f"數據取得有誤: {str(e)}")
        return []

# 解析CVE數據
def parse_cves(cve_data):
    parsed = []
    for item in cve_data['vulnerabilities']:
        cve = item['cve']
        metrics = cve.get('metrics', {})

        # 處理cvss_score空值
        cvss_v31 = metrics.get('cvssMetricV31', [{}])[0].get('cvssData', {})
        cvss_v30 = metrics.get('cvssMetricV30', [{}])[0].get('cvssData', {})
        base_score = cvss_v31.get('baseScore') or cvss_v30.get('baseScore') or 0.0  # 空值設定為0.0

        # 處理severity空值
        severity = cvss_v31.get('baseSeverity') or cvss_v30.get('baseSeverity') or "UNKNOWN"

        parsed.append({
            "id": cve['id'],
            "description": cve['descriptions'][0]['value'],
            "published": cve['published'],
            "cvss_score": base_score,  # 確保數值類型
            "severity": severity.upper()  # 確保字符類型
        })
    return parsed

# 將CVE數據存到Chromadb
def store_to_chroma(cve_list):
    # client = chromadb.PersistentClient(
    #     path="./cve_db",
    #     settings=settings,
    #     tenant="default",
    #     database="default"
    # )

    client = chromadb.PersistentClient(
        path="./cve_db"
    )

    collection = client.get_or_create_collection(
        name="cve_2025_jan",
        metadata={"hnsw:space": "cosine"}
    )

    # 批量數據
    documents = [cve["description"] for cve in cve_list]
    metadatas = [{
        "published": cve["published"],
        "cvss": cve["cvss_score"],
        "severity": cve["severity"]
    } for cve in cve_list]
    ids = [cve["id"] for cve in cve_list]

    # 批量插入
    collection.upsert(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

    print(f"成功存入{len(ids)}筆記錄")

    # metadata過濾邏輯
    valid_metadatas = []
    valid_ids = []
    valid_documents = []

    for idx, metadata in enumerate(metadatas):
        # 過濾None和非法類型
        clean_metadata = {
            k: v if isinstance(v, (str, int, float, bool)) else str(v)
            for k, v in metadata.items()
            if v is not None
        }

        if len(clean_metadata) == len(metadata):
            valid_metadatas.append(clean_metadata)
            valid_ids.append(ids[idx])
            valid_documents.append(documents[idx])
        else:
            print(f"過濾異常metadata數據: {metadata}")

    # 使用過濾後的數據
    collection.upsert(
        documents=valid_documents,
        metadatas=valid_metadatas,
        ids=valid_ids
    )

if __name__ == "__main__":
    # 取得數據
    cves = fetch_cves("2025-02-01", "2025-02-01")

    # 儲存數據
    if cves:
        store_to_chroma(cves)

        # 驗證儲存結果
        client = chromadb.PersistentClient("./cve_db")
        collection = client.get_collection("cve_2025_jan")
        print(f"當前集合記錄筆數: {collection.count()}")
