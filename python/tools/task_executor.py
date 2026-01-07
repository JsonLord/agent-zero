import json
from collections import defaultdict
from python.helpers.tool import Tool, Response

class TaskExecutor(Tool):
    """
    The core of the task_manager_subagent. This tool reads a task list from
    todo.ai, builds a dependency graph, and executes the tasks in the correct
    order, handling parallel execution and testing.
    """

    async def execute(self, **kwargs) -> Response:
        """
        Runs the entire task execution workflow.
        """
        # 1. Get the list of tasks from the taskmaster tool (todo.ai).
        tasks_response = await self.agent.call_tool("taskmaster", command="list --format json")
        try:
            tasks = json.loads(tasks_response.message)
            if not tasks:
                return Response(message="No tasks found to execute.", break_loop=True)
        except (json.JSONDecodeError, AttributeError):
            return Response(message=f"Error parsing task list: {tasks_response.message}", break_loop=True)

        # 2. Build the dependency graph and get the execution order.
        try:
            execution_plan = self._get_execution_plan(tasks)
        except ValueError as e:
            return Response(message=f"Error building dependency graph: {e}", break_loop=True)

        # 3. Execute the plan.
        for level, task_batch in enumerate(execution_plan):
            self.agent.send_message_to_user(f"Executing level {level + 1} of the plan...")

            parallel_tasks = {task['id']: task for task in task_batch if task.get('parallel')}
            sequential_tasks = [task for task in task_batch if not task.get('parallel')]

            # Execute parallel tasks first using swarmtask.
            if parallel_tasks:
                swarm_commands = {task_id: task['description'] for task_id, task in parallel_tasks.items()}
                response = await self.agent.call_tool("swarmtask_tool", tasks=json.dumps(swarm_commands))
                if response.break_loop:
                    for task_id in parallel_tasks:
                        await self.agent.call_tool(
                            "taskmaster",
                            command=f"add --priority high 'Fix failed parallel task {task_id}'"
                        )
                    continue  # Skip to the next level

                for task_id in parallel_tasks:
                    await self._run_test_and_handle_failure(parallel_tasks[task_id])


            # Execute sequential tasks one by one.
            for task in sequential_tasks:
                assigned_agent = task.get('agent', 'developer-agent')
                response = await self.agent.call_tool(assigned_agent, command=task['description'])
                if response.break_loop:
                    await self.agent.call_tool(
                        "taskmaster",
                        command=f"add --priority high 'Fix failed sequential task {task['id']}'"
                    )
                    continue # Skip to the next task
                await self._run_test_and_handle_failure(task)

        return Response(message="All tasks have been executed.", break_loop=True)

    async def _run_test_and_handle_failure(self, task: dict):
        """
        (Placeholder) Runs the test for a task and handles failure.
        """
        test_goal = task.get('test_goal')
        if not test_goal:
            # Mark task as successful if there's no test.
            await self.agent.call_tool("taskmaster", command=f"done {task['id']}")
            return

        # Delegate test creation and execution to the new, specialized tool.
        test_result_response = await self.agent.call_tool(
            "create_and_run_test",
            test_goal=test_goal
        )

        try:
            test_result = json.loads(test_result_response.message)
            if test_result.get("status") == "success":
                await self.agent.call_tool("taskmaster", command=f"done {task['id']}")
            else:
                await self.agent.call_tool(
                    "taskmaster",
                    command=f"add --priority high 'Fix failed test for task {task['id']}: {test_goal} - {test_result.get('message', '')}'"
                )
        except (json.JSONDecodeError, AttributeError):
            # Create a new high-priority task to fix the failure.
            await self.agent.call_tool(
                "taskmaster",
                command=f"add --priority high 'Fix failed test for task {task['id']}: {test_goal}'"
            )

    def _get_execution_plan(self, tasks: list) -> list:
        """
        Builds a dependency graph and returns a topologically sorted execution plan.
        The plan is a list of lists, where each inner list is a batch of tasks that
        can be executed in parallel.
        """
        adj = defaultdict(list)
        in_degree = defaultdict(int)
        task_map = {task['id']: task for task in tasks}

        for task in tasks:
            task_id = task['id']
            dependencies = task.get('dependencies', [])
            if not isinstance(dependencies, list):
                dependencies = [dependencies]

            for dep in dependencies:
                if dep in task_map:
                    adj[dep].append(task_id)
                    in_degree[task_id] += 1

        queue = [task_id for task_id in task_map if in_degree[task_id] == 0]

        execution_plan = []
        while queue:
            level_tasks = []
            for _ in range(len(queue)):
                current_task_id = queue.pop(0)
                level_tasks.append(task_map[current_task_id])

                for neighbor_id in adj[current_task_id]:
                    in_degree[neighbor_id] -= 1
                    if in_degree[neighbor_id] == 0:
                        queue.append(neighbor_id)
            execution_plan.append(level_tasks)

        if sum(len(level) for level in execution_plan) != len(tasks):
            raise ValueError("A cycle was detected in the task dependencies.")

        return execution_plan
