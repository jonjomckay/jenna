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
from threads import DownloadThread, FetchThread, SearchThread

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