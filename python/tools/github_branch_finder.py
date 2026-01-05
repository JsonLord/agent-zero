import requests
from python.helpers.tool import Tool, Response
from datetime import datetime

class GitHubBranchFinder(Tool):
    """
    A tool to find branch names on GitHub for repositories.
    """

    async def execute(self, repo_name: str, **kwargs) -> Response:
        """
        Finds branch names on GitHub for a given repository.

        Args:
            repo_name (str): The name of the repository in the format 'owner/repo_name'.
                             Defaults to 'JsonLord/{repo-name}' if no owner is provided.
        """
        if '/' not in repo_name:
            repo_name = f"JsonLord/{repo_name}"

        branches_url = f"https://api.github.com/repos/{repo_name}/branches"

        try:
            response = requests.get(branches_url)
            response.raise_for_status()
            branches = response.json()

            if not branches:
                return Response(message=f"No branches found for repository: {repo_name}", break_loop=False)

            branch_info = []
            for branch in branches:
                branch_name = branch['name']
                commits_url = f"https://api.github.com/repos/{repo_name}/commits?sha={branch_name}&per_page=1"
                commit_response = requests.get(commits_url)
                commit_response.raise_for_status()
                commit_data = commit_response.json()
                if commit_data:
                    commit_date = commit_data[0]['commit']['committer']['date']
                    branch_info.append({
                        'name': branch_name,
                        'last_commit_date': commit_date
                    })

            # Sort branches by the last commit date in descending order
            branch_info.sort(key=lambda x: x['last_commit_date'], reverse=True)

            # Format the output
            output = f"Branches for {repo_name}:\n"
            for i, branch in enumerate(branch_info):
                date = datetime.strptime(branch['last_commit_date'], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S")
                line = f"- {branch['name']} (Last commit: {date})"
                if i == 0:
                    line += " **(Latest)**"
                output += line + "\n"

            return Response(message=output, break_loop=False)

        except requests.exceptions.RequestException as e:
            return Response(message=f"Error fetching branches for {repo_name}: {e}", break_loop=False)
        except Exception as e:
            return Response(message=f"An unexpected error occurred: {e}", break_loop=False)
