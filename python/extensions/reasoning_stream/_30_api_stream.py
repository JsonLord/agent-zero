async def reasoning_stream(agent, text, **kwargs):
    if hasattr(agent.context, 'stream_queue'):
        agent.context.stream_queue.put({'type': 'reasoning', 'text': text})
