import asyncio
import sys
from pyatv import connect, scan
from pyatv.const import Protocol, FeatureState, FeatureName
from helpers.graceful_exit import GracefulExit, cancel_tasks
from scrobbling_protocol import ScrobblingProtocol


async def _play_handler():
    device = {
        "name": "Home Theatre",
        "identifiers": {"F0:B3:EC:6A:92:87"},
        "credentials": {
            Protocol.AirPlay: "e83be0738cb27cc1007fe46b1054f4dea5a3a0544698e4ce14cef7f8e02d652e"
                              ":273d04db1f5dca43e6eb6a7bf7494b000bf6088a63fa5b71ad42777158ebb535"
                              ":46413330373530382d433042322d343644382d394533462d314234383931324244383031"
                              ":38343934323836322d326332382d343931342d393365332d613837313238663731356139",
        },
    }

    """Find a device and print what is playing."""
    print(f"Discovering {device['name']} on network...")
    loop = asyncio.get_event_loop()
    confs = await scan(loop, identifier=device["identifiers"])

    if not confs:
        print("Device could not be found", file=sys.stderr)
        return

    conf = confs[0]
    for protocol, credentials in device["credentials"].items():
        conf.set_credentials(protocol, credentials)

    print(f"Connecting to {conf.address}")
    atv = await connect(conf, loop)

    if not atv.features.in_state(FeatureState.Available, FeatureName.PushUpdates):
        print("Push updates are not supported (no protocol supports it)")
        return 1

    listener = ScrobblingProtocol(atv, conf)
    await listener.setup()

    # sleep forever by 1 hour intervals,
    # on Windows before Python 3.8 wake up every 1 second to handle
    # Ctrl+C smoothly
    try:
        if sys.platform == "win32" and sys.version_info < (3, 8):
            delay = 1
        else:
            delay = 3600

        while True:
            await asyncio.sleep(delay)
    finally:
        await listener.cleanup()


def main():
    """Application start here."""
    loop = asyncio.get_event_loop()
    main_task = loop.create_task(
        _play_handler()
    )
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main_task)
    except (GracefulExit, KeyboardInterrupt):  # pragma: no cover
        pass
    finally:
        cancel_tasks({main_task}, loop)
        cancel_tasks(asyncio.all_tasks(loop), loop)
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        asyncio.set_event_loop(None)
        print("Done")


if __name__ == "__main__":
    sys.exit(main())
