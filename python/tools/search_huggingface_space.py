from gradio_client import Client
from python.helpers.tool import Tool, Response
from typing import List, Literal

class SearchHuggingfaceSpace(Tool):
    """
    A tool to search for Hugging Face Spaces, models, and datasets.
    """
    async def execute(self,
                      repo_types: List[Literal['model', 'dataset', 'space']] = ["model","dataset","space"],
                      sort: Literal['last_modified', 'likes', 'downloads', 'trending_score'] = "likes",
                      sort_method: Literal['ascending order', 'descending order'] = "ascending order",
                      filter_str: str = "",
                      search_str: str = "",
                      author: str = "",
                      tags: str = "",
                      infer: Literal['warm', 'cold', 'frozen', 'all'] = "all",
                      gated: Literal['gated', 'non-gated', 'all'] = "all",
                      appr: List[Literal['auto', 'manual']] = ["auto","manual"],
                      size_categories: List[Literal['n<1K', '1K<n<10K', '10K<n<100K', '100K<n<1M', '1M<n<10M', '10M<n<100M', '100M<n<1B', '1B<n<10B', '10B<n<100B', '100B<n<1T', 'n>1T']] = [],
                      limit: float = 1000,
                      hardware: List[Literal['cpu-basic', 'zero-a10g', 'cpu-upgrade', 't4-small', 'l4x1', 'a10g-large', 'l40sx1', 'a10g-small', 't4-medium', 'cpu-xl', 'a100-large']] = [],
                      stage: List[Literal['RUNNING', 'SLEEPING', 'RUNTIME_ERROR', 'PAUSED', 'BUILD_ERROR', 'CONFIG_ERROR', 'BUILDING', 'APP_STARTING', 'RUNNING_APP_STARTING']] = [],
                      fetch_detail: List[Literal['Space Runtime']] = ["Space Runtime"],
                      show_labels: List[Literal['Type', 'ID', 'Status', 'Gated', 'Likes', 'DLs', 'AllDLs', 'Trending', 'LastMod.', 'Library', 'Pipeline', 'Hardware', 'Stage', 'NFAA']] = ["Type","ID","Status","Gated","Likes","DLs","Trending","LastMod.","Pipeline"],
                      **kwargs) -> Response:
        """
        Searches for Hugging Face resources using the gradio client.
        """
        try:
            client = Client("John6666/testwarm")
            result = client.predict(
                repo_types=repo_types,
                sort=sort,
                sort_method=sort_method,
                filter_str=filter_str,
                search_str=search_str,
                author=author,
                tags=tags,
                infer=infer,
                gated=gated,
                appr=appr,
                size_categories=size_categories,
                limit=limit,
                hardware=hardware,
                stage=stage,
                fetch_detail=fetch_detail,
                show_labels=show_labels,
                api_name="/search"
            )

            # Format the result
            if isinstance(result, tuple) and len(result) > 0:
                result_dict = result[0]
            else:
                result_dict = result

            # The actual data is nested under the 'value' key
            if isinstance(result_dict, dict) and 'value' in result_dict and isinstance(result_dict['value'], dict):
                data_payload = result_dict['value']
            else:
                data_payload = result_dict

            if 'headers' not in data_payload or 'data' not in data_payload:
                return Response(message=f"Unexpected result format from Hugging Face search: {result}", break_loop=True)

            headers = data_payload['headers']
            data = data_payload['data']

            formatted_results = []
            for row in data:
                formatted_row = []
                for i, item in enumerate(row):
                    formatted_row.append(f"{headers[i]}: {item}")
                formatted_results.append("\n".join(formatted_row))

            return Response(message="\n\n---\n\n".join(formatted_results), break_loop=False)

        except Exception as e:
            return Response(message=f"Error searching Hugging Face: {str(e)}", break_loop=True)
