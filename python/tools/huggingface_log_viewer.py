import requests
import time
from python.helpers.tool import Tool, Response

class HuggingfaceLogViewer(Tool):
    """
    A tool to retrieve build or container logs from a Hugging Face Space.
    """
    async def execute(self, repo_id: str, log_type: str = 'container', token: str = None, retries: int = 3, delay: int = 5, **kwargs) -> Response:
        """
        Retrieves logs from a Hugging Face Space with a retry mechanism.
        """
        endpoint = 'https://huggingface.co'
        url = f'{endpoint}/api/spaces/{repo_id}/logs/{log_type}'

        headers = {'User-Agent': 'AgentZero/1.0'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        for i in range(retries):
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    return Response(message=response.text, break_loop=False)
                elif response.status_code == 404:
                    if log_type == 'container':
                        # For container logs, a 404 might mean the container is not running yet.
                        # We'll retry after a delay.
                        time.sleep(delay)
                        continue
                    else:
                        return Response(message=f'Error: Repository or logs not found (404). URL: {url}', break_loop=True)
                elif response.status_code == 401:
                    return Response(message=f'Error: Unauthorized access. Token may be invalid or have insufficient permissions (401).', break_loop=True)
                elif response.status_code == 403:
                    return Response(message=f'Error: Access forbidden. Authentication may be required (403).', break_loop=True)
                else:
                    return Response(message=f'Error: {response.status_code} - {response.text}', break_loop=True)
            except requests.exceptions.RequestException as e:
                return Response(message=f'Exception: {str(e)}', break_loop=True)

        return Response(message=f'Error: Failed to retrieve logs after {retries} retries.', break_loop=True)
