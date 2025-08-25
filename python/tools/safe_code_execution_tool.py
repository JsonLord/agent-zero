from python.helpers.tool import Tool, Response
from python.helpers.safe_code_executor import SafeCodeExecutor

class SafeCodeExecution(Tool):

    def __init__(self, agent, name, method, args, message, loop_data, **kwargs):
        super().__init__(agent, name, method, args, message, loop_data, **kwargs)
        self.executor = SafeCodeExecutor()

    async def execute(self, **kwargs):
        runtime = self.args.get("runtime", "").lower().strip()
        code = self.args.get("code", "")

        if runtime == "python":
            result = self.executor.execute_python(code)
            return Response(message=result, break_loop=False)
        else:
            return Response(message=f"Error: runtime '{runtime}' is not supported. Only 'python' is supported.", break_loop=False)

    async def after_execution(self, response, **kwargs):
        self.agent.hist_add_tool_result(self.name, response.message)
