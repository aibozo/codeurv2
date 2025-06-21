import asyncio, signal
from .main import main_loop

loop = asyncio.get_event_loop()
task = loop.create_task(main_loop())
for s in (signal.SIGINT, signal.SIGTERM):
    loop.add_signal_handler(s, task.cancel)
loop.run_until_complete(task)