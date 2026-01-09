from python.helpers.tool import Tool, Response
import json
import os
import subprocess
import asyncio
import shutil
import re

# Global dictionary to hold monitoring tasks, keyed by context ID
_monitoring_tasks = {}

def sanitize_branch_name(name):
    # Sanitize the branch name to be compliant with Git's naming conventions
    name = name.lower()
    name = re.sub(r'\s+', '-', name)
    name = re.sub(r'[^a-z0-9-_/]', '', name)
    # Get the first 5 words
    words = name.split('-')
    return '-'.join(words[:5])


class DeveloperOrchestrator(Tool):
    """
    Orchestrates the entire development workflow through a state machine,
    from ideation to completion, waiting for user feedback at key stages.
    """

    async def _monitor_jules_session(self, session_id: str, agent: "Agent"):
        """
        A background task to monitor a Jules session.
        """
        while True:
            await asyncio.sleep(900) # Wait for 15 minutes

            try:
                jules_agent = agent.get_tool(name="jules_api", method=None, args={}, message="", loop_data=None)
                response = await jules_agent.execute(command="list_activities", session_id=session_id)

                activities_data = json.loads(response.message)
                activities = activities_data.get("activities", [])

                is_complete = any(activity.get("state") == "DONE" for activity in activities)
                if is_complete:
                    agent.context.log.log(type="info", heading="Jules Task Complete", content=f"Jules session {session_id} has completed successfully.")
                    break

                # Check for questions from Jules
                for activity in reversed(activities): # Check newest first
                    if activity.get("message") and activity.get("message", {}).get("author") == "JULES":
                        question = activity.get("message", {}).get("content")
                        if question:
                            # Formulate an answer using the utility model
                            answer = await agent.call_utility_model(
                                system="You are an expert software engineer. Answer the following question from another AI assistant concisely.",
                                message=question
                            )
                            # Send the answer back to Jules
                            await jules_agent.execute(command="send_message", session_id=session_id, data=json.dumps({"message": {"content": answer}}))
                            agent.context.log.log(type="info", heading="Answered Jules' Question", content=f"Automatically answered a question in session {session_id}:\nQ: {question}\nA: {answer}")
                            break # Only answer the latest question per check
            except Exception as e:
                agent.context.log.log(type="error", heading="Jules Monitoring Error", content=f"An error occurred while monitoring session {session_id}: {str(e)}")
                break

    async def execute(self, message: str, **kwargs) -> Response:
        global _monitoring_tasks
        context_id = self.agent.context.id
        state_data = self.loop_data.params_persistent.get("developer_orchestrator_data", {})
        current_state = state_data.get("state", "start")

        response_message = ""
        break_loop = True

        if current_state == "start":
            state_data["user_idea"] = message

            # Check for a GitHub URL in the user's message
            match = re.search(r'https?://github\.com/([^/]+/[^/]+)', message)
            if match:
                state_data["github_repo"] = match.group(1)

            research_agent = self.agent.get_tool(name="call_subordinate", method=None, args={"profile": "research-agent"}, message="", loop_data=self.loop_data)
            research_findings = await research_agent.execute(f"Research external solutions and best practices for implementing '{message}'.", depth="deep")
            state_data["research_findings"] = research_findings.message

            state_data["state"] = "awaiting_feedback"

            report = f"""Based on your idea and my initial research, here is a proposed plan:
**Initial Idea:**
{state_data['user_idea']}

**Research Findings & Recommendations:**
{state_data['research_findings']}

Please provide your feedback on this direction."""

            response_message = report

        elif current_state == "awaiting_feedback":
            state_data["user_feedback"] = message

            plan_prompt = f"""Based on the user's idea, the research findings, and the user's feedback, create a detailed, step-by-step task list for a junior software engineer to follow.

**User's Idea:**
{state_data['user_idea']}

**Research Findings:**
{state_data['research_findings']}

**User's Feedback:**
{state_data['user_feedback']}

**Task List:**
"""

            final_plan = await self.agent.call_utility_model(
                system="You are a senior software engineer creating a project plan.",
                message=plan_prompt
            )

            response_message = f"Thank you for your feedback. I have generated the final plan:\n\n{final_plan}\n\nI will now proceed to create the deployment package."
            state_data["plan"] = final_plan
            state_data["state"] = "create_deployment_package"
            break_loop = False

        elif current_state == "create_deployment_package":
            os.makedirs("deployment", exist_ok=True)
            with open("deployment/idea_summary.md", "w") as f:
                f.write(f"# Idea Summary\n\n{state_data['user_idea']}")
            with open("deployment/task_list.md", "w") as f:
                f.write(f"# Task List\n\n{state_data['plan']}")

            shutil.copy("knowledge/default/huggingface_deployment_sheet.md", "deployment/huggingface_deployment_sheet.md")
            shutil.copy("knowledge/default/api_log_sheet.md", "deployment/api_log_sheet.md")
            shutil.copy("knowledge/default/hf_log_retrieval_sheet.md", "deployment/hf_log_retrieval_sheet.md")

            if "github_repo" in state_data:
                repo = state_data["github_repo"]
                branch = f"feature/{sanitize_branch_name(state_data['user_idea'])}"
            else:
                repo = f"JsonLord/{sanitize_branch_name(state_data['user_idea'])}"
                branch = "main"

            params = {
                "github_repo": repo,
                "branch": branch,
                "hf_token_env_var": "HF_TOKEN",
                "hf_space_name": sanitize_branch_name(state_data['user_idea'])
            }
            with open("deployment/parameters.json", "w") as f:
                json.dump(params, f, indent=2)

            response_message = "The `/deployment` package has been created. Next, I will upload it to GitHub."
            state_data["state"] = "upload_to_github"
            break_loop = False

        elif current_state == "upload_to_github":
            with open("deployment/parameters.json", "r") as f:
                params = json.load(f)

            repo_name = params["github_repo"]
            branch_name = params["branch"]

            try:
                if "github_repo" in state_data: # Existing repo
                    clone_dir = "temp_repo"
                    if os.path.exists(clone_dir):
                        shutil.rmtree(clone_dir)

                    subprocess.run(["git", "clone", f"https://github.com/{repo_name}.git", clone_dir], check=True)
                    subprocess.run(["git", "checkout", "-b", branch_name], check=True, cwd=clone_dir)

                    # Copy deployment files into the repo, under a 'deployment' subdirectory
                    deployment_source = "deployment"
                    deployment_dest = os.path.join(clone_dir, "deployment")
                    if not os.path.exists(deployment_dest):
                        os.makedirs(deployment_dest)

                    for item in os.listdir(deployment_source):
                        s = os.path.join(deployment_source, item)
                        d = os.path.join(deployment_dest, item)
                        if os.path.isdir(s):
                            shutil.copytree(s, d, dirs_exist_ok=True)
                        else:
                            shutil.copy2(s, d)

                    subprocess.run(["git", "add", "deployment"], check=True, cwd=clone_dir)
                    subprocess.run(["git", "commit", "-m", f"Add deployment package for: {state_data['user_idea']}"], check=True, cwd=clone_dir)
                    subprocess.run(["git", "push", "origin", branch_name], check=True, cwd=clone_dir)

                    shutil.rmtree(clone_dir) # Clean up
                    response_message = f"Successfully pushed the deployment package to the new branch '{branch_name}' on https://github.com/{repo_name}"

                else: # New repo
                    # Need to init git repo in deployment folder
                    subprocess.run(["git", "init"], check=True, cwd="deployment")
                    subprocess.run(["git", "add", "."], check=True, cwd="deployment")
                    subprocess.run(["git", "commit", "-m", "Initial commit"], check=True, cwd="deployment")
                    subprocess.run(["gh", "repo", "create", repo_name, "--public", "--source=.", "--push"], check=True, cwd="deployment")
                    response_message = f"Successfully created and pushed to GitHub repository: https://github.com/{repo_name}"

                state_data["state"] = "awaiting_start_command"

            except subprocess.CalledProcessError as e:
                response_message = f"Error during GitHub operation: {e.stderr}"
                state_data["state"] = "start"
            except FileNotFoundError:
                response_message = "Error: `gh` or `git` CLI not found. Please ensure they are installed and authenticated."
                state_data["state"] = "start"

        elif current_state == "awaiting_start_command":
            if message.lower() == "start":
                with open("deployment/parameters.json", "r") as f:
                    params = json.load(f)

                hf_token = os.environ.get(params["hf_token_env_var"], "HF_TOKEN_NOT_FOUND")
                hf_space_name = params["hf_space_name"]

                prompt = f"""Follow the files in the deployment/ folder to prepare the codebase for deployment to a Hugging Face Space.

Your primary tool for this is the Hugging Face CLI, `hf`. Use the token `{hf_token}` to create a new space named `{hf_space_name}` with an appropriate SDK, and then push the prepared files there.

To monitor the deployment, you MUST use the `huggingface_log_viewer` tool. Refer to the `hf_log_retrieval_sheet.md` for instructions on how to use it. After pushing the files, use the tool to retrieve the logs and validate the build's success. If you encounter issues retrieving container logs, ask the user to provide them."""

                jules_agent = self.agent.get_tool(name="jules_api", method=None, args={}, message="", loop_data=None)

                session_data = {
                    "source": {
                        "gitSource": {
                            "repoUri": f"https://github.com/{params['github_repo']}",
                            "branch": params["branch"]
                        }
                    },
                    "initial_prompt": prompt
                }

                response = await jules_agent.execute(command="create_session", data=json.dumps(session_data))

                session_info = json.loads(response.message)
                state_data["jules_session_id"] = session_info.get("name")

                response_message = f"Jules session started. I will now begin monitoring the session for progress."
                state_data["state"] = "monitoring_jules"
                break_loop = False
            else:
                response_message = "I am waiting for you to say 'Start' to begin the execution phase with the Jules agent."

        elif current_state == "monitoring_jules":
            task = _monitoring_tasks.get(context_id)
            if not task or task.done():
                session_id = state_data.get("jules_session_id")
                if session_id:
                    new_task = asyncio.create_task(self._monitor_jules_session(session_id, self.agent))
                    _monitoring_tasks[context_id] = new_task
                    response_message = f"Jules session monitoring has started (ID: {session_id}). I will check for updates every 15 minutes. You can continue with other tasks."
                else:
                    response_message = "Error: No Jules session ID found."
                    state_data["state"] = "start"
            else:
                response_message = "Jules session is already being monitored."

            break_loop = True

        else:
            response_message = f"Orchestrator is in an unknown state: {current_state}. Resetting."
            state_data = {"state": "start"}

        self.loop_data.params_persistent["developer_orchestrator_data"] = state_data

        return Response(message=response_message, break_loop=break_loop)
