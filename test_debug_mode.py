import os
from ai_categorizer import AICategorizer

def test_debug_mode():
    print("Testing Debug Mode (Silence Check)...")
    
    # Enable debug mode
    os.environ["DEBUG"] = "true"
    
    categorizer = AICategorizer()
    
    # Mock bookmark
    bookmark = {
        'url': 'https://example.com',
        'path': ['Root'],
        'title': 'Example'
    }
    
    print("\n--- Running Categorize ---\n")
    categorizer.categorize(bookmark)

if __name__ == "__main__":
    test_debug_mode()
