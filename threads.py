import os
import math
import datetime
import threading

from gi.repository import GObject
from time import sleep

class FetchThread(threading.Thread):
	def __init__(self, app, track, destination):
		threading.Thread.__init__(self)

		self.app = app
		self.track = track
		self.destination = destination

	def run(self):
		try:	
			self.app.api.save_stream(self.track, self.destination)
		except Exception, e:
			print e

	def fetch(self, track, destination):
		self.app.api.save_stream(track, destination)

class DownloadThread(threading.Thread):
	def __init__(self, app, iter):
		threading.Thread.__init__(self)

		self.app = app
		self.iter = iter

	def run(self):
		try:
			self.app.status_bar.push(self.app.status_bar_context_id, 'Downloading ' + self.app.download_list_store.get_value(self.iter, 0) + '...')
			store_id = self.app.download_list_store.get_value(self.iter, 4)

			track = self.app.api.get_track(store_id)

			filename = track.get('artist') + ' - ' + track.get('album') + ' - ' + track.get('trackNumber').__str__() + ' - '+ track.get('title') + '.mp3'
			destination = os.path.join(self.app.settings.get('download_directory'), filename)

			fetch_thread = FetchThread(self.app, track, destination)
			fetch_thread.start()

			while fetch_thread.isAlive():
				sleep(0.4)
				
				percent = int(100 / float(track.get('estimatedSize')) * os.path.getsize(destination))

				if percent > 100:
					percent = 100

				self.app.download_list_store[self.iter][5]
				self.app.download_list_store[self.iter][-1] = percent
		except Exception, e:
			print e


class SearchThread(threading.Thread):
	def __init__(self, app, query, type):
		threading.Thread.__init__(self)

		self.app = app
		self.query = query
		self.type = type

	def bytes_to_human(self, size):
		size = int(size)
		size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
		i = int(math.floor(math.log(size,1024)))
		p = math.pow(1024,i)
		s = round(size/p,2)
		if (s > 0):
			return '%s %s' % (s,size_name[i])
		else:
			return '0B'

	def run(self):
		try:
			self.app.status_bar.push(self.app.status_bar_context_id, 'Searching Google Music for: ' + self.query + '...')
			results = self.app.api.search(self.query, 'song')
			GObject.idle_add(self.fill_results, results)			
		except Exception, e:
			print e

	def fill_results(self, results):
		store = self.app.track_list_store
		store.clear()

		for track in results:
			store.append([
				track.get('track').get('trackNumber'),
				track.get('track').get('title'),
				track.get('track').get('artist'),
				track.get('track').get('album'),
				str(datetime.timedelta(milliseconds=int(track.get('track').get('durationMillis')))),
				self.bytes_to_human(track.get('track').get('estimatedSize')),
				track.get('track').get('year'),
				track.get('track').get('storeId'),
				int(track.get('track').get('estimatedSize'))
			])
		
		self.app.status_bar.push(self.app.status_bar_context_id, 'Found ' + len(results).__str__() + ' results!')

		self.app.results_tree_view.set_model(store)
