import requests
import json
from python.helpers.tool import Tool, Response

class SearchHFSpaces(Tool):
    """
    Search for Hugging Face Spaces using the Hugging Face API.
    """

    async def execute(self, search_terms: str = None, limit: int = 20, filter_private: bool = True, sort_by_likes: bool = True, include_tags: list = None, exclude_tags: list = None, **kwargs) -> Response:
        """
        Search for Hugging Face Spaces using the Hugging Face API.

        Args:
            search_terms (str or list): Search term(s) to look for in spaces
            limit (int): Maximum number of results to return
            filter_private (bool): Whether to filter out private spaces
            sort_by_likes (bool): Whether to sort results by number of likes
            include_tags (list): List of tags that must be present in results
            exclude_tags (list): List of tags that must NOT be present in results

        Returns:
            list: List of dictionaries containing space information
        """
        # API endpoint for searching spaces
        url = 'https://huggingface.co/api/spaces'

        # Handle search terms
        if isinstance(search_terms, str):
            search_terms = [search_terms]
        elif search_terms is None:
            search_terms = ['research', 'deep learning', 'ai']

        all_spaces = []

        # Search with each term
        for term in search_terms:
            params = {'search': term, 'limit': limit}
            try:
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    spaces = response.json()
                    all_spaces.extend(spaces)
                else:
                    return Response(message=f"Error searching for '{term}': {response.status_code}", break_loop=False)
            except Exception as e:
                return Response(message=f"Exception searching for '{term}': {str(e)}", break_loop=False)

        # Remove duplicates based on space ID
        unique_spaces = []
        seen_ids = set()
        for space in all_spaces:
            if space['id'] not in seen_ids:
                seen_ids.add(space['id'])
                unique_spaces.append(space)

        # Apply tag filters if specified
        if include_tags:
            filtered_spaces = []
            for space in unique_spaces:
                space_tags = set(space.get('tags', []))
                if all(tag in space_tags for tag in include_tags):
                    filtered_spaces.append(space)
            unique_spaces = filtered_spaces

        if exclude_tags:
            filtered_spaces = []
            for space in unique_spaces:
                space_tags = set(space.get('tags', []))
                if not any(tag in space_tags for tag in exclude_tags):
                    filtered_spaces.append(space)
            unique_spaces = filtered_spaces

        # Filter private spaces if requested
        if filter_private:
            public_spaces = [space for space in unique_spaces if not space.get('private', False)]
            unique_spaces = public_spaces

        # Sort by likes if requested
        if sort_by_likes:
            unique_spaces.sort(key=lambda x: x.get('likes', 0), reverse=True)

        return Response(message=json.dumps(unique_spaces, indent=2), break_loop=False)
