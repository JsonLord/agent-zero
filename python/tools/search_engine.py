import requests
from typing import List, Dict, Any
from python.helpers.tool import Tool, Response

# The base URL of the public SearXNG instance.
# WARNING: Using a public, third-party instance is not recommended for production
# due to significant reliability, security, and privacy risks.
SEARXNG_BASE_URL = "https://CJJ-on-HF-SearXNG.hf.space"

class SearchEngine(Tool):
    """
    A tool to perform web searches using a public SearXNG instance.
    """

    async def execute(self, query: str, category: str = "general", num_results: int = 5) -> Response:
        """
        Performs a web search using a public SearXNG instance and returns formatted results.
        This tool allows for targeted searches using categories defined in the SearXNG instance.

        Args:
            query (str): The search query string.
            category (str): The SearXNG category to search in (e.g., 'science', 'it', 'news').
                            Defaults to 'general' for a broad search.
            num_results (int): The maximum number of search results to return. Defaults to 5.

        Returns:
            Response: A Response object containing the formatted search results or an error message.
        """
        if not query:
            return Response(message="Error: The search query cannot be empty.", break_loop=False)

        # Construct the query with a category prefix if specified.
        # This leverages the power of SearXNG's engine configuration.
        search_query = f"!{category} {query}" if category and category != "general" else query

        params = {
            "q": search_query,
            "format": "json",  # Essential for machine-readable output
            "pageno": 1,
        }

        try:
            response = requests.get(
                f"{SEARXNG_BASE_URL}/search",
                params=params,
                timeout=15  # A generous but necessary timeout for a public service
            )
            # Raise an HTTPError for bad responses (4xx or 5xx)
            response.raise_for_status()

            data = response.json()
            results: List[Dict[str, Any]] = data.get("results", [])

            if not results:
                return Response(message=f"No search results found for the query: '{query}'", break_loop=False)

            # Format the results into a clean, readable string for the agent
            formatted_output = []
            for i, res in enumerate(results[:num_results]):
                title = res.get("title", "No Title Provided")
                url = res.get("url", "No URL Provided")
                snippet = res.get("content") or res.get("description", "No Snippet Provided")
                
                # Sanitize snippet to remove excessive newlines for cleaner LLM input
                clean_snippet = ' '.join(snippet.split()) if snippet else "No Snippet Provided"

                formatted_output.append(
                    f"Result {i+1}:\n"
                    f"  Title: {title}\n"
                    f"  URL: {url}\n"
                    f"  Snippet: {clean_snippet}"
                )
            
            return Response(message="\n---\n".join(formatted_output), break_loop=False)

        except requests.exceptions.Timeout:
            return Response(message="Error: The search request timed out. The SearXNG instance may be offline or overloaded.", break_loop=False)
        except requests.exceptions.RequestException as e:
            return Response(message=f"Error: A network error occurred while contacting the search service: {e}", break_loop=False)
        except ValueError:  # Catches JSON decoding errors
            return Response(message="Error: Failed to parse a valid JSON response from the search service. The service might be down or returning malformed data.", break_loop=False)