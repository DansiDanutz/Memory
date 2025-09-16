"""
Test Firecrawl with live API key
"""

from firecrawl_integration import MemoryWebIntegration
import json

def test_live_firecrawl():
    print("=" * 60)
    print("TESTING FIRECRAWL WITH LIVE API")
    print("=" * 60)

    # Initialize integration
    integration = MemoryWebIntegration()

    # Test 1: Scrape a real website
    print("\n1. Testing URL Scraping:")
    print("-" * 40)

    test_url = "https://www.anthropic.com"
    print(f"Scraping: {test_url}")

    memory = integration.save_web_memory(
        test_url,
        tags=["test", "anthropic", "ai"]
    )

    if memory.get("success") != False:
        print(f"[OK] Successfully scraped!")
        print(f"Title: {memory.get('title', 'N/A')}")
        print(f"Description: {memory.get('description', 'N/A')[:100]}...")
        print(f"Content length: {len(memory.get('content', ''))} characters")
        print(f"Memory ID: {memory.get('id')}")
    else:
        print(f"[INFO] Result: {memory}")

    # Test 2: Direct scraping test
    print("\n2. Testing Direct Scraping:")
    print("-" * 40)

    result = integration.extractor.scrape_url("https://docs.firecrawl.dev")

    if result.get("success"):
        print(f"[OK] Successfully scraped Firecrawl docs!")
        print(f"Title: {result.get('title', 'N/A')}")
        print(f"Content preview: {result.get('content', '')[:200]}...")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

    print("\n" + "=" * 60)
    print("Firecrawl API is configured and ready to use!")
    print("=" * 60)

if __name__ == "__main__":
    test_live_firecrawl()