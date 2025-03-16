import os
import re
import time
import random
import signal
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


# User-Agent 池
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
    # 以下可以添加更多 User-Agent
]

# 代理 IP 列表 (请替换为你的代理 IP)
PROXY_LIST = [
    {"http": "http://39.101.65.228:111", "https": "http://47.119.20.8:9098"},
    # 可以添加更多代理 IP，以下推荐两个提供免费代理的网站
       # http://www.ip3366.net/free/
       # https://www.kuaidaili.com/free/
    # 注意，免费代理的质量并不高，经过我测试，有时不会生效，所以下面提供了代理的验证以及跳过程序，没错就是这么严谨
]

# 停止标志
stop_flag = False

# 信号处理函数
def signal_handler(sig, frame):
    global stop_flag
    print("收到停止信号，爬虫即将停止...")
    stop_flag = True

# 注册信号处理函数
signal.signal(signal.SIGINT, signal_handler)

def get_random_headers(url):
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": url,
    }
    return headers

def get_random_proxy():
    if PROXY_LIST:  # 检查代理 IP 列表是否为空
        return random.choice(PROXY_LIST)
    else:
        return None  # 如果没有代理 IP，返回 None

def add_delay():
    time.sleep(random.uniform(1, 3))

def sanitize_filename(filename):
    """清理文件名，移除非法字符"""
    return re.sub(r'[\\/:*?"<>|]', "", filename)

def get_filename_from_url(url, content_type):
    """从 URL 和 Content-Type 获取文件名"""
    parsed_url = urlparse(url)
    path = parsed_url.path
    filename = os.path.basename(path)
    if not filename:
        filename = "unknown"
    if "." not in filename:
        ext = content_type.split("/")[-1]
        if ext:
            filename += "." + ext
    return sanitize_filename(filename)

def validate_proxy(proxy):
    """验证代理 IP 的可用性"""
    if not proxy:
        return True  # 如果没有代理，则认为可用
    try:
        requests.get("https://www.hippopx.com", proxies=proxy, timeout=5)  # 尝试连接一个常用网站
        return True  # 代理可用
    except Exception:
        return False  # 代理不可用

def download_resource(url, save_dir, headers, proxies):
    """下载资源，如果代理 IP 不可用，则不使用代理"""
    try:
        add_delay()
        if proxies and validate_proxy(proxies):  # 如果有代理 IP 且可用，则使用代理
            response = requests.get(url, headers=headers, proxies=proxies, stream=True, timeout=10) #添加超时时间
        else:  # 如果没有代理 IP 或代理 IP 不可用，则不使用代理
            response = requests.get(url, headers=headers, stream=True, timeout=10) #添加超时时间
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        filename = get_filename_from_url(url, content_type)
        file_path = os.path.join(save_dir, filename)

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"Downloaded: {filename}")
        return filename, content_type
    except requests.exceptions.RequestException as e:
        print(f"Failed to download {url}: {e}")
        return None, None

def extract_text(soup):
    """提取网页文本"""
    for script in soup(["script", "style"]):
        script.decompose()
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return "\n".join(chunk for chunk in chunks if chunk)

def crawl_resources(url, resource_types, save_dir="downloads"):
    """爬取资源"""
    global stop_flag
    try:
        add_delay()
        proxy = get_random_proxy()
        headers = get_random_headers(url)
        if proxy and validate_proxy(proxy):  # 如果有代理 IP 且可用，则使用代理
            response = requests.get(url, headers=headers, proxies=proxy, timeout=10) #添加超时时间
        else:  # 如果没有代理 IP 或代理 IP 不可用，则不使用代理
            response = requests.get(url, headers=headers, timeout=10) #添加超时时间
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        downloaded_data = []

        if "image" in resource_types:
            img_tags = soup.find_all("img")
            # 在下载图片之前，创建 "images" 子目录
            os.makedirs(os.path.join(save_dir, "images"), exist_ok=True)
            for img_tag in img_tags:
                if stop_flag:
                    break
                img_url = img_tag.get("data-src") or img_tag.get("data-original") or img_tag.get("src")
                if img_url:
                    img_url = urljoin(url, img_url)
                    filename, content_type = download_resource(img_url, os.path.join(save_dir, "images"), headers, proxy)
                    if filename:
                        downloaded_data.append({"type": "image", "filename": filename, "url": img_url, "content_type": content_type})

        if "text" in resource_types:
            text = extract_text(soup)
            if text:
                filename = sanitize_filename(urlparse(url).netloc) + ".txt"
                file_path = os.path.join(save_dir, "text", filename)
                os.makedirs(os.path.join(save_dir, "text"), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"Downloaded text: {filename}")
                downloaded_data.append({"type": "text", "filename": filename, "url": url, "content_type": "text/plain"})

        if downloaded_data:
            df = pd.DataFrame(downloaded_data)
            print(df)  # 打印下载信息
            df.to_csv(os.path.join(save_dir, "downloaded_resources.csv"), index=False) #保存信息到csv
        if stop_flag:
            print("爬虫已经停止")
            return

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    target_url = input("请输入要爬取的网页 URL: ")
    resource_types = input("请输入要爬取的资源类型 (image, text, 多个类型用逗号分隔): ").split(",")
    resource_types = [r.strip().lower() for r in resource_types] #清理用户的输入
    save_directory = input("请输入保存资源的目录 (默认为 'downloads'): ") or "downloads"
    crawl_resources(target_url, resource_types, save_directory)