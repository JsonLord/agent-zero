from python.helpers.extension import Extension
from agent import LoopData, AgentContextType
from python.helpers.hf_storage import HFStorageManager

class SaveChat(Extension):
    def __init__(self, agent):
        super().__init__(agent)
        self.storage_manager = HFStorageManager()

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        # Skip saving BACKGROUND contexts as they should be ephemeral
        if self.agent.context.type == AgentContextType.BACKGROUND:
            return

        # Serialize the context for persistence
        data_to_save = self.agent.context.serialize_for_persistence()

        # Save the conversation using the HFStorageManager
        self.storage_manager.save_conversation(
            conversation_id=self.agent.context.id,
            data=data_to_save
        )
