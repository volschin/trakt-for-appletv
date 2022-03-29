from typing import Optional
from pyatv.interface import Playing, App
from pyatv.protocols.mrp.protobuf import ContentItemMetadata
from helpers.better_named_tuple import make_named_tuple_type
from atv.tv_protocol import TVProtocol


class PlayStatusTracker(TVProtocol):
    now_playing_metadata: Optional[ContentItemMetadata]
    app: Optional[App]
    playstatus: Optional[Playing]

    def __init__(self, atv, conf):
        super().__init__(atv, conf)
        self.now_playing_metadata = None
        self.app = None
        self.playstatus = None
        self.prev_state = None
        self.save_state = make_named_tuple_type('playstatus', 'app')

    def playstatus_update(self, updater, playstatus: Playing):
        super().playstatus_update(updater, playstatus)
        self.prev_state = self.save_state.from_object(self)
        self.playstatus = playstatus
        self.app = self.atv.metadata.app
        self.now_playing_metadata = updater.psm.playing.metadata
        self.playstatus_changed()

    def playstatus_changed(self):
        raise NotImplementedError
