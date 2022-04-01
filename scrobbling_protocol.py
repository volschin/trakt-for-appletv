import time

from atv.playstatus_tracker import PlayStatusTracker


class ScrobblingProtocol(PlayStatusTracker):

    def __init__(self, atv, conf):
        super().__init__(atv, conf)
        self.app_handlers = {'com.apple.TVShows': self.handle_tvshows,
                             'com.apple.TVWatchList': self.handle_tv_app,
                             'com.apple.TVMovies': self.handle_movies,
                             'com.netflix.Netflix': self.handle_netflix}

    def playstatus_changed(self):
        print(self.curr_state)
        time.sleep(1)
        return

    def handle_tvshows(self):
        return

    def handle_tv_app(self):
        return

    def handle_movies(self):
        return

    def handle_netflix(self):
        return
