Space Repository Log Retrieval Template
API Endpoint Structure
{endpoint}/api/spaces/{repo_id}/logs/{target}
Parameter Replacement Guide:
Parameter	Description	Example Values	Where to Replace
{endpoint}	Base API endpoint	https://huggingface.co	Replace in all requests
{repo_id}	Repository identifier	harvesthealth/magneticui	Replace with your target repository
{target}	Log type to retrieve	build or container	Replace based on log type needed
{token}	Authentication token	<YOUR_HF_TOKEN>	Replace with your valid token
Python Code Template
import requests

def get_space_logs(repo_id, target='container', token=None):
    # Replace {endpoint} with actual endpoint URL
    endpoint = 'https://huggingface.co'
    url = f'{endpoint}/api/spaces/{repo_id}/logs/{target}'

    # Add authentication if token is provided
    headers = {'User-Agent': 'AgentZero/1.0'}
    if token:
        # Replace {token} with actual token value
        headers['Authorization'] = f'Bearer {token}'

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.text
        elif response.status_code == 404:
            return f'Error: Repository or logs not found (404). URL: {url}'
        elif response.status_code == 401:
            return f'Error: Unauthorized access. Token may be invalid or insufficient permissions (401).'
        elif response.status_code == 403:
            return f'Error: Access forbidden. Authentication may be required (403).'
        else:
            return f'Error: {response.status_code} - {response.text}'
    except Exception as e:
        return f'Exception: {str(e)}'
Usage Examples
Example 1: Retrieving Build Logs
# Replace {repo_id} with actual repository ID
# Replace {token} with actual token
logs = get_space_logs(
    repo_id='harvesthealth/magneticui',  # ← REPLACE THIS
    target='build',  # ← SET TO 'build' FOR BUILD LOGS
    token='<YOUR_HF_TOKEN>'  # ← REPLACE THIS
)
print(logs)
Example 2: Retrieving Container Logs
# Replace {repo_id} with actual repository ID
# Replace {token} with actual token
logs = get_space_logs(
    repo_id='harvesthealth/magneticui',  # ← REPLACE THIS
    target='container',  # ← SET TO 'container' FOR CONTAINER LOGS
    token='<YOUR_HF_TOKEN>'  # ← REPLACE THIS
)
print(logs)
Key Differences Between Build and Container Logs
Aspect	Build Logs	Container Logs
Purpose	Shows build process and dependency installation	Shows runtime application logs
Availability	Available after each build	Only available when container is running
Access Pattern	Consistently accessible with proper auth	May return 404 if container not running
Typical Use	Debugging build issues, dependency problems	Monitoring application performance, runtime errors
Troubleshooting Guide
Common Issues and Solutions:
404 Not Found Error:

For build logs: Verify repository ID and ensure build exists
For container logs: The container may not be running (common cause)
Solution: Check if the space is active and try again
401 Unauthorized Error:

Token is missing or invalid
Solution: Verify token validity and permissions
403 Forbidden Error:

Token lacks sufficient permissions
Solution: Use a token with appropriate access rights
Best Practices
Always validate parameters before making requests
Start with build logs as they're more consistently available
Use descriptive variable names to avoid confusion
Implement retry logic for transient failures in production
Store tokens securely and never hardcode in production code