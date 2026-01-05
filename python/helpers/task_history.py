import json
import time
from datetime import datetime
import asyncio

class TaskHistorySystem:
    """
    A comprehensive Task History System for Agent Zero that records detailed
    task execution data and uses it to optimize future performance.
    """

    def __init__(self, agent):
        self.agent = agent
        self.agent_id = "agent-zero"
        self.current_tasks = {}
        self.feedback_weights = {
            'execution_time': 0.3,
            'accuracy': 0.4,
            'user_satisfaction': 0.3
        }

    async def start_task_recording(self, task_id: str, task_name: str, task_type: str,
                            parameters: dict = None):
        """
        Start recording a new task execution.
        """
        self.current_tasks[task_id] = {
            'task_name': task_name,
            'task_type': task_type,
            'parameters': parameters or {},
            'start_time': time.time(),
            'start_timestamp': datetime.now().isoformat(),
            'status': 'running'
        }

        # Save initial task metadata
        memory_id = await self._save_to_memory({
            'record_type': 'task_start',
            'task_id': task_id,
            'task_name': task_name,
            'task_type': task_type,
            'parameters': parameters,
            'start_timestamp': datetime.now().isoformat(),
            'agent_id': self.agent_id
        }, f"task_start_{task_id}")

        return {'task_id': task_id, 'status': 'recording_started', 'memory_id': memory_id}

    async def complete_task_recording(self, task_id: str, result: any, success: bool = True,
                              error_message: str = None, output_size: int = 0):
        """
        Complete the recording of a task execution with final results.
        """
        if task_id not in self.current_tasks:
            return {'error': f'Task {task_id} not found in active tasks'}

        task_data = self.current_tasks[task_id]
        end_time = time.time()
        execution_time = end_time - task_data['start_time']

        # Update task status
        task_data['status'] = 'completed'
        task_data['end_time'] = end_time
        task_data['end_timestamp'] = datetime.now().isoformat()
        task_data['execution_time'] = execution_time
        task_data['success'] = success
        task_data['result_summary'] = str(result)[:500]  # Truncate long results
        task_data['error_message'] = error_message
        task_data['output_size'] = output_size

        # Calculate performance score
        performance_score = self._calculate_performance_score(task_data)
        task_data['performance_score'] = performance_score

        # Save complete task record
        memory_id = await self._save_to_memory({
            'record_type': 'task_complete',
            'task_id': task_id,
            'task_name': task_data['task_name'],
            'task_type': task_data['task_type'],
            'parameters': task_data['parameters'],
            'start_timestamp': task_data['start_timestamp'],
            'end_timestamp': task_data['end_timestamp'],
            'execution_time': execution_time,
            'success': success,
            'performance_score': performance_score,
            'result_summary': task_data['result_summary'],
            'error_message': error_message,
            'output_size': output_size,
            'agent_id': self.agent_id,
            'version': '1.0'
        }, f"task_complete_{task_id}")

        # Clean up from current tasks
        completed_task = self.current_tasks.pop(task_id)

        return {
            'task_id': task_id,
            'status': 'completed',
            'execution_time': execution_time,
            'performance_score': performance_score,
            'memory_id': memory_id
        }

    async def record_user_feedback(self, task_id: str, user_satisfaction: int,
                           comments: str = None, accuracy_rating: int = None):
        """
        Record user feedback for a completed task.
        Ratings are on a scale of 1-5.
        """
        feedback_data = {
            'record_type': 'user_feedback',
            'task_id': task_id,
            'user_satisfaction': max(1, min(5, user_satisfaction)),  # Clamp to 1-5
            'comments': comments,
            'accuracy_rating': accuracy_rating,
            'feedback_timestamp': datetime.now().isoformat(),
            'agent_id': self.agent_id
        }

        memory_id = await self._save_to_memory(feedback_data, f"feedback_{task_id}")

        # Update the performance score with user feedback
        self._update_performance_with_feedback(task_id, feedback_data)

        return {'status': 'feedback_recorded', 'memory_id': memory_id}

    async def _save_to_memory(self, data: dict, memory_key: str) -> str:
        from python.tools.memory_save import MemorySave
        """
        Save data to persistent memory using the memory_save tool.
        """
        memory_save_tool = MemorySave(agent=self.agent, name="memory_save", method=None, args={}, message="", loop_data=None)
        data_str = json.dumps(data)
        response = await memory_save_tool.execute(text=data_str, area="task_history", key=memory_key)

        # The response is expected to be a Response object with a message attribute
        # in the format "Memory saved with ID: <id>"
        if hasattr(response, 'message') and isinstance(response.message, str) and ":" in response.message:
            try:
                memory_id = response.message.split(":", 1)[1].strip()
                return memory_id
            except IndexError:
                return "unknown"
        return "unknown"


    def _calculate_performance_score(self, task_data: dict) -> float:
        """
        Calculate a performance score based on execution metrics.
        """
        # Base score from success/failure
        base_score = 1.0 if task_data.get('success', False) else 0.0

        # Normalize execution time (assume 10 seconds is 'average')
        execution_time = task_data.get('execution_time', 0)
        time_score = max(0, min(1, (10 - execution_time) / 10)) if execution_time < 20 else 0

        # Combine scores with weights
        final_score = (
            base_score * 0.6 +
            time_score * 0.4
        )

        return round(final_score, 3)

    def _update_performance_with_feedback(self, task_id: str, feedback_data: dict):
        """
        Update the performance score with user feedback.
        """
        # In a real implementation, this would retrieve the task record,
        # update it with feedback, and save it back
        pass

    def get_task_statistics(self, task_name: str = None, task_type: str = None,
                          time_range: str = 'all') -> dict:
        """
        Get statistics for tasks, optionally filtered by name, type, or time range.
        """
        # In reality, this would use memory_load to retrieve relevant records
        # For now, return a template response
        return {
            'task_name': task_name or 'all',
            'task_type': task_type or 'all',
            'time_range': time_range,
            'total_executions': 0,
            'success_rate': 0.0,
            'avg_execution_time': 0.0,
            'best_performance': 0.0,
            'worst_performance': 0.0,
            'trend': 'unknown'
        }

    def get_optimal_approach(self, task_type: str, parameters: dict = None) -> dict:
        """
        Analyze historical data to recommend the optimal approach for a task type.
        """
        # In reality, this would query the memory system for past executions
        # of similar tasks and analyze which approaches performed best

        # Placeholder logic - in reality this would be data-driven
        recommendations = {
            'task_type': task_type,
            'recommended_approach': 'default',
            'confidence': 0.5,
            'expected_performance': 0.7,
            'execution_time_prediction': 5.0,
            'success_probability': 0.8,
            'historical_benchmark': {
                'avg_execution_time': 7.5,
                'success_rate': 0.75,
                'avg_performance_score': 0.65
            }
        }

        # Example: For git operations, recommend specific strategies
        if task_type == 'git_operation':
            recommendations['recommended_approach'] = 'use_git_agent_with_validation'
            recommendations['confidence'] = 0.8

        return recommendations

    def generate_performance_report(self, time_period: str = 'last_7_days') -> str:
        """
        Generate a performance report based on task history.
        """
        # This would compile data from multiple task records
        return f"Performance report for {self.agent_id} - {time_period}\n" + \
               "Details would include success rates, execution times, and improvement trends."
