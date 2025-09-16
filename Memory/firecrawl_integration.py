"""
Firecrawl MCP Integration for Memory Bot
Web scraping and content extraction for memory storage
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from dotenv import load_dotenv
from firecrawl import FirecrawlApp

load_dotenv()


class FirecrawlMemoryExtractor:
    """Extract and process web content for memory storage"""

    def __init__(self):
        """Initialize Firecrawl client"""
        self.api_key = os.getenv("FIRECRAWL_API_KEY")

        if not self.api_key or self.api_key == "your_firecrawl_api_key_here":
            print("[WARNING] Firecrawl API key not configured in .env")
            print("Get your API key from: https://www.firecrawl.dev/")
            self.client = None
        else:
            try:
                from firecrawl import FirecrawlApp
                self.client = FirecrawlApp(api_key=self.api_key)
                print("[OK] Firecrawl client initialized")
            except Exception as e:
                print(f"[ERROR] Failed to initialize Firecrawl: {e}")
                self.client = None

    def scrape_url(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Scrape a single URL and extract content

        Args:
            url: The URL to scrape
            **kwargs: Additional parameters for Firecrawl

        Returns:
            Dict containing scraped content and metadata
        """
        if not self.client:
            return {"error": "Firecrawl client not initialized. Please configure API key."}

        try:
            # Scrape the URL using the correct method name
            result = self.client.scrape(url)

            # Handle Document object from Firecrawl
            if hasattr(result, 'metadata'):
                metadata = result.metadata
                title = metadata.title if hasattr(metadata, 'title') else "Untitled"
                description = metadata.description if hasattr(metadata, 'description') else ""

                return {
                    "url": url,
                    "title": title,
                    "description": description,
                    "content": result.markdown if hasattr(result, 'markdown') else str(result),
                    "html": result.html if hasattr(result, 'html') else "",
                    "metadata": vars(metadata) if metadata else {},
                    "timestamp": datetime.now().isoformat(),
                    "success": True
                }
            else:
                # Fallback for dictionary response
                return {
                    "url": url,
                    "title": "Scraped Page",
                    "content": str(result),
                    "timestamp": datetime.now().isoformat(),
                    "success": True
                }

        except Exception as e:
            return {
                "url": url,
                "error": str(e),
                "success": False,
                "timestamp": datetime.now().isoformat()
            }

    def crawl_website(self, url: str, max_pages: int = 10) -> List[Dict[str, Any]]:
        """
        Crawl entire website starting from URL

        Args:
            url: Starting URL for crawl
            max_pages: Maximum number of pages to crawl

        Returns:
            List of scraped pages
        """
        if not self.client:
            return [{"error": "Firecrawl client not initialized"}]

        try:
            # Start crawl job
            crawl_result = self.client.crawl(
                url,
                params={
                    'limit': max_pages
                }
            )

            pages = []
            for page in crawl_result:
                pages.append({
                    "url": page.get("url"),
                    "title": page.get("metadata", {}).get("title"),
                    "content": page.get("markdown", ""),
                    "metadata": page.get("metadata", {}),
                    "timestamp": datetime.now().isoformat()
                })

            return pages

        except Exception as e:
            return [{"error": str(e), "url": url}]

    def search_web(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search web and scrape top results

        Args:
            query: Search query
            num_results: Number of results to scrape

        Returns:
            List of scraped search results
        """
        if not self.client:
            return [{"error": "Firecrawl client not initialized"}]

        try:
            # Search using Firecrawl
            search_results = self.client.search(
                query,
                limit=num_results
            )

            results = []
            for result in search_results:
                # Scrape each search result
                scraped = self.scrape_url(result.get("url"))
                scraped["search_title"] = result.get("title")
                scraped["search_description"] = result.get("description")
                results.append(scraped)

            return results

        except Exception as e:
            return [{"error": str(e), "query": query}]

    def extract_structured_data(self, url: str, schema: Dict) -> Dict[str, Any]:
        """
        Extract structured data from URL using schema

        Args:
            url: URL to extract from
            schema: JSON schema for extraction

        Returns:
            Structured data matching schema
        """
        if not self.client:
            return {"error": "Firecrawl client not initialized"}

        try:
            result = self.client.extract(
                urls=[url],
                schema=schema
            )

            return {
                "url": url,
                "extracted_data": result.get("extract", {}),
                "content": result.get("markdown", ""),
                "success": True,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "url": url,
                "error": str(e),
                "success": False
            }


class MemoryWebIntegration:
    """Integrate web content into memory system"""

    def __init__(self):
        """Initialize web integration"""
        self.extractor = FirecrawlMemoryExtractor()

    def save_web_memory(self, url: str, tags: List[str] = None) -> Dict:
        """
        Save web page as memory

        Args:
            url: URL to save
            tags: Optional tags for categorization

        Returns:
            Memory object
        """
        # Scrape the URL
        content = self.extractor.scrape_url(url)

        if not content.get("success"):
            return content

        # Create memory object
        memory = {
            "id": f"web_{datetime.now().timestamp()}",
            "type": "web_content",
            "source": url,
            "title": content.get("title"),
            "description": content.get("description"),
            "content": content.get("content"),
            "tags": tags or [],
            "metadata": {
                "url": url,
                "scraped_at": content.get("timestamp"),
                "domain": url.split('/')[2] if '/' in url else url,
                **content.get("metadata", {})
            },
            "importance": 3,  # Default medium importance
            "created_at": datetime.now().isoformat()
        }

        return memory

    def research_topic(self, topic: str, depth: int = 3) -> List[Dict]:
        """
        Research a topic by searching and scraping multiple sources

        Args:
            topic: Topic to research
            depth: Number of sources to analyze

        Returns:
            List of research memories
        """
        # Search for the topic
        results = self.extractor.search_web(topic, num_results=depth)

        memories = []
        for idx, result in enumerate(results):
            if result.get("success"):
                memory = {
                    "id": f"research_{topic}_{idx}",
                    "type": "research",
                    "topic": topic,
                    "source": result.get("url"),
                    "title": result.get("title"),
                    "content": result.get("content"),
                    "relevance_score": 1.0 - (idx * 0.2),  # Higher score for top results
                    "metadata": result.get("metadata", {}),
                    "timestamp": datetime.now().isoformat()
                }
                memories.append(memory)

        return memories

    def monitor_url(self, url: str, previous_content: str = None) -> Dict:
        """
        Monitor URL for changes

        Args:
            url: URL to monitor
            previous_content: Previous content for comparison

        Returns:
            Change detection result
        """
        current = self.extractor.scrape_url(url)

        if not current.get("success"):
            return current

        if previous_content:
            # Simple change detection
            has_changed = current.get("content") != previous_content

            return {
                "url": url,
                "has_changed": has_changed,
                "current_content": current.get("content"),
                "previous_content": previous_content,
                "timestamp": datetime.now().isoformat()
            }

        return {
            "url": url,
            "content": current.get("content"),
            "initial_scan": True,
            "timestamp": datetime.now().isoformat()
        }


def example_usage():
    """Example usage of Firecrawl integration"""

    print("=" * 60)
    print("FIRECRAWL MEMORY INTEGRATION TEST")
    print("=" * 60)

    # Initialize integration
    integration = MemoryWebIntegration()

    # Test 1: Save a web page as memory
    print("\n1. Testing URL scraping (mock - no API key):")
    print("-" * 40)

    if not integration.extractor.client:
        print("Firecrawl not configured. Example output:")
        mock_memory = {
            "id": "web_1234567890",
            "type": "web_content",
            "source": "https://example.com/article",
            "title": "Example Article",
            "content": "This would contain the scraped content...",
            "tags": ["example", "test"],
            "importance": 3,
            "created_at": datetime.now().isoformat()
        }
        print(json.dumps(mock_memory, indent=2)[:300] + "...")
    else:
        # Real scraping if API key is configured
        memory = integration.save_web_memory(
            "https://docs.anthropic.com/claude/docs",
            tags=["documentation", "claude", "api"]
        )
        print(json.dumps(memory, indent=2)[:500] + "...")

    # Test 2: Research a topic
    print("\n2. Research topic example structure:")
    print("-" * 40)
    mock_research = {
        "topic": "machine learning",
        "sources": 3,
        "memories": [
            {
                "id": "research_ml_0",
                "type": "research",
                "source": "https://example.com/ml-guide",
                "title": "ML Guide",
                "relevance_score": 1.0
            }
        ]
    }
    print(json.dumps(mock_research, indent=2))

    print("\n" + "=" * 60)
    print("To use Firecrawl:")
    print("1. Get API key from https://www.firecrawl.dev/")
    print("2. Add to .env: FIRECRAWL_API_KEY=your_key_here")
    print("3. Use integration.save_web_memory(url) to scrape")
    print("=" * 60)


if __name__ == "__main__":
    example_usage()