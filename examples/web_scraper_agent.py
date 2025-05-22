#!/usr/bin/env python3
"""
Web Scraper Agent Template

This agent demonstrates how to scrape websites, extract data,
and handle various web scraping challenges.
"""

import asyncio
import logging
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
import hashlib

from artcafe_agent import ArtCafeAgent


class WebScraperAgent(ArtCafeAgent):
    """
    Agent that performs web scraping tasks.
    
    Features:
    - HTML parsing
    - CSS selector support
    - Link following
    - Rate limiting
    - Caching
    - JavaScript rendering (optional)
    - Data extraction patterns
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(
            agent_id=config["agent_id"],
            tenant_id=config["tenant_id"],
            private_key_path=config["private_key_path"],
            api_endpoint=config.get("api_endpoint", "https://api.artcafe.ai"),
            log_level=config.get("log_level", "INFO")
        )
        
        # Register command handlers
        self.register_command("scrape_url", self.handle_scrape_url)
        self.register_command("scrape_list", self.handle_scrape_list)
        self.register_command("scrape_sitemap", self.handle_scrape_sitemap)
        self.register_command("extract_data", self.handle_extract_data)
        self.register_command("follow_links", self.handle_follow_links)
        self.register_command("get_cache_stats", self.handle_get_cache_stats)
        
        # Initialize configuration
        self.user_agent = config.get("user_agent", "ArtCafe WebScraper/1.0")
        self.timeout = config.get("timeout", 30)
        self.rate_limit = config.get("rate_limit", 1)  # seconds between requests
        self.max_retries = config.get("max_retries", 3)
        self.cache_enabled = config.get("cache_enabled", True)
        self.cache_ttl = config.get("cache_ttl", 3600)  # 1 hour
        
        # Initialize state
        self.cache = {}
        self.last_request_time = {}
        self.stats = {
            "urls_scraped": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0,
            "total_bytes": 0
        }
        
        # Initialize HTTP client
        self.client = httpx.AsyncClient(
            headers={"User-Agent": self.user_agent},
            timeout=self.timeout,
            follow_redirects=True
        )
        
        self.logger.info(f"Web Scraper Agent initialized: {config['agent_id']}")
    
    async def handle_scrape_url(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scrape a single URL.
        
        Args:
            args: Command arguments containing:
                - url: URL to scrape
                - selectors: CSS selectors to extract (optional)
                - patterns: Regex patterns to extract (optional)
                - follow_links: Whether to extract links (optional)
                - use_cache: Whether to use cache (optional)
        """
        url = args.get("url")
        selectors = args.get("selectors", {})
        patterns = args.get("patterns", {})
        follow_links = args.get("follow_links", False)
        use_cache = args.get("use_cache", self.cache_enabled)
        
        if not url:
            return {
                "status": "error",
                "error": "URL is required"
            }
        
        try:
            # Get page content
            content = await self._fetch_url(url, use_cache)
            
            if not content:
                return {
                    "status": "error",
                    "error": "Failed to fetch content"
                }
            
            # Parse HTML
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract data using selectors
            extracted_data = {}
            for name, selector in selectors.items():
                elements = soup.select(selector)
                if elements:
                    if len(elements) == 1:
                        extracted_data[name] = self._extract_text(elements[0])
                    else:
                        extracted_data[name] = [
                            self._extract_text(elem) for elem in elements
                        ]
            
            # Extract data using patterns
            for name, pattern in patterns.items():
                matches = re.findall(pattern, content)
                if matches:
                    extracted_data[name] = matches[0] if len(matches) == 1 else matches
            
            # Extract links if requested
            links = []
            if follow_links:
                for link in soup.find_all('a', href=True):
                    absolute_url = urljoin(url, link['href'])
                    links.append({
                        "url": absolute_url,
                        "text": link.get_text(strip=True),
                        "title": link.get('title', '')
                    })
            
            # Update stats
            self.stats["urls_scraped"] += 1
            
            return {
                "status": "success",
                "url": url,
                "title": soup.title.string if soup.title else None,
                "data": extracted_data,
                "links": links if follow_links else None,
                "content_length": len(content),
                "scraped_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            self.logger.error(f"Error scraping {url}: {e}")
            self.stats["errors"] += 1
            
            return {
                "status": "error",
                "url": url,
                "error": str(e)
            }
    
    async def handle_scrape_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scrape a list of URLs.
        
        Args:
            args: Command arguments containing:
                - urls: List of URLs to scrape
                - selectors: CSS selectors to extract
                - batch_size: Number of concurrent requests (optional)
        """
        urls = args.get("urls", [])
        selectors = args.get("selectors", {})
        batch_size = args.get("batch_size", 5)
        
        if not urls:
            return {
                "status": "error",
                "error": "URLs list is required"
            }
        
        results = []
        errors = []
        
        # Process URLs in batches
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            
            # Scrape batch concurrently
            tasks = []
            for url in batch:
                task = asyncio.create_task(
                    self.handle_scrape_url({
                        "url": url,
                        "selectors": selectors
                    })
                )
                tasks.append(task)
            
            # Wait for batch to complete
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    errors.append({
                        "url": batch[j],
                        "error": str(result)
                    })
                elif result.get("status") == "error":
                    errors.append({
                        "url": batch[j],
                        "error": result.get("error")
                    })
                else:
                    results.append(result)
            
            # Respect rate limit between batches
            if i + batch_size < len(urls):
                await asyncio.sleep(self.rate_limit)
        
        return {
            "status": "success" if not errors else "partial",
            "scraped": len(results),
            "errors": len(errors),
            "results": results,
            "error_details": errors if errors else None
        }
    
    async def handle_scrape_sitemap(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scrape URLs from a sitemap.
        
        Args:
            args: Command arguments containing:
                - sitemap_url: URL of the sitemap
                - filter_pattern: Regex pattern to filter URLs (optional)
                - max_urls: Maximum number of URLs to scrape (optional)
        """
        sitemap_url = args.get("sitemap_url")
        filter_pattern = args.get("filter_pattern")
        max_urls = args.get("max_urls", 100)
        
        if not sitemap_url:
            return {
                "status": "error",
                "error": "Sitemap URL is required"
            }
        
        try:
            # Fetch sitemap
            content = await self._fetch_url(sitemap_url, use_cache=False)
            
            # Parse sitemap
            soup = BeautifulSoup(content, 'xml')
            urls = []
            
            for loc in soup.find_all('loc'):
                url = loc.get_text()
                
                # Apply filter if specified
                if filter_pattern:
                    if not re.search(filter_pattern, url):
                        continue
                
                urls.append(url)
                
                if len(urls) >= max_urls:
                    break
            
            # Scrape the URLs
            result = await self.handle_scrape_list({
                "urls": urls,
                "selectors": args.get("selectors", {})
            })
            
            return {
                "status": "success",
                "sitemap_url": sitemap_url,
                "urls_found": len(urls),
                "scrape_result": result
            }
        
        except Exception as e:
            self.logger.error(f"Error processing sitemap {sitemap_url}: {e}")
            
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def handle_extract_data(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured data from HTML content.
        
        Args:
            args: Command arguments containing:
                - html: HTML content to parse
                - schema: Extraction schema defining selectors and types
        """
        html = args.get("html")
        schema = args.get("schema")
        
        if not html or not schema:
            return {
                "status": "error",
                "error": "HTML and schema are required"
            }
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            extracted = {}
            
            for field, config in schema.items():
                selector = config.get("selector")
                field_type = config.get("type", "text")
                multiple = config.get("multiple", False)
                
                if not selector:
                    continue
                
                elements = soup.select(selector)
                
                if not elements:
                    extracted[field] = [] if multiple else None
                    continue
                
                if multiple:
                    values = []
                    for elem in elements:
                        value = self._extract_value(elem, field_type)
                        if value is not None:
                            values.append(value)
                    extracted[field] = values
                else:
                    extracted[field] = self._extract_value(elements[0], field_type)
            
            return {
                "status": "success",
                "data": extracted
            }
        
        except Exception as e:
            self.logger.error(f"Error extracting data: {e}")
            
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def handle_follow_links(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Follow links from a starting URL.
        
        Args:
            args: Command arguments containing:
                - start_url: Starting URL
                - max_depth: Maximum depth to follow (optional)
                - max_pages: Maximum pages to visit (optional)
                - url_pattern: Pattern for URLs to follow (optional)
                - same_domain: Only follow same domain links (optional)
        """
        start_url = args.get("start_url")
        max_depth = args.get("max_depth", 2)
        max_pages = args.get("max_pages", 50)
        url_pattern = args.get("url_pattern")
        same_domain = args.get("same_domain", True)
        
        if not start_url:
            return {
                "status": "error",
                "error": "Start URL is required"
            }
        
        # Initialize crawl state
        visited = set()
        to_visit = [(start_url, 0)]  # (url, depth)
        results = []
        start_domain = urlparse(start_url).netloc
        
        while to_visit and len(visited) < max_pages:
            url, depth = to_visit.pop(0)
            
            if url in visited or depth > max_depth:
                continue
            
            # Scrape the page
            result = await self.handle_scrape_url({
                "url": url,
                "follow_links": True
            })
            
            if result.get("status") == "success":
                visited.add(url)
                results.append(result)
                
                # Extract links to follow
                links = result.get("links", [])
                for link in links:
                    link_url = link["url"]
                    
                    # Apply filters
                    if same_domain:
                        if urlparse(link_url).netloc != start_domain:
                            continue
                    
                    if url_pattern:
                        if not re.search(url_pattern, link_url):
                            continue
                    
                    if link_url not in visited:
                        to_visit.append((link_url, depth + 1))
                
                # Respect rate limit
                await asyncio.sleep(self.rate_limit)
        
        return {
            "status": "success",
            "start_url": start_url,
            "pages_visited": len(visited),
            "results": results
        }
    
    async def handle_get_cache_stats(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get cache statistics."""
        cache_size = len(self.cache)
        cache_bytes = sum(len(v["content"]) for v in self.cache.values())
        
        return {
            "status": "success",
            "cache_enabled": self.cache_enabled,
            "cache_ttl": self.cache_ttl,
            "cache_size": cache_size,
            "cache_bytes": cache_bytes,
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "hit_rate": (
                self.stats["cache_hits"] / 
                (self.stats["cache_hits"] + self.stats["cache_misses"])
                if self.stats["cache_hits"] + self.stats["cache_misses"] > 0
                else 0
            )
        }
    
    async def _fetch_url(self, url: str, use_cache: bool = True) -> Optional[str]:
        """Fetch URL content with caching and rate limiting."""
        # Check cache
        cache_key = hashlib.md5(url.encode()).hexdigest()
        
        if use_cache and cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.utcnow().timestamp() - cached["timestamp"] < self.cache_ttl:
                self.stats["cache_hits"] += 1
                return cached["content"]
        
        # Rate limiting
        domain = urlparse(url).netloc
        if domain in self.last_request_time:
            elapsed = datetime.utcnow().timestamp() - self.last_request_time[domain]
            if elapsed < self.rate_limit:
                await asyncio.sleep(self.rate_limit - elapsed)
        
        # Fetch content
        self.stats["cache_misses"] += 1
        retries = 0
        
        while retries < self.max_retries:
            try:
                response = await self.client.get(url)
                response.raise_for_status()
                
                content = response.text
                self.stats["total_bytes"] += len(content)
                
                # Update cache
                if use_cache:
                    self.cache[cache_key] = {
                        "content": content,
                        "timestamp": datetime.utcnow().timestamp()
                    }
                
                # Update rate limit tracking
                self.last_request_time[domain] = datetime.utcnow().timestamp()
                
                return content
            
            except Exception as e:
                retries += 1
                if retries >= self.max_retries:
                    self.logger.error(f"Failed to fetch {url}: {e}")
                    return None
                
                await asyncio.sleep(2 ** retries)  # Exponential backoff
        
        return None
    
    def _extract_text(self, element) -> str:
        """Extract text from BeautifulSoup element."""
        return element.get_text(strip=True)
    
    def _extract_value(self, element, field_type: str) -> Any:
        """Extract value based on field type."""
        if field_type == "text":
            return self._extract_text(element)
        elif field_type == "href":
            return element.get("href")
        elif field_type == "src":
            return element.get("src")
        elif field_type == "attr":
            return element.attrs
        elif field_type == "html":
            return str(element)
        else:
            return self._extract_text(element)
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup when agent exits."""
        await self.client.aclose()
        await super().__aexit__(exc_type, exc_val, exc_tb)


async def main():
    """Main entry point."""
    # Load configuration
    config = {
        "agent_id": "web-scraper-001",
        "tenant_id": "your-tenant-id",
        "private_key_path": "~/.ssh/artcafe_agent_key",
        "user_agent": "ArtCafe WebScraper/1.0",
        "rate_limit": 1,  # 1 second between requests
        "cache_enabled": True,
        "cache_ttl": 3600
    }
    
    # Try to load from file
    try:
        with open("scraper_config.json") as f:
            config.update(json.load(f))
    except FileNotFoundError:
        print("No config file found, using defaults")
    
    # Create and start agent
    agent = WebScraperAgent(config)
    
    try:
        print(f"Starting Web Scraper Agent: {config['agent_id']}")
        await agent.start()
    except KeyboardInterrupt:
        print("\nShutting down agent...")
        await agent.stop()
    except Exception as e:
        print(f"Agent error: {e}")
        await agent.stop()


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run the agent
    asyncio.run(main())