import os
import pickle
from abc import ABC
from datetime import datetime, timedelta

import pytz as pytz
from trakt import Trakt

from atv.playstatus_tracker import PlayStatusTracker


class TraktScrobbler(PlayStatusTracker, ABC):

    def __init__(self):
        self.watched_percent = 90
        self.currently_scrobbling = None
        self.auth_file = 'data/trakt.auth'
        Trakt.configuration.defaults.client(
            id='34ea1338c16b79f0067b31f4a8e6a35a5e6b9ccc6476e4e7e7300f059b4514d7',
            secret='8453ad791caa51872a2fd9d18b273f55348297cf14885dbc94cb91123ce08d18'
        )
        Trakt.configuration.defaults.http(retry=True)
        Trakt.on('oauth.token_refreshed', self.on_trakt_token_refreshed)
        self.authenticate_trakt()
        super().__init__()

    def authenticate_trakt(self):
        if os.path.exists(self.auth_file):
            response = pickle.load(open(self.auth_file, 'rb'))
        else:
            print('Navigate to %s' % Trakt['oauth'].authorize_url('urn:ietf:wg:oauth:2.0:oob'))
            pin = input('Authorization code: ')
            response = Trakt['oauth'].token_exchange(pin, 'urn:ietf:wg:oauth:2.0:oob')
            self.on_trakt_token_refreshed(response)
        Trakt.configuration.defaults.oauth.from_response(response, refresh=True)

    def on_trakt_token_refreshed(self, response):
        pickle.dump(response, open(self.auth_file, 'wb'))

    async def start_scrobbling(self, **kwargs):
        now = datetime.now(pytz.utc)
        secs_left = self.curr_state.total_time - self.curr_state.position
        started_at = now - timedelta(seconds=self.curr_state.position)
        expires_at = now + timedelta(seconds=secs_left)
        self.currently_scrobbling = kwargs, started_at, expires_at
        try:
            Trakt['scrobble'].start(
                **kwargs
            )
            await self.print_info(f'Started {kwargs}', prefix='TRAKT', success=True)
        except Exception as e:
            await self.print_warning(f'Failed to start scrobble {e}')

    async def stop_scrobbling(self, safe=False):
        if self.currently_scrobbling is None:
            await self.print_debug('No scrobble to stop', prefix='TRAKT')
            return
        current = await self.calculate_current_scrobble()
        self.currently_scrobbling = None
        if current:
            progress = current.get('progress')
            if progress and progress > self.watched_percent:
                Trakt['scrobble'].stop(
                    **current
                )
                await self.print_info(f'Stopped {current}', prefix='TRAKT', success=True)
            elif progress:
                Trakt['scrobble'].pause(
                    **current
                )
                await self.print_info(f'Paused {current}', prefix='TRAKT', success=True)

    async def calculate_current_scrobble(self):
        kwargs, started_at, expires_at = self.currently_scrobbling
        now = datetime.now(pytz.utc)
        progress = (now - started_at).seconds / (expires_at - started_at).seconds * 100
        kwargs['progress'] = round(progress, 1)
        return kwargs

