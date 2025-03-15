import os
import time
import random
import signal
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


# User-Agent 池
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
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

def add_delay():
    time.sleep(random.uniform(1, 3))

def download_images(url, save_dir="images"):
    global stop_flag
    try:
        add_delay()
        response = requests.get(url, headers=get_random_headers(url))
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        img_tags = soup.find_all("img")

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        for img_tag in img_tags:
            if stop_flag:
                break
            img_url = img_tag.get("data-src") or img_tag.get("data-original") or img_tag.get("src")
            if img_url:
                img_url = urljoin(url, img_url)
                try:
                    add_delay()
                    # 优先使用srcset中的高分辨率图片
                    srcset = img_tag.get('srcset')
                    if srcset:
                        urls = srcset.split(',')
                        high_res_url = urls[-1].split()[0]
                        img_url = urljoin(url,high_res_url)
                    img_data = requests.get(img_url, headers=get_random_headers(img_url)).content
                    img_name = os.path.basename(img_url)
                    img_path = os.path.join(save_dir, img_name)
                    with open(img_path, "wb") as f:
                        f.write(img_data)
                    print(f"Downloaded: {img_name}")
                except Exception as e:
                    print(f"Failed to download {img_url}: {e}")
        if stop_flag:
            print("爬虫已经停止")
            return

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    target_url = input("请输入要爬取的网页 URL: ")
    save_directory = input("请输入保存图片的目录 (默认为 'images'): ") or "images"
    download_images(target_url, save_directory)