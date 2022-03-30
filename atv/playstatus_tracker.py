from dataclasses import dataclass, field
from typing import Optional
from pyatv import const
from pyatv.interface import Playing, App
from pyatv.protocols.mrp.protobuf import ContentItemMetadata
from atv.tv_protocol import TVProtocol
import time


@dataclass(frozen=True)
class PlaybackState:
    app: Optional[str] = None
    metadata: Optional[ContentItemMetadata] = field(repr=False, default=None, compare=False, hash=False)
    device_state: const.DeviceState = field(default=const.DeviceState.Idle, compare=True, hash=False),
    title: Optional[str] = None,
    total_time: Optional[int] = None,
    position: Optional[int] = field(default=0, compare=False, hash=False),
    series_name: Optional[str] = None,
    season_number: Optional[int] = None,
    episode_number: Optional[int] = None,
    content_identifier: Optional[str] = None,
    time: float = field(repr=False, default=0, compare=False, hash=False)

    def __eq__(self, other):
        return (self.device_state == other.device_state and
                self.title == other.title and
                self.app == other.app and
                self.total_time == other.total_time and
                self.series_name == other.series_name and
                self.season_number == other.season_number and
                self.episode_number == other.episode_number and
                self.content_identifier == other.content_identifier)

    def has_changed_from(self, obj) -> bool:
        return self != obj or \
               (isinstance(obj, PlaybackState) and (self.position - obj.position) - (self.time - obj.time) > 0)


class PlayStatusTracker(TVProtocol):
    curr_state: PlaybackState
    prev_state: PlaybackState

    def __init__(self, atv, conf):
        super().__init__(atv, conf)
        self.curr_state = PlaybackState()
        self.prev_state = PlaybackState()

    def playstatus_update(self, updater, playstatus: Playing):
        # super().playstatus_update(updater, playstatus)
        self.prev_state = self.curr_state
        self.curr_state = self._make_state(updater, playstatus)
        if self.curr_state.has_changed_from(self.prev_state):
            self.playstatus_changed()

    def _make_state(self, updater, playstatus: Playing):
        return PlaybackState(app=self.atv.metadata.app.identifier if self.atv.metadata.app else None,
                             metadata=updater.psm.playing.metadata,
                             device_state=playstatus.device_state,
                             title=playstatus.title,
                             total_time=playstatus.total_time,
                             position=playstatus.position,
                             series_name=playstatus.series_name,
                             season_number=playstatus.season_number,
                             episode_number=playstatus.episode_number,
                             content_identifier=playstatus.content_identifier,
                             time=time.monotonic())

    def playstatus_changed(self):
        raise NotImplementedError
