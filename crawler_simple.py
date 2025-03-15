import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def download_images(url, save_dir="images"):
    """从给定 URL 下载图像，处理相对 URL 和错误。 """
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        img_tags = soup.find_all("img")

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        for img in img_tags:
            img_url = img.get("src")
            if img_url:
                absolute_url = urljoin(url, img_url) # 处理相对 URL
                try:
                    img_data = requests.get(absolute_url, stream=True)
                    img_data.raise_for_status()

                    if 'image' in img_data.headers.get('Content-Type', ''): #验证内容类型
                        filename = os.path.basename(absolute_url)
                        filename = re.sub(r'[^\w\-. ]', '_', filename)
                        filepath = os.path.join(save_dir, filename)

                        with open(filepath, "wb") as f:
                            for chunk in img_data.iter_content(chunk_size=8192):
                                f.write(chunk)
                        print(f"已下载：{filename}")
                    else:
                        print(f"跳过非图像文件：{absolute_url}")

                except requests.exceptions.RequestException as e:
                    print(f"下载 {absolute_url} 失败：{e}")

    except requests.exceptions.RequestException as e:
        print(f"获取 URL 失败：{e}")

download_images("https://www.hippopx.com") # 将其替换为目标网址。