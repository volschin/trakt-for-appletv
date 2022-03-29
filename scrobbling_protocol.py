from typing import Optional
from pyatv.interface import Playing, App
from pyatv.protocols.mrp.protobuf import ContentItemMetadata
from helpers.better_named_tuple import make_named_tuple_type
from atv.playstatus_tracker import PlayStatusTracker


class ScrobblingProtocol(PlayStatusTracker):

    def __init__(self, atv, conf):
        super().__init__(atv, conf)

    def playstatus_changed(self):
        return
