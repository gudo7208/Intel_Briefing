import sys
import os
import json
import logging

# 使用相对于脚本位置的路径，避免硬编码 Windows 路径
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_PATH = os.path.join(_SCRIPT_DIR, 'src')
if _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)

from sensors.product_hunt import fetch_trending_products

logger = logging.getLogger(__name__)

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logger.info("正在获取 Product Hunt 产品列表...")
    try:
        products = fetch_trending_products(10)

        output_path = os.path.join(os.getcwd(), 'ph_clean_list.md')

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Product Hunt Live List\n\n")
            for i, p in enumerate(products, 1):
                f.write(f"### {i}. {p.name}\n")
                f.write(f"> {p.tagline}\n")
                f.write(f"- Votes: {p.votes_count}\n")
                f.write(f"- URL: {p.url}\n")
                f.write("\n")

        logger.info("写入完成: %s", output_path)

    except Exception as e:
        logger.error("获取失败: %s", e)

if __name__ == "__main__":
    main()
