from __future__ import division

import signal
import datetime
import math
import threading
import os
import sys
import sched
import time

from gi.repository import Gtk, GObject
from time import sleep
from tempfile import mkstemp
from gmusicapi import Webclient, Mobileclient
from settings import Settings
from googlemusic import GoogleMusic

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

class Alfonso:
	def __init__(self):
		GObject.threads_init()

		self.settings = Settings()
		self.api = GoogleMusic()

		builder = Gtk.Builder()
		builder.add_from_file('ui/main.glade')
		builder.connect_signals(self)

		self.loading_modal = builder.get_object('loadingModal')
		self.loading_modal_label = builder.get_object('loadingModalLabel')

		self.window = builder.get_object('mainWindow')

		self.notebook = builder.get_object('mainWindowNotebook')

		self.status_bar = builder.get_object('statusBar')
		self.status_bar_context_id = self.status_bar.get_context_id('search')

		self.preferences_dialog = builder.get_object('preferencesDialog')
		self.preferences_username_entry = builder.get_object('preferencesUsernameEntry')
		self.preferences_password_entry = builder.get_object('preferencesPasswordEntry')
		self.preferences_directory_chooser = builder.get_object('preferencesDirectoryChooser')

		self.search_entry = builder.get_object('searchEntry')

		self.track_list_store = builder.get_object('trackListStore')
		self.download_list_store = builder.get_object('downloadListStore')

		self.results_tree_view = builder.get_object('resultsTreeView')
		
		self.window.show_all()

	def on_preferences_dialog_show(self, dialog):
		self.preferences_username_entry.set_text(self.settings.get('username'))
		self.preferences_password_entry.set_text(self.settings.get('password'))
		self.preferences_directory_chooser.set_filename(self.settings.get('download_directory'))

	def on_preferences_ok_clicked(self, button):
		username = self.preferences_username_entry.get_text()
		password = self.preferences_password_entry.get_text()
		download_directory = self.preferences_directory_chooser.get_filename()

		self.settings.set('username', username)
		if password != self.settings.get('password'):
			self.settings.set('password', password.encode('base64'))
		self.settings.set('download_directory', download_directory)

		self.preferences_dialog.hide()

	def on_preferences_cancel_clicked(self, button):
		self.preferences_dialog.hide()

	def on_main_show(self, window):
		# check for login details
		# make async
		self.status_bar.push(self.status_bar_context_id, 'Logging into Google Music...')

		try:
			self.api.login(self.settings.get('username'), self.settings.get('password').decode('base64'))

			self.status_bar.push(self.status_bar_context_id, 'Logged in!')
		except Exception, e:
			self.status_bar.push(self.status_bar_context_id, e.message)

	def on_main_delete_window(self, *args):
		Gtk.main_quit(*args)

	def on_main_search_toolitem_clicked(self, button):
		self.notebook.set_current_page(0)

	def on_main_downloads_toolitem_clicked(self, button):
		self.notebook.set_current_page(1)

	def on_main_preferences_toolitem_clicked(self, button):
		self.preferences_dialog.show_all()

	def on_main_search_button_clicked(self, button):
		if self.search_entry.get_text() != '':
			search_thread = SearchThread(self, self.search_entry.get_text(), 'song')
			search_thread.start()

	def on_main_tracklist_activated(self, treeview, path, column):
		store = treeview.get_model()

		treeiter = store.get_iter(path)

		# only append if not already in list

		row = self.download_list_store.append([
			store.get_value(treeiter, 1),
			store.get_value(treeiter, 2),
			store.get_value(treeiter, 3),
			store.get_value(treeiter, 5),
			store.get_value(treeiter, 7),
			store.get_value(treeiter, 8),
			0
		])

		download_thread = DownloadThread(self, row)
		download_thread.start()

		# print self.download_list_store.get_value(row, 4)

		# self.api.save_stream(store_id, self.preferences_directory_chooser.get_filename())

signal.signal(signal.SIGINT, signal.SIG_DFL)

app = Alfonso()

Gtk.main()