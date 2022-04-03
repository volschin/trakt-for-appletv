# https://github.com/aio-libs/aiohttp/blob/936e682d1ab6c833b3e5f0cc3596882cb9cb2444/aiohttp/web_runner.py#L274
import asyncio
import signal
from typing import cast
from helpers.graceful_exit import GracefulExit
from pyatv import connect
from pyatv.core.relayer import Relayer
from pyatv.interface import PushListener, DeviceListener, AppleTV, Playing
from pyatv.protocols.mrp import MrpProtocol
from pyatv.protocols.mrp.protobuf import ContentItemMetadata


def _raise_graceful_exit() -> None:
    raise GracefulExit()


class TVProtocol(PushListener, DeviceListener):
    atv: AppleTV

    def __init__(self, atv, conf):
        self.atv = atv
        self.conf = conf
        self.protocol = cast(
            MrpProtocol,
            cast(Relayer, self.atv.remote_control).main_instance.protocol
        )

    def playstatus_update(self, updater, playstatus: Playing):
        # app = updater['metadata']['identifier']
        # update.psm.playing.metadata
        title = playstatus.title if playstatus.series_name is None else playstatus.series_name
        print('{}: {} is {}'.format(self.atv.metadata.app.name, title, playstatus.device_state.name))

    def playstatus_error(self, updater, exception):
        print(exception)
        # Error in exception

    def connection_lost(self, exception: Exception) -> None:
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(connect(self.conf, loop), loop)

    def connection_closed(self) -> None:
        pass

    async def setup(self) -> None:
        self.atv.listener = self
        self.atv.push_updater.listener = self
        self.atv.push_updater.start()
        loop = asyncio.get_event_loop()
        try:
            loop.add_signal_handler(signal.SIGINT, _raise_graceful_exit)
            loop.add_signal_handler(signal.SIGTERM, _raise_graceful_exit)
        except NotImplementedError:  # pragma: no cover
            # add_signal_handler is not implemented on Windows
            pass

    async def cleanup(self) -> None:
        loop = asyncio.get_event_loop()
        self.atv.push_updater.stop()
        remaining_tasks = self.atv.close()
        await asyncio.wait_for(asyncio.gather(*remaining_tasks), 10.0)
        try:
            loop.remove_signal_handler(signal.SIGINT)
            loop.remove_signal_handler(signal.SIGTERM)
        except NotImplementedError:  # pragma: no cover
            # remove_signal_handler is not implemented on Windows
            pass
