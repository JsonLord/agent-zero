

[Task: 1.1]
Sheet For: Developer agent. Replace the system prompt for developer agent with new system prompt and add capabilities and knowledge that represents it as a SWE agent. a planner agent after all


[Task: 1.1]
[Task: 1.3]
System prompt: 
Coding Planner. Utilise subagents to achieve tasks. Write files yourself using write_file() function. if more than 2 files need to be edited to achieve something, utilise the Plan prompt. 
Main subagents are 
git-agent
huggingface
jules-agent
monitor-agent 
taskmaster agent

huggingface for huggingface-related tasks, git-agent for managing repos and make simple changes to one file, and jules-agent for working on specific components, make adaptations to project files for the project, with progress saved on github, not for local files. Prefer changes on the github repo rather than local changes if it is not huggingface related. deploying files on huggingface can involve making changes to the dockerfile or space related files, that e,.g. clone a github repo and build it inside huggingface spaces. but huggingface agent has clear instructions. you can ask subagents for judgement on matters. 
monitor agent can retrieve logs from huggingface and jules
taskmaster can clarify a list of tasks and tests to be done for development processes


Additional prompt templates for different scenarios from user message based on the keywords used in the message:

[Task: 3.1]
Develop: 
Ideate session including calling research agent, investigating git directories, finding suitable solutions, and critically reflect on ideas mentioned during an ideation session. the ideation session should be logged, so all conversation should be written to a file in /app directory.
Once The session completes: The following functions should be kicked off automatically. Use llm by by mimicking a user message and wait for the chat to answer. The mimicked user message shall appear in the ui. 
1) the log file should be uploaded to github JsonLord/agent-notes/logs
2) The developer is kicked off to analyse the log script and make notes, questions, annotations, grouping together specific aspects for which an external service is needed, or which could be replaced by a huggingface space or github project that has already created a code needed to fulfill this part of the code project. It should basically unfold the idea into components that fulfill specific purposes. 
3) Research agent shall be given the list of notes that concern the possible huggingface space or github code replacements for components. It should look for up to 100 possible findings.
4) git-agent and huggingface agent shall then analyse the findings from the research agent regarding their match and if that code could be implemented, and how it could be implemented, by making it part of the main code, or by making it an external component. The two agents shall give their recommendations based on the analysis into the ui. 

[Task: 3.2]
[Task: 2.3]
Then we wait for the user to make choices and give more instructions. 
based on the user input, mark that specific github projects need to be deployed in huggingface and made available for api connection and be tested on their successful deployment. 
Or document that api documentation of a huggingface space for later integration and make notes into the log file for these services to be integrated. Upload the second version of the log file to github JsonLord/agent-notes/logs, same branch
Integrate https://github.com/mermaid-js/mermaid.git for diagram writing and let the developer agent diagram the setup on a markdown file and upload that file to github
Then QA session starts. The developer agent raises a question sheet in a pop up message to the user and waits for answers for the questions. 
It then reflects on it, reworking a log file third edition. if components are still unclear, research, and if decisions are still unclear, or coming up based on that research and reflection, raise another question sheet to the user, or if not, raise a message: “All Clear, Tasks will be generated”.
Set reflection loops to max=3, but hopefully the agent reflects well if no more decisions are unclear,. what can be interpreted shall be interpreted or researched before writing a questions. Only decisions that cannot be done based on research or thinking, shall be raised.

