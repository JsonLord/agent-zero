import subprocess
import time
import requests
from python.helpers.mcp_handler import MCPConfig, MCPServerLocal, MCPServerRemote
from python.helpers.print_style import PrintStyle

class MCPManager:
    """
    Manages the lifecycle of MCP servers.
    """

    def __init__(self):
        self.processes = {}

    def start_server(self, server: MCPServerLocal):
        """
        Starts a local MCP server.
        """
        try:
            process = subprocess.Popen(
                [server.command] + server.args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.processes[server.name] = process
            PrintStyle(background_color="green", font_color="white", padding=True).print(
                f"Started MCP server: {server.name}"
            )
        except Exception as e:
            PrintStyle(background_color="red", font_color="white", padding=True).print(
                f"Error starting MCP server {server.name}: {e}"
            )

    def check_servers(self):
        """
        Checks the status of all configured MCP servers.
        """
        mcp_config = MCPConfig.get_instance()
        for server in mcp_config.servers:
            if isinstance(server, MCPServerLocal):
                process = self.processes.get(server.name)
                if process and process.poll() is not None:
                    PrintStyle(background_color="red", font_color="white", padding=True).print(
                        f"MCP server {server.name} has stopped."
                    )
                elif process:
                    PrintStyle(background_color="green", font_color="white", padding=True).print(
                        f"MCP server {server.name} is running."
                    )
            elif isinstance(server, MCPServerRemote):
                try:
                    response = requests.get(server.url, timeout=5)
                    if response.status_code == 200:
                        PrintStyle(background_color="green", font_color="white", padding=True).print(
                            f"MCP server {server.name} is reachable."
                        )
                    else:
                        PrintStyle(background_color="red", font_color="white", padding=True).print(
                            f"MCP server {server.name} is unreachable (status code: {response.status_code})."
                        )
                except requests.exceptions.RequestException as e:
                    PrintStyle(background_color="red", font_color="white", padding=True).print(
                        f"Error checking MCP server {server.name}: {e}"
                    )

    def manage_servers(self):
        """
        Starts local MCP servers and checks the status of all servers.
        """
        mcp_config = MCPConfig.get_instance()
        for server in mcp_config.servers:
            if isinstance(server, MCPServerLocal):
                self.start_server(server)

        # Give the servers a moment to start up
        time.sleep(5)
        self.check_servers()

_mcp_manager = None

def get_mcp_manager():
    """
    Returns a singleton instance of the MCPManager.
    """
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager
