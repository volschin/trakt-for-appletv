from atv.playstatus_tracker import PlayStatusTracker


class ScrobblingProtocol(PlayStatusTracker):

    def __init__(self, atv, conf):
        super().__init__(atv, conf)

    def playstatus_changed(self):
        print(self.curr_state)
        return
