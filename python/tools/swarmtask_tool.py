import subprocess
import json
import threading
from queue import Queue

def worker(q, results):
    """Worker function to process tasks from the queue."""
    while not q.empty():
        try:
            task_name, command = q.get()
            process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                check=True
            )
            results[task_name] = {"status": "completed", "output": process.stdout}
        except subprocess.CalledProcessError as e:
            results[task_name] = {"status": "error", "output": e.stderr}
        except Exception as e:
            results[task_name] = {"status": "error", "output": str(e)}
        finally:
            q.task_done()

def swarmtask_tool(tasks_json: str) -> str:
    """
    A tool for executing a swarm of tasks in parallel using Python threading.

    Args:
        tasks_json: A JSON string representing a dictionary of tasks.
                    The keys are task names and the values are the shell commands to execute.
                    Example: '{"task1": "echo hello", "task2": "sleep 1 && echo world"}'

    Returns:
        A JSON string with the results of the executed tasks.
    """
    try:
        tasks = json.loads(tasks_json)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON string provided for tasks."})

    if not isinstance(tasks, dict):
        return json.dumps({"error": "Tasks must be provided as a dictionary."})

    task_queue = Queue()
    for name, command in tasks.items():
        task_queue.put((name, command))

    results = {}
    threads = []
    num_threads = min(len(tasks), 10) # Limit to 10 concurrent threads

    for _ in range(num_threads):
        thread = threading.Thread(target=worker, args=(task_queue, results))
        thread.start()
        threads.append(thread)

    task_queue.join() # Block until all tasks are done

    for thread in threads:
        thread.join()

    return json.dumps(results, indent=2)
