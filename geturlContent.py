import requests
import markdown

# 設定目標網址
url = 'https://r.jina.ai/https://juejin.cn/post/7384347818384867368?utm_source=gold_browser_extension'  # 替換要爬取的 Markdown 格式內容的網址

# 發送請求並獲取網頁內容
response = requests.get(url)

# 確保請求成功
if response.status_code == 200:
    # 獲取內容，假設內容是純文本的 Markdown
    markdown_content = response.text

    # 打印原始 Markdown 內容
    print("原始 Markdown 內容:")
    print(markdown_content)

    # 將 markdown_content 轉換為 HTML
    html_content = markdown.markdown(markdown_content)

    # 打印轉換後的 HTML 內容
    print("\n轉換後的 HTML 內容:")
    print(html_content)
else:
    print("請求失敗，狀態碼:", response.status_code)
