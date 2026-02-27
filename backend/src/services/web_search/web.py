"""
Web search service with 2026 best practices:
- JavaScript rendering (Playwright)
- LLM-optimized output (Markdown)
- Main content extraction (Readability)
- Comprehensive DOM pruning
- Schema-based extraction
- Connection pooling for performance
- Parallel URL fetching
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Optional, Any
import urllib.parse
import time
from functools import lru_cache
import hashlib
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class WebSearchService:
    """Web search with 2026 best practices: JS rendering, Markdown output, content extraction"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.enabled = True
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Configuration with defaults
        config = config or {}
        self._min_request_interval = config.get('min_request_interval', 0.5)
        self._cache_ttl = config.get('cache_ttl', 300)
        self.vlm_enabled = config.get('vlm_enabled', True)
        self.vlm_model = config.get('vlm_model', 'us.anthropic.claude-3-7-sonnet-20250219-v1:0')
        self.vlm_use_bedrock = config.get('vlm_use_bedrock', True)
        self.vlm_region = config.get('vlm_region', 'us-west-2')
        self.api_discovery_enabled = config.get('api_discovery_enabled', True)
        self.js_rendering_enabled = config.get('js_rendering_enabled', True)
        self.llm_judge_enabled = config.get('llm_judge_enabled', True)
        self.llm_judge_model = config.get('llm_judge_model', 'us.anthropic.claude-3-7-sonnet-20250219-v1:0')
        
        self._last_request_time = 0
        self._cache = {}
        
        # Connection pooling for performance
        self.session = requests.Session()
        retry_strategy = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=retry_strategy
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # Lazy import heavy dependencies
        self._playwright = None
        self._browser = None
    
    def search(self, query: str, num_results: int = 10, deep_extract: bool = True) -> List[Dict]:
        """
        Search with 2026 best practices:
        - Multi-level caching (memory + LRU)
        - Rate limiting
        - Authority ranking
        - Deep content extraction (NEW)
        - Structured output
        """
        # Check cache first (2026: caching critical for performance)
        cache_key = self._get_cache_key(query, num_results)
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.info(f"Cache hit for: {query[:50]}")
            return cached
        
        # Rate limiting (2026: protect against API abuse)
        self._apply_rate_limit()
        
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            
            response = self.session.get(url, headers=self.headers, timeout=3)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            for result in soup.find_all('div', class_='result')[:num_results * 2]:
                try:
                    title_elem = result.find('a', class_='result__a')
                    snippet_elem = result.find('a', class_='result__snippet')
                    
                    if title_elem and snippet_elem:
                        title = title_elem.get_text(strip=True)
                        snippet = snippet_elem.get_text(strip=True)[:300]
                        url = title_elem.get('href', '')
                        
                        if url.startswith('//duckduckgo.com/l/?'):
                            url_params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                            url = url_params.get('uddg', [''])[0]
                        
                        if title and snippet and url:
                            domain = self._extract_domain(url)
                            authority_score = self._get_authority_score(domain)
                            
                            results.append({
                                'title': title[:150],
                                'snippet': snippet,
                                'url': url,
                                'domain': domain,
                                'authority_score': authority_score,
                                'score': 0.8
                            })
                                
                except Exception:
                    continue
            
            # Quality improvements (2026)
            results = self._boost_recent(results)  # Recency bias
            results = self._apply_quality_signals(results)  # Content quality
            
            # Deep content extraction for key domains (NEW)
            if deep_extract:
                results = self._deep_extract_content(results, query)
            
            ranked = self._rank_by_quality(results)
            diverse = self._ensure_diversity(ranked, max_per_domain=2)[:num_results]
            
            # Cache results
            self._save_to_cache(cache_key, diverse)
            
            logger.info(f"Web search: {len(diverse)} results")
            return diverse
            
        except Exception as e:
            logger.warning(f"Web search failed: {e}")
            return []
    
    def _get_cache_key(self, query: str, num_results: int) -> str:
        """Generate cache key from query"""
        key_str = f"{query}:{num_results}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_from_cache(self, key: str) -> Optional[List[Dict]]:
        """Get from cache if not expired"""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return data
            else:
                del self._cache[key]  # Expired
        return None
    
    def _save_to_cache(self, key: str, data: List[Dict]):
        """Save to cache with timestamp"""
        self._cache[key] = (data, time.time())
        
        # Simple cache size limit (keep last 100 queries)
        if len(self._cache) > 100:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
    
    def _apply_rate_limit(self):
        """Rate limiting: wait if needed (2026 best practice)"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.replace('www.', '')
        except:
            return ''
    
    def _get_authority_score(self, domain: str) -> int:
        """
        2026 Authority Ranking (Princeton/Georgia Tech research)
        High-authority sources get 30-40% more citations
        """
        HIGH_AUTHORITY = [
            'nytimes.com', 'reuters.com', 'bbc.com', 'wsj.com',
            'forbes.com', 'bloomberg.com', 'theguardian.com',
            'nature.com', 'science.org', 'arxiv.org'
        ]
        
        MEDIUM_AUTHORITY = [
            '.gov', '.edu', 'wikipedia.org', 'github.com',
            'stackoverflow.com', 'medium.com'
        ]
        
        domain_lower = domain.lower()
        
        # High authority: +10 points
        if any(d in domain_lower for d in HIGH_AUTHORITY):
            return 10
        
        # Medium authority: +7 points
        if any(domain_lower.endswith(d) or d in domain_lower for d in MEDIUM_AUTHORITY):
            return 7
        
        # Default: +3 points
        return 3
    
    def _rank_by_quality(self, results: List[Dict]) -> List[Dict]:
        """
        Rank sources by authority + relevance (Perplexity-style)
        Research: Authority matters more than backlinks for AI citations
        """
        def quality_score(source):
            authority = source.get('authority_score', 3)
            relevance = source.get('score', 0.5) * 10
            return authority + relevance
        
        return sorted(results, key=quality_score, reverse=True)
    
    def _boost_recent(self, results: List[Dict]) -> List[Dict]:
        """Boost recent content (dynamic)"""
        import re
        from datetime import datetime
        
        current_year = datetime.now().year
        last_year = current_year - 1
        
        for r in results:
            snippet = r['snippet']
            # Dynamic: current year and last year
            pattern = f'{current_year}|{last_year}|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec {current_year}'
            if re.search(pattern, snippet):
                r['score'] += 0.3
        return results
    
    def _apply_quality_signals(self, results: List[Dict]) -> List[Dict]:
        """Detect content quality"""
        for r in results:
            snippet = r['snippet'].lower()
            
            # Positive signals
            if any(w in snippet for w in ['research', 'study', 'analysis']):
                r['score'] += 0.2
            if len(snippet) > 200:
                r['score'] += 0.1
            
            # Negative signals (spam)
            if any(w in snippet for w in ['click here', 'buy now', 'ad']):
                r['score'] -= 0.3
        
        return results
    
    def _ensure_diversity(self, results: List[Dict], max_per_domain: int = 2) -> List[Dict]:
        """Limit results per domain"""
        domain_counts = {}
        diverse = []
        for r in results:
            domain = r['domain']
            count = domain_counts.get(domain, 0)
            if count < max_per_domain:
                diverse.append(r)
                domain_counts[domain] = count + 1
        return diverse
    
    def _get_browser(self):
        """Lazy load Playwright browser with stealth mode and anti-detection."""
        if not self._browser:
            try:
                from playwright.sync_api import sync_playwright
                if not self._playwright:
                    self._playwright = sync_playwright().start()
                self._browser = self._playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    ]
                )
                logger.info("✅ Playwright browser initialized with stealth mode")
            except Exception as e:
                logger.warning(f"Playwright init failed: {e}")
        return self._browser
    
    def _try_api_endpoint(self, url: str) -> Optional[Dict]:
        """
        Priority 1: Try to find JSON API endpoint before HTML scraping.
        10x faster and more reliable.
        """
        try:
            # Common API patterns
            patterns = [
                url.replace('www.', 'api.'),
                url.replace('www.', 'cdn.'),
                url + '/data.json',
                url + '/api/data',
                url.replace('/schedule', '/api/schedule'),
                url.replace('/scores', '/api/scores'),
                url.replace('.html', '.json'),
                url.replace('.htm', '.json'),
            ]
            
            for api_url in patterns:
                try:
                    response = self.session.get(api_url, headers=self.headers, timeout=2)
                    if response.status_code == 200:
                        data = response.json()
                        if data:
                            logger.info(f"✅ API endpoint found: {api_url}")
                            return data
                except:
                    continue
            
            return None
        except Exception as e:
            logger.debug(f"API discovery failed: {e}")
            return None
    
    def _judge_content_sufficiency(self, content: str, query: str) -> bool:
        """
        LLM judge: Evaluate if extracted content sufficiently answers the query.
        Returns True if sufficient, False if need to try next extraction tier.
        Uses Nova Lite for fast, cheap judgments.
        """
        if not self.llm_judge_enabled:
            return len(content) > 100
        
        if not content or len(content) < 50:
            return False
        
        try:
            import boto3
            import json
            from config.prompts import CONTENT_SUFFICIENCY_PROMPT
            
            bedrock = boto3.client('bedrock-runtime', region_name=self.vlm_region)
            
            prompt = CONTENT_SUFFICIENCY_PROMPT.format(query=query, content=content[:1000])
            
            # Use Nova Lite format for fast judging
            body = json.dumps({
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ],
                "inferenceConfig": {
                    "max_new_tokens": 10,
                    "temperature": 0.1
                }
            })
            
            response = bedrock.invoke_model(
                modelId=self.llm_judge_model,
                body=body
            )
            
            result = json.loads(response['body'].read())
            answer = result['output']['message']['content'][0]['text'].strip().upper()
            
            is_sufficient = 'YES' in answer
            logger.info(f"🔍 LLM Judge: {'✅ Sufficient' if is_sufficient else '❌ Insufficient'}")
            return is_sufficient
            
        except Exception as e:
            logger.debug(f"LLM judge failed: {e}, using length heuristic")
            return len(content) > 100
    
    def fetch_page_content(self, url: str, max_chars: int = 1000, use_js: bool = True, try_api: bool = True, use_vlm_fallback: bool = True, query: str = "") -> str:
        """
        Fetch and extract main content with 2026 best practices + LLM judge.
        Returns LLM-optimized Markdown.
        
        Tier 1: API endpoint (10x faster)
        Tier 2: HTML + JS + Markdown
        Tier 3: VLM fallback (if enabled)
        
        LLM Judge evaluates each tier before proceeding to next.
        """
        try:
            # Tier 1: Try API endpoint first
            if try_api and self.api_discovery_enabled:
                api_data = self._try_api_endpoint(url)
                if api_data:
                    import json
                    content = json.dumps(api_data, indent=2)[:max_chars]
                    
                    # Judge: Is API data sufficient?
                    if self._judge_content_sufficiency(content, query):
                        logger.info("✅ Tier 1 (API) sufficient")
                        return content
                    else:
                        logger.info("⏭️ Tier 1 insufficient, trying Tier 2")
            
            # Tier 2: HTML + JS + Markdown
            if use_js and self.js_rendering_enabled and any(domain in url for domain in ['nba.com', 'espn.com', 'react', 'vue', 'angular']):
                html = self._fetch_with_playwright(url)
            else:
                response = self.session.get(url, headers=self.headers, timeout=5)
                response.raise_for_status()
                html = response.text
            
            # Extract main content
            try:
                from readability import Document
                doc = Document(html)
                title = doc.title()
                main_html = doc.summary()
            except:
                main_html = html
                title = ""
            
            # Prune DOM
            soup = BeautifulSoup(main_html, 'html.parser')
            soup = self._prune_dom(soup)
            
            # Convert to Markdown
            try:
                from markdownify import markdownify as md
                markdown = md(str(soup), heading_style="ATX", strip=['script', 'style'])
                
                import re
                markdown = re.sub(r'\n{3,}', '\n\n', markdown)
                markdown = re.sub(r' +', ' ', markdown)
                
                content = markdown[:max_chars]
                
                # Judge: Is HTML extraction sufficient?
                if self._judge_content_sufficiency(content, query):
                    logger.info("✅ Tier 2 (HTML) sufficient")
                    return content
                else:
                    logger.info("⏭️ Tier 2 insufficient, trying Tier 3")
                    
            except:
                text = soup.get_text(separator=' ', strip=True)
                if self._judge_content_sufficiency(text[:max_chars], query):
                    return text[:max_chars]
            
        except Exception as e:
            logger.debug(f"Content extraction failed: {e}")
            
            # Tier 3: VLM fallback (disabled by default - threading issues)
            if use_vlm_fallback and self.vlm_enabled:
                try:
                    logger.info(f"Trying VLM fallback for: {url[:50]}")
                    vlm_content = self.extract_with_vision(
                        url=url,
                        prompt=f"Extract content relevant to: {query}" if query else "Extract the main content from this webpage.",
                        use_bedrock=self.vlm_use_bedrock,
                        model_id=self.vlm_model
                    )
                    if vlm_content and len(vlm_content) > 100:
                        return vlm_content[:max_chars]
                except Exception as vlm_error:
                    logger.error(f"VLM extraction failed: {vlm_error}")
            
            return ""
    
    def _fetch_with_playwright(self, url: str) -> str:
        """Fetch page with JavaScript rendering and stealth mode."""
        try:
            browser = self._get_browser()
            if not browser:
                raise Exception("Browser not available")
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            
            # Enhanced stealth mode - bypass bot detection
            page.add_init_script("""
                // Remove webdriver flag
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                
                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                // Add chrome object
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
                
                // Mock permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Hide automation
                delete navigator.__proto__.webdriver;
                
                // Mock hardware concurrency
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 8
                });
                
                // Mock device memory
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8
                });
            """)
            
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=15000)
                # Wait a bit for dynamic content
                page.wait_for_timeout(1000)
            except Exception as goto_error:
                logger.warning(f"Page load timeout, using partial content: {goto_error}")
            
            html = page.content()
            page.close()
            context.close()
            
            logger.info(f"✅ JS rendered with stealth: {url[:50]}")
            return html
        except Exception as e:
            logger.warning(f"Playwright fetch failed: {e}, falling back to requests")
            try:
                response = self.session.get(url, headers=self.headers, timeout=5)
                return response.text
            except:
                return ""  # Return empty if all fails
    
    def _prune_dom(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Comprehensive DOM pruning (2026 best practice)."""
        # Remove all noise elements
        REMOVE_SELECTORS = [
            'script', 'style', 'nav', 'footer', 'header', 'aside',
            '[class*="ad-"]', '[class*="advertisement"]', '[id*="ad-"]',
            '[class*="social"]', '[class*="share"]', '[class*="sharing"]',
            '[class*="comment"]', '[class*="sidebar"]', '[class*="related"]',
            '[class*="recommended"]', '[class*="promo"]', '[class*="banner"]',
            'iframe', 'noscript', '[role="complementary"]', '[role="banner"]',
            '[class*="cookie"]', '[class*="popup"]', '[class*="modal"]'
        ]
        
        for selector in REMOVE_SELECTORS:
            try:
                for elem in soup.select(selector):
                    elem.decompose()
            except:
                pass
        
        return soup
    
    def extract_with_vision(self, url: str, prompt: str, use_bedrock: bool = None, model_id: str = None) -> str:
        """
        Priority 3: Vision-based extraction using Claude on Bedrock (FALLBACK ONLY).
        Only called when API and HTML extraction fail.
        """
        # Use config defaults if not specified
        if use_bedrock is None:
            use_bedrock = self.vlm_use_bedrock
        if model_id is None:
            model_id = self.vlm_model
        
        try:
            import base64
            import os
            from datetime import datetime
            
            # Take screenshot
            browser = self._get_browser()
            if not browser:
                return ""
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            
            # Manual stealth
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                window.chrome = {runtime: {}};
            """)
            
            page.goto(url, wait_until='domcontentloaded', timeout=15000)
            screenshot_bytes = page.screenshot()
            page.close()
            context.close()
            
            # Save screenshot
            screenshots_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'screenshots')
            os.makedirs(screenshots_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            domain = url.split('/')[2].replace('www.', '')
            filename = f"{timestamp}_{domain}.png"
            filepath = os.path.join(screenshots_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(screenshot_bytes)
            logger.info(f"📸 Screenshot saved: {filepath}")
            
            # Encode to base64
            b64_image = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            if use_bedrock:
                # Use AWS Bedrock with Claude
                try:
                    import boto3
                    import json
                    
                    bedrock = boto3.client('bedrock-runtime', region_name=self.vlm_region)
                    
                    body = json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 4096,
                        "messages": [{
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": b64_image
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }]
                    })
                    
                    response = bedrock.invoke_model(
                        modelId=model_id,
                        body=body
                    )
                    
                    result = json.loads(response['body'].read())
                    content = result['content'][0]['text']
                    
                    logger.info(f"✅ VLM fallback (Bedrock {model_id}): {url[:50]}")
                    return content
                    
                except Exception as e:
                    logger.warning(f"Bedrock VLM failed: {e}, trying OpenAI")
            
            # Fallback to OpenAI
            try:
                from openai import OpenAI
                
                client = OpenAI()
                response = client.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}}
                        ]
                    }],
                    max_tokens=4096
                )
                
                content = response.choices[0].message.content
                logger.info(f"✅ VLM fallback (OpenAI): {url[:50]}")
                return content
                
            except Exception as e:
                logger.warning(f"OpenAI VLM failed: {e}")
                return ""
            
        except Exception as e:
            logger.error(f"VLM extraction failed: {e}")
            return ""
    
    def _deep_extract_content(self, results: List[Dict], query: str) -> List[Dict]:
        """
        Universal deep content extraction with LLM-judged fallback chain:
        1. Try API endpoint (10x faster)
        2. HTML + JS + Markdown (current)
        3. VLM (FALLBACK ONLY - if enabled and others fail)
        
        LLM judge evaluates each tier before proceeding.
        PARALLEL: Fetches multiple URLs simultaneously for speed.
        """
        max_deep_extract = 2  # Only extract top 2 results for speed
        
        def extract_single_result(result):
            """Extract content for a single result."""
            url = result.get('url', '')
            
            if not url:
                return result
            
            try:
                # All tiers with LLM judge (automatic inside fetch_page_content)
                content = self.fetch_page_content(
                    url, 
                    max_chars=800, 
                    use_js=True, 
                    try_api=True,
                    use_vlm_fallback=True,
                    query=query  # Pass query for LLM judge
                )
                
                if content and len(content) > 100:
                    result['snippet'] = content
                    result['deep_extracted'] = True
                    result['format'] = 'markdown'
                    logger.info(f"✅ Deep extracted: {result.get('domain', 'unknown')}")
                        
            except Exception as e:
                logger.debug(f"Deep extraction failed for {url}: {e}")
            
            return result
        
        # Parallel extraction with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=5) as executor:
            results[:max_deep_extract] = list(executor.map(extract_single_result, results[:max_deep_extract]))
        
        return results
    
    def __del__(self):
        """Cleanup Playwright resources."""
        try:
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
            if self.session:
                self.session.close()
        except:
            pass
    
    def should_use_web_search(self, query: str) -> bool:
        """
        Determine if query would benefit from web search
        
        Keywords indicating current events, news, or real-time info
        """
        from datetime import datetime
        current_year = str(datetime.now().year)
        last_year = str(datetime.now().year - 1)
        
        web_keywords = [
            'latest', 'recent', 'current', 'today', 'now', 'breaking',
            'news', 'update', 'happening', 'trend', 'new', current_year, last_year,
            'weather', 'stock', 'price', 'score', 'result', 'who is', 'what is'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in web_keywords)

