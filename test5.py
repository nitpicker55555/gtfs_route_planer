import requests
import time
import os
from urllib.parse import urlparse

# 定义要下载的链接列表（从你的输入中提取）
urls = [
    "https://www.voanews.com/a/us-defense-officials-china-is-leading-in-hypersonic-weapons/7000160.html",
    "https://www.politico.eu/article/china-leads-research-into-hypersonic-technology-report/",
    "https://www.japantimes.co.jp/news/2022/07/26/national/japan-hypersonic-missiles-china-jaxa/",
    "https://apnews.com/article/technology-seoul-south-korea-north-korea-pyongyang-7d9438c6c58680ea75ffc72ea1589600",
    "https://news.sky.com/story/amp/uk-to-develop-hypersonic-missiles-to-catch-up-with-china-and-russia-by-2030-report-13124768",
    "https://www.indiatoday.in/india-today-insight/story/how-indias-hypersonic-missile-test-puts-china-pakistan-on-notice-2635339-2024-11-18",
    "https://www.ft.com/content/ba0a3cde-719b-4040-93cb-a486e1f843fb",
    "https://www.washingtonpost.com/national-security/2022/10/17/china-hypersonic-missiles-american-technology/",
    "https://www.defensenews.com/global/europe/2021/03/15/where-does-nato-fit-into-the-global-hypersonic-contest/",
    "https://www.geostrategy.org.uk/research/the-hypersonic-threat-to-the-united-kingdom/",
    "https://www.gov.uk/government/news/hypersonic-missiles-travelling-at-the-speed-of-soundtimes-5",
    "https://asiatimes.com/2024/07/china-and-japan-ignite-asian-hypersonic-arms-race/",
    "https://www.csis.org/analysis/what-does-indias-hypersonic-missile-test-mean"
]

# 设置请求头，模拟浏览器访问
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# 创建保存文件的目录
output_dir = "downloaded_html"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# 下载并保存每个网页
for url in urls:
    try:
        # 发送 GET 请求
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # 检查请求是否成功

        # 获取网页内容
        html_content = response.text

        # 从 URL 中提取域名作为文件名的一部分
        domain = urlparse(url).netloc.replace(".", "_")
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{domain}_{timestamp}.html"
        filepath = os.path.join(output_dir, filename)

        # 保存为 HTML 文件
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"成功下载并保存: {url} -> {filepath}")

        # 添加短暂延迟，避免过于频繁的请求
        time.sleep(2)

    except requests.exceptions.RequestException as e:
        print(f"下载失败: {url} - 错误: {e}")

print("所有下载任务完成！")