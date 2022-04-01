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
    device_state: const.DeviceState = const.DeviceState.Idle,
    title: Optional[str] = None,
    total_time: Optional[int] = None,
    position: Optional[int] = field(default=0, compare=False, hash=False),
    series_name: Optional[str] = None,
    season_number: Optional[int] = None,
    episode_number: Optional[int] = None,
    content_identifier: Optional[str] = None,
    time: float = field(repr=False, default=0, compare=False, hash=False)

    def __eq__(self, other):
        return (self.title == other.title and
                self.device_state == other.device_state and
                self.app == other.app and
                self.total_time == other.total_time and
                self.series_name == other.series_name and
                self.season_number == other.season_number and
                self.episode_number == other.episode_number and
                self.content_identifier == other.content_identifier)

    def is_playing(self) -> bool:
        return self.device_state == const.DeviceState.Playing

    def has_valid_metadata(self) -> bool:
        return (self.title or
                self.series_name or
                self.season_number or
                self.episode_number or
                self.device_state == const.DeviceState.Idle)


class PlayStatusTracker(TVProtocol):
    curr_state: PlaybackState
    prev_state: PlaybackState

    def __init__(self, atv, conf):
        super().__init__(atv, conf)
        self.curr_state = PlaybackState(position=0, time=0)
        self.prev_state = PlaybackState(position=0, time=0)

    def playstatus_update(self, updater, playstatus: Playing):
        # super().playstatus_update(updater, playstatus)
        new_state = self._make_state(updater, playstatus)
        if new_state.has_valid_metadata():
            self.prev_state = self.curr_state
            self.curr_state = new_state
            self._register_change_notification()
        else:
            self.print_warning(new_state)

    def _register_change_notification(self):
        if self._states_differ() or self._positions_differ():
            self.playstatus_changed()
        else:
            self.print_warning(self.curr_state, failure=True)

    def _states_differ(self) -> bool:
        """Compares equality of previous and current playback states ignoring position, time, and metadata properties.
        :return: True if states differ, False otherwise
        """

        return self.prev_state != self.curr_state

    def _positions_differ(self, sec_threshold=1) -> bool:
        """Determines if playback position differs from the time passed if both prev and curr states are playing
        otherwise if playback position difference is more than the sec_threshold
        intended to reduce meaningless playstatus updates some apps send

        :param sec_threshold: amount of seconds required before difference is registered
        :return:
        """

        pos_diff = abs(self.curr_state.position - self.prev_state.position)
        if self.curr_state.is_playing() and self.prev_state.is_playing():
            time_passed = int(self.curr_state.time - self.prev_state.time)
            return pos_diff - (time_passed + sec_threshold) > 0
        return pos_diff - sec_threshold > 0

    def _make_state(self, updater, playstatus: Playing) -> PlaybackState:
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

    @staticmethod
    def print_warning(message, failure: bool = False):
        color = '\033[93m' if not failure else '\033[91m'
        end = '\033[0m'
        # print(f"{color}{message}{end}")
