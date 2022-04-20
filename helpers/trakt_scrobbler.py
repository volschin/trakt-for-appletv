import os
import pickle
from datetime import datetime
from json import JSONDecodeError

import pytz as pytz
import requests
from dateutil.parser import parse
from requests.auth import HTTPBasicAuth
from trakt import Trakt


class TraktScrobbler:

    def __init__(self):
        # TODO: fix this init not being called
        self.watched_percent = 90
        self.currently_scrobbling = None
        self.auth_file = None

    def init_trakt(self):
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
        self.currently_scrobbling = kwargs
        try:
            Trakt['scrobble'].start(
                **kwargs
            )
            self.print_info(f'Started {kwargs}', scrobble=True)
        except Exception as e:
            print(e)

    class BearerAuth(requests.auth.AuthBase):
        def __init__(self, token):
            self.token = token

        def __call__(self, r):
            r.headers['Content-Type'] = 'application/json'
            r.headers["Authorization"] = "Bearer " + self.token
            r.headers['trakt-api-version'] = '2'
            r.headers['trakt-api-key'] = Trakt.configuration.defaults.data['client.id']

            return r

    async def stop_scrobbling(self, safe=False):
        if safe and self.currently_scrobbling is None:
            return
        current = await self.fetch_current_scrobble()
        self.currently_scrobbling = None
        if current:
            progress = current.get('progress')
            if progress and progress > self.watched_percent:
                Trakt['scrobble'].stop(
                    **current
                )
                self.print_info(f'Stopped {current}', scrobble=True)
            elif progress:
                Trakt['scrobble'].pause(
                    **current
                )
                self.print_info(f'Paused {current}', scrobble=True)

    async def fetch_current_scrobble(self):
        settings = Trakt['users/settings'].get()
        try:
            data = requests.get(
                url='https://api.trakt.tv/users/{}/watching'.format(settings['user']['username']),
                auth=self.BearerAuth(Trakt.configuration.defaults.data['oauth.token'])
            ).json()
        except JSONDecodeError:
            return None

        started_at = parse(data['started_at'])
        expires_at = parse(data['expires_at'])
        now = datetime.now(pytz.utc)
        return {
            'movie': data.get('movie'),
            'show': data.get('show'),
            'episode': data.get('episode'),
            'progress': (now-started_at).seconds / (expires_at-started_at).seconds * 100
        }

    @staticmethod
    def print_info(message: str, scrobble: bool = False):
        color = '\033[96m' if not scrobble else '\033[92m'
        end = '\033[0m'
        begin = 'HANDLE: ' if not scrobble else 'SCROBBLE: '
        print(f"{color}{begin}{message}{end}")
