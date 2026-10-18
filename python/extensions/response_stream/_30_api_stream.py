async def response_stream(agent, text, parsed, **kwargs):
    if hasattr(agent.context, 'stream_queue'):
        agent.context.stream_queue.put({'type': 'response', 'text': text, 'parsed': parsed})