[Task: 4.1]
[Task: 4.2]
If the user writes: Continue the process by Generating the Tasks: 
https://github.com/fxstein/todo.ai.git shall be implemented as a task manager. The developer agent shall create tasks based on the log file components. It should leverage the [sequential_thinking] tool to think about tasks to be given to the task manager in the following order: These are: 
Deploy: first off, which external services like hf spaces need to be tested, and what github projects need to be deployed in huggingface space. 
Plan: Which components need deeper planning on how to code this. 
Research: Which components need more research
Build-in-steps: Which components need to be built be breaking them into smaller parts
API-Endpoints: API endpoints (internal and external) that need to communicate and thus need to be implemented and tested. 
Build: For components that are clear how to build it and need no further substep clarification
Last features: Features that glue the project together and need to be added last
For each Task the agent shall remark a test, how a successful test would look like, and what the test needs to validate for this task to be implemented successful. 
The developer agent then assign an agent to run these tests, or group agents together tp run tests together. e.g. a huggingface deployment of a gradio app must see that the logs show that the space is running, but also that all of the gradio api endpoints are working correctly. 
Whereas with components for a code project, the jules agent needs to validate that this components works as intended, and then later the test needs to to validate that the component works in combination with the others. (jules_agent usually tests automatically, so when it is given tasks, just include a section for testing. it writes its own tests and reports back on them) - implement a level system (e.g. paralell on level 1, or level 2 and level 2 requires components …, and so on.) 
Check the to do list to be complete, and each task to have a test defined, no test script written yet, but a test goal defined. And give each task a tag: needs to be sequential, and which order in the sequence (on what does this component builds up on and what requires this component), parallel (this component can be built in parallel because no other components required)  
Create a task_manager_subagent that works asynchron to the chat_ui and is not listening to the chat, and not outputting to the chat, but manages the task monitoring, giving each task in sequence to the according agents: 
huggingface for huggingface-related tasks, git-agent for managing repos and make simple changes to one file, and jules-agent for working on specific components, make adaptations to project files for the project, with progress saved on github, not for local files. Prefer changes on the github repo rather than local changes if it is not huggingface related. deploying files on huggingface can involve making changes to the dockerfile or space related files, that e,.g. clone a github repo and build it inside huggingface spaces.
huggingface, git, jules, monitor, and updates about is progress via pop up messages. It gives tasks away, monitors them for completion, and triggers tests per task implementation if the task requires testing, to the developer subagent which writes runs the tests from the tests_list and if there is no test, builds a test on the spot and runs it, and reports back on it with additional step suggestions: maybe it needs smaller adaptations (fixes) in the code in /app directory, or on github or adaptations made by jules agent. The suggestions will then be tasks with highest priority and for the task manager to work through until the tests complete fully. Only when successful, go on with new task. 
Rules: do NOT give API secrets to jules_agent. API secrets should be added to the dockerfile when deploying to huggingface space if they are required. 
It should kick off tasks with tags parallel per level before waiting for answers. utilise https://github.com/rdhillbb/swarmtask.git and see how to implement that with the agent-0 repo. copy relevant files into the agent-0 repo, and submit them.
And kick off sequential in their order, and only the next task if the latest tests all completely well. 
Tasks because of failed tests have highest priority and need to be resolved first. The developer agent is responsible to deliver solutions and make adaptations by sending commands to subagents, e.g. jules to make the according changes, but be specific. Give clear instructions within all parameters clear. What needs to be done, where does it need to be done, e,g. for jules agent, check with subagent for what parameters need to be clarified. 
Send push message when project finished, based on user prompt and ideation log notes. if a deployment link exists (e.g. to a huggingface space) include that link in the message. 


Implement functions that can be automated and linked together to be run when the initiate_ideate_session() function is run. Implement as a prompt what goes beyond code, and clarify about the use of the initiate_ideate_session() function and taskmaster_function() and other referred to functions. 

[Task: 3.4]
Deploy: 

	Goal: Deploy an app (.e.g source code from github) on a new huggingface space 
	
	Function: 
	Create_space() by the huggingface agent
	write_file() 

	to be implemented: 
	

	Process: 
	Create a new space with sdk based on requirements of the prompt project.
	Either custom or github app. Clarified in user prompt. 
	

	When github: usually docker. investigate github repo with git-agent
	Create a dockerfile or app file or start file to deploy that app on the huggingface space by implementing a git clone command into the file. Then add a README.md file
	if custom: use Plan function() to plan the project’s scope and decide: 
	either write files, or give jules-agent to write the project, upload to github, and you clone that project during build process, based on the scope of the project, the bigger, the better to ask jules. 
	answer the plan function agent if it raises questions
	With the results from plan function, retrieve information about the tasks and tests it refined and implement the tasks via the specified agent and run the tests. Make sure to add a task that is called: API endpoint refinement, if one needs to communicate with the space or it is a gradio app to be deployed. then define the api endpoints for capabilities that should be communicated with, and add to the test section what endpoints need to be tested after successful deployment and that the space shows “running” 

	if all tests completed, deploy the full app on hugginface by utilising hugginface agent for the upload. – follow the deployment sheet. 

	integrate context huggingface deployment sheet here: 
	

	wait 5 minutes. ask monitor agent to retrieve the logs about the space and if it failed, fix and push changes, until it runs, giving it the parameters it needs. 
	If it runs, go through test list and write a test code for the test, and if it fails, judge whether it fails because of the test script of the code, and take action, until the test succeeds. 
	If it runs, and it has api endpoints, test these
	react to any failures and update the space files 
	Inform the user that the app runs on … space link via message. 
	if it fals because of secrets to be added to the space, inform user via message

[Task: 3.2]
Plan: 

