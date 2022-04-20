# https://gist.github.com/jdowner/d4b4079678ed7ce39212
import asyncio
import sys


async def async_input(prompt: str, timeout: int) -> str:
    """ Get input from user with timeout.

    :param prompt: Prompt to display to user.
    :param timeout: Timeout in seconds.
    :return: Input from user.
    :raise asyncio.TimeoutError: If timeout is reached.
    """
    loop = asyncio.get_event_loop()
    queue = asyncio.Queue()
    print(prompt, end="")

    def response_handler():
        """ Handle response from user. """
        loop.create_task(queue.put(sys.stdin.readline()))

    loop.add_reader(sys.stdin, response_handler)
    try:
        response = await asyncio.wait_for(queue.get(), timeout)
    finally:
        loop.remove_reader(sys.stdin)
    return response.strip()
