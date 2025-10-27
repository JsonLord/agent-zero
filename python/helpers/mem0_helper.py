import os
from mem0 import MemoryClient
from dotenv import load_dotenv

load_dotenv()

class Mem0Helper:
    def __init__(self):
        self.api_key = os.getenv("MEM0_API_KEY")
        if not self.api_key:
            raise ValueError("MEM0_API_KEY not found in environment variables")
        self.client = MemoryClient(api_key=self.api_key)

    def get_memory(self, user_id: str, query: str):
        return self.client.search(query=query, user_id=user_id)

    def add_memory(self, user_id: str, role: str, content: str):
        """Adds a single message to the memory."""
        message = {"role": role, "content": content}
        self.client.add(messages=[message], user_id=user_id)

    def get_relevant_memories(self, user_id: str, query: str):
        """Retrieves relevant memories for a given query."""
        memories = self.client.search(query=query, user_id=user_id)
        return memories if memories is not None else []

    def get_all_memories(self, user_id: str):
        """Retrieves all memories for a given user."""
        return self.client.get_all(user_id=user_id)

    def delete_user_memories(self, user_id: str):
        """Deletes all memories for a given user."""
        memories = self.get_all_memories(user_id=user_id)
        for memory in memories:
            self.client.delete(memory_id=memory['id'])