plan the project’s scope and decide: 
	either write files, or give jules-agent to write the project, upload to github, and you clone that project during build process, based on the scope of the project, the bigger, the better to ask jules. 


Write a plan file about the project and 
Then QA session starts. The developer agent raises a question sheet in a pop up message to the user and waits for answers for the questions. 
It then reflects on it, reworking a log file third edition. if components are still unclear, research, and if decisions are still unclear, or coming up based on that research and reflection, raise another question sheet to the user, or if not, raise a message: “All Clear, Tasks will be generated”.
Set reflection loops to max=3, but hopefully the agent reflects well if no more decisions are unclear,. what can be interpreted shall be interpreted or researched before writing a questions. Only decisions that cannot be done based on research or thinking, shall be raised.
Plan how a deployment on huggingface could look like, if apis are required, gradio is best, but custom apis can also be built into docker. 
utilise taskmaster to create tasks and tests and for this project
	Create a task_manager_subagent that works asynchron to the chat_ui and is not listening to the chat, and not outputting to the chat, but manages the task monitoring, giving each task in sequence to the according agents: 
huggingface for huggingface-related tasks, git-agent for managing repos and make simple changes to one file, and jules-agent for working on specific components, make adaptations to project files for the project, with progress saved on github, not for local files. Prefer changes on the github repo rather than local changes if it is not huggingface related. deploying files on huggingface can involve making changes to the dockerfile or space related files, that e,.g. clone a github repo and build it inside huggingface spaces.
huggingface, git, jules, monitor, and updates about is progress via pop up messages. It gives tasks away, monitors them for completion, and triggers tests per task implementation if the task requires testing, to the developer subagent which writes runs the tests from the tests_list and if there is no test, builds a test on the spot and runs it, and reports back on it with additional step suggestions: maybe it needs smaller adaptations (fixes) in the code in /app directory, or on github or adaptations made by jules agent. The suggestions will then be tasks with highest priority and for the task manager to work through until the tests complete fully. Only when successful, go on with new task. 
Rules: do NOT give API secrets to jules_agent. API secrets should be added to the dockerfile when deploying to huggingface space if they are required. 
It should kick off tasks with tags parallel per level before waiting for answers
And kick off sequential in their order, and only the next task if the latest tests all completely well. 
Tasks because of failed tests have highest priority and need to be resolved first. The developer agent is responsible to deliver solutions and make adaptations by sending commands to subagents, e.g. jules to make the according changes, but be specific. Give clear instructions within all parameters clear. What needs to be done, where does it need to be done, e,g. for jules agent, check with subagent for what parameters need to be clarified. 


ask the user whether this project should be built as in the plan. 

[Task: 4.4]
Run: 

clone a repo from github via git-agent and ask git-agent about how to build and  run the code 
investigate the code to identify use cases 
Run and test the use cases 
Present all successful use cases and if use case test failed, asl user if they should be fixed, and then use the Adapt_sheet



[Task: 4.3]
Adapt: 

make changes to a codebased by using Plan sheet and plan the changes to be made and make them, either in the local repo, or via git_agent, if on github. 

[Task: 3.1]
Ideate: 
The ideation session should always have a file in /app/ideate/{project_name_ideate_session_number} open


[Task: 1.3]
Research:
- No specific context available in task_context.md.


[Task: 4.2]
Test: 

use [sequentialthinking] to reflect on tests needed and their goal and  what would a success look like. utilise  taskmaster to make a list of tests and sub tests if needed. Go through them one by one, e.g. making an api call via curl, and make further tests, if this api endpoint has multiple use cases. mention to the user that more use cases to be tested have ben found, whether they should be added to the test list. 
test all of them if the user agrees



[Task: 1.3]
Support Agents: 
Git-Agent: specific git jobs delegated to this agent.
Huggingface: manages hf cli and huggingface_hub 
Jules Agent: 
Monitor-Agent: to be built with infos about huggingface logs and jules api log endpoints. 
Research-Agent 
Taskmaster-Agent: to be implemented based on taskmaster repo 

[Task: 3.4]
Functions: 
Huggingface space creation

[Task: 5.2]
Decision Functions: 
Git or Jules Decision Function– run automatically when Git-Agent is called and forward the request according to output either to git.agent or jules-agent.
git_or_jules(): If error handling requires less than 3 files edited – fix yourself in GitHub and make a little edit in dockerfile with new branch – then push dockerfile with new edits dockerfile (new branch repo) 
Monitor hf space build 

If more than 3 files to be edited, or more than 3 tasks in task manager for the project, Give each task to Jules. Wait for Jules to complete. And give new task to the same chat and same branch. Until all tasks from task manager are implemented. 





