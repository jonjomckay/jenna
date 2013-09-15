import urllib

from gmusicapi import Webclient, Mobileclient
from urlparse import urlparse, parse_qsl
from mutagen import easyid3, id3, mp3

class GoogleMusic(object):
    def __init__(self):
        self.webclient = Webclient()
        self.mobileclient = Mobileclient()

    def is_authenticated(self):
        if self.webclient.is_authenticated():
            if self.mobileclient.is_authenticated():
                return True

        return False

    def login(self, username, password):
        if not self.is_authenticated():
            try:
                self.mobileclient.login(username, password)
                self.webclient.login(username, password)
            except:
                raise Exception('Couldn\'t log into Google Music')

    def search(self, query, kind):
        if self.is_authenticated():
            results = self.mobileclient.search_all_access(query)[kind + '_hits']

            return results

    def get_track(self, store_id):
        return self.mobileclient.get_track_info(store_id)

    def save_stream(self, track, destination):
        if self.is_authenticated():
            with open(destination, 'w+b') as stream_file:
                urls = self.webclient.get_stream_urls(track.get('storeId'))

                if len(urls) == 1:
                    stream_file.write(self.webclient.session._rsession.get(urls[0]).content)

                range_pairs = [[int(s) for s in val.split('-')]
                               for url in urls
                               for key, val in parse_qsl(urlparse(url)[4])
                               if key == 'range']

                for url, (start, end) in zip(urls, range_pairs):
                    stream_file.truncate(start)
                    stream_file.seek(0, 2)
                    audio = self.webclient.session._rsession.get(url).content
                    stream_file.write(audio)

            tag = easyid3.EasyID3()
            tag['title'] = track.get('title').__str__()
            tag['artist'] = track.get('artist').__str__()
            tag['album'] = track.get('album').__str__()
            tag['date'] = track.get('year').__str__()
            tag['discnumber'] = track.get('discNumber').__str__()
            tag['tracknumber'] = track.get('trackNumber').__str__()
            tag['performer'] = track.get('albumArtist').__str__()
            tag.save(destination)

            tag = mp3.MP3(destination)
            tag.tags.add(
                id3.APIC(3, 'image/jpeg', 3, 'Front cover', urllib.urlopen(track.get('albumArtRef')[0].get('url')).read())
            )
            tag.save()
