# https://github.com/aio-libs/aiohttp/blob/936e682d1ab6c833b3e5f0cc3596882cb9cb2444/aiohttp/web_runner.py#L274
import asyncio
import logging
import os
import signal
import warnings
from typing import cast, Optional, List

import pyatv
from pyatv.const import FeatureState, FeatureName

from helpers.graceful_exit import GracefulExit
from pyatv import connect
from pyatv.core.relayer import Relayer
from pyatv.interface import PushListener, DeviceListener, AppleTV, Playing
from pyatv.protocols.mrp import MrpProtocol
import yaml


def _raise_graceful_exit() -> None:
    raise GracefulExit()


class TVProtocol(PushListener, DeviceListener):
    atv: Optional[AppleTV]

    def __init__(self):
        self.atv = None
        self.device = None
        self.protocol = None
        self._config_file = 'data/config.yml'
        self._pairing_file = 'data/pairing.state'
        self.settings = self._read_settings()
        self.protocol = None

    def playstatus_update(self, updater, playstatus: Playing):
        title = playstatus.title if playstatus.series_name is None else playstatus.series_name
        print('{}: {} is {}'.format(self.atv.metadata.app.name, title, playstatus.device_state.name))

    def playstatus_error(self, updater, exception):
        print(exception)
        # Error in exception

    def connection_lost(self, exception: Exception) -> None:
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(connect(self.device, loop), loop)

    def connection_closed(self) -> None:
        pass

    async def setup(self) -> None:
        """ Add signal handlers to gracefully exit then connect to the Apple TV starting the push updater."""
        loop = asyncio.get_event_loop()
        try:
            loop.add_signal_handler(signal.SIGINT, _raise_graceful_exit)
            loop.add_signal_handler(signal.SIGTERM, _raise_graceful_exit)
        except NotImplementedError:  # pragma: no cover
            # add_signal_handler is not implemented on Windows
            pass

        await self._connect()
        self.atv.listener = self
        self.atv.push_updater.listener = self
        self.atv.push_updater.start()
        self.protocol = cast(
            MrpProtocol,
            cast(Relayer, self.atv.remote_control).main_instance.protocol
        )

    async def cleanup(self) -> None:
        """ Cleanup the Apple TV connection and remove signal handlers."""
        loop = asyncio.get_event_loop()
        try:
            loop.remove_signal_handler(signal.SIGINT)
            loop.remove_signal_handler(signal.SIGTERM)
        except NotImplementedError:  # pragma: no cover
            # remove_signal_handler is not implemented on Windows
            pass

        if self.atv is not None:
            self.atv.push_updater.stop()
            remaining_tasks = self.atv.close()
            await asyncio.wait_for(asyncio.gather(*remaining_tasks), 10.0)

    async def _connect(self) -> None:
        """ Connect to the Apple TV and store connection information."""
        loop = asyncio.get_event_loop()
        settings_atv = self.settings.get('apple_tv') or {}
        atv_id = settings_atv.get('id')
        devices = await self._scan_for_devices(settings_atv)
        device = self._choose_device(devices)

        if atv_id != device.identifier:
            self.settings['apple_tv'] = {}
            self.settings['apple_tv']['id'] = device.identifier
            self.settings['apple_tv']['name'] = device.name
            yaml.dump(self.settings, open(self._config_file, 'w'), default_flow_style=False)
            try:
                os.remove(self._pairing_file)
            except FileNotFoundError:
                pass

        await self._pair_device(device)
        print(f"Connecting to {device.address}")
        self.atv = await pyatv.connect(device, loop)
        if not self.atv.features.in_state(FeatureState.Available, FeatureName.PushUpdates):
            logging.error("Push updates are not supported (no protocol supports it)")
            _raise_graceful_exit()
        self.device = device

    async def _pair_device(self, device: pyatv.interface.BaseConfig) -> None:
        """ Pair with the Apple TV and store pairing information."""
        loop = asyncio.get_event_loop()
        if not os.path.exists(self._pairing_file):
            pairing = await pyatv.pair(device, pyatv.Protocol.AirPlay, loop)
            await pairing.begin()

            code = input("Enter code displayed by Apple TV: ")
            pairing.pin(code)

            await pairing.finish()
            await pairing.close()
            if pairing.has_paired:
                with open(self._pairing_file, "w") as f:
                    f.write(pairing.service.credentials)
            else:
                logging.error("Pairing failed")
                _raise_graceful_exit()
        else:
            with open(self._pairing_file, "r") as f:
                device.set_credentials(pyatv.Protocol.AirPlay, f.read())

    @staticmethod
    async def _scan_for_devices(atv_settings: dict) -> List[pyatv.interface.BaseConfig]:
        """ Scan for Apple TVs and return a list of devices."""
        async def _perform_scan(loop, identifier=None):
            name = atv_settings.get('name') or "Apple TV's"
            print(f"Discovering {name} on network...")
            scan_result = await pyatv.scan(loop, identifier=identifier, protocol=pyatv.Protocol.AirPlay)
            return list(
                filter(lambda x: x.device_info.operating_system == pyatv.const.OperatingSystem.TvOS, scan_result))

        atv_id = atv_settings.get('id')
        devices = await _perform_scan(asyncio.get_event_loop(), atv_id)
        if atv_id and not devices:
            warnings.warn(f"Saved Apple TV with identifier {atv_id} could not be found, rescanning...")
            devices = await _perform_scan(asyncio.get_event_loop())
        if not devices:
            logging.error("No Apple TV's found on network")
            _raise_graceful_exit()
        return devices

    @staticmethod
    def _choose_device(devices: list) -> pyatv.interface.BaseConfig:
        """ Choose a device from a list of devices."""
        if len(devices) == 1:
            return devices[0]
        print("Found multiple Apple TVs, please choose one:")
        for i, device in enumerate(devices):
            print(f"{i + 1}: {device.name}")
        choice = int(input("Enter number: "))
        return devices[choice - 1]

    def _read_settings(self) -> dict:
        """ Reads the settings from the config file."""
        return yaml.load(open(self._config_file, 'r'), Loader=yaml.FullLoader) or {}
