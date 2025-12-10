from processor import Processor
import os

def test_proxy():
    # Set a potentially invalid proxy to verify code path doesn't crash, 
    # or set a real one if you have one.
    # checking default behavior.
    
    print("Initializing Processor...")
    processor = Processor()
    
    urls = [
        "https://www.baidu.com", # CN, should succeed direct
        "https://www.google.com", # Blocked, should fail direct, retry with proxy (might fail if no proxy)
    ]
    
    print("\n--- Testing URLs ---")
    for url in urls:
        print(f"\nChecking {url}...")
        result = processor._check_url(url)
        print(f"Result: {result}")

if __name__ == "__main__":
    test_proxy()
