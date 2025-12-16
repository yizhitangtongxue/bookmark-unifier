from processor import Processor
import os

def test_proxy():
    # 设置一个可能无效的代理以验证代码路径是否崩溃，
    # 或者如果你有代理，设置一个真实的代理。
    # 检查默认行为。
    
    print("初始化处理器...")
    processor = Processor()
    
    urls = [
        "https://www.baidu.com", # CN, 应该直连成功
        "https://www.google.com", # 被屏蔽，直连失败，重试用代理 (如果没有代理可能失败)
    ]
    
    print("\n--- 测试 URL ---")
    for url in urls:
        print(f"\n正在检查 {url}...")
        result = processor._check_url(url)
        print(f"结果: {result}")

if __name__ == "__main__":
    test_proxy()
