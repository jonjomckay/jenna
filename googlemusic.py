import os
import sys
import pyid3lib
import urllib
import cStringIO

from gmusicapi import Webclient, Mobileclient
from urlparse import urlparse, parse_qsl

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

	def search(self, query, type):
		if self.is_authenticated():
			results = self.mobileclient.search_all_access(query)[type + '_hits']

			return results

	def get_track(self, store_id):
		return self.mobileclient.get_track(store_id)

	def save_stream(self, track, destination):
		if self.is_authenticated():
			with open(destination, 'w+b') as f:
				# f.write(self.webclient.get_stream_audio(track.get('storeId')))

				urls = self.webclient.get_stream_urls(track.get('storeId'))

				if len(urls) == 1:
					f.write(self.webclient.session._rsession.get(urls[0]).content)

				range_pairs = [[int(s) for s in val.split('-')]
							   for url in urls
							   for key, val in parse_qsl(urlparse(url)[4])
							   if key == 'range']

				stream_pieces = []

				for url, (start, end) in zip(urls, range_pairs):
					f.truncate(start)
					f.seek(0, 2)
					audio = self.webclient.session._rsession.get(url).content
					f.write(audio)

			print 'saved'

			tag = pyid3lib.tag(destination)
			tag.title = track.get('title').__str__()
			tag.artist = track.get('artist').__str__()
			tag.album = track.get('album').__str__()
			tag.year = track.get('year')
			tag.track = (track.get('discNumber'), track.get('trackNumber'))
			tag.band = track.get('albumArtist').__str__()
			tag.append({
				'frameid': 'APIC',
				'mimetype': 'image/jpeg',
				'picturetype': 3,
				'data': urllib.urlopen(track.get('albumArtRef')[0].get('url')).read()
			})
			tag.update()

			print 'tagged'