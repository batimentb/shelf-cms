import httplib2
from apiclient.discovery import build
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run

import datetime

def pretty(d, indent=0):
   for key, value in d.iteritems():
      print '\t' * indent + str(key)
      if isinstance(value, dict):
         pretty(value, indent+1)
      else:
         print '\t' * (indent+1) + str(value)

class Analytics():
	DEFAULT_DIR = 'google-analytics'

	# The file with the OAuth 2.0 Client details for authentication and authorization.
	DEFAULT_CLIENT_SECRETS = 'client_secrets.json'

	# A helpful message to display if the CLIENT_SECRETS file is missing.
	DEFAULT_MISSING_CLIENT_SECRETS_MESSAGE = '%s is missing' % DEFAULT_CLIENT_SECRETS	

	# A file to store the access token
	DEFAULT_TOKEN_FILE_NAME = 'analytics.dat'

	DEFAULT_START = datetime.date.today() - datetime.timedelta(days=30)
	DEFAULT_END = datetime.date.today() 

	def __init__(self, app=None):
		if (app):
			self.init_app(app)
		self.profile = None
		self.analytics = None

		self.TOKEN_FILE_NAME = self.DEFAULT_TOKEN_FILE_NAME
		self.CLIENT_SECRETS = self.DEFAULT_CLIENT_SECRETS
		self.MISSING_CLIENT_SECRETS_MESSAGE = self.DEFAULT_MISSING_CLIENT_SECRETS_MESSAGE


	def prepare(self):
		self.http = httplib2.Http()

		storage = Storage(self.TOKEN_FILE_NAME)
		credentials = storage.get()

		if credentials is None or credentials.invalid:
			FLOW = flow_from_clientsecrets(self.CLIENT_SECRETS,
				scope='https://www.googleapis.com/auth/analytics.readonly',
				message=self.MISSING_CLIENT_SECRETS_MESSAGE)
			credentials = run(FLOW, storage) 

		self.http = credentials.authorize(self.http)
		self.analytics = build('analytics', 'v3', http=self.http)

	def init_app(self, app):
		self.TOKEN_FILE_NAME = self.DEFAULT_TOKEN_FILE_NAME
		self.CLIENT_SECRETS = self.DEFAULT_CLIENT_SECRETS
		self.MISSING_CLIENT_SECRETS_MESSAGE = self.DEFAULT_MISSING_CLIENT_SECRETS_MESSAGE

	def get_stats(self, metrics=None, dimensions=None, start=None, end=None):
		if not self.profile:
			self.set_profile()

		start = start if start else self.DEFAULT_START
		end = end if end else self.DEFAULT_END

		if not (metrics or dimensions):
			raise ValueError

		raw_res = self.analytics.data().ga().get(
			ids='ga:' + self.profile,
			start_date=str(start),
			end_date=str(end),
			metrics=','.join(['ga:%s' % m for m in metrics]) if metrics else None,
			dimensions=','.join(['ga:%s' % m for m in dimensions]) if dimensions else None).execute()

		results = {}

		for row in raw_res.get('rows'):
			ptr = results
			if dimensions:
				for i in range(len(dimensions)):
					dim = dimensions[i]
					if row[i] not in ptr:
						ptr[row[i]] = {}
					ptr = ptr[row[i]]
			
			for i in range(len(metrics)):
				met = metrics[i]
				ptr[met] = row[i+len(dimensions) if dimensions else i]

		return results


		

		

	def set_profile(self):
		try:
			# Get a list of all Google Analytics accounts for this user
			accounts = self.analytics.management().accounts().list().execute()

			if accounts.get('items'):
				# Get the first Google Analytics account
				self.account = accounts.get('items')[0].get('id')

				# Get a list of all the Web Properties for the first account
				webproperties = self.analytics.management().webproperties().list(accountId=self.account).execute()

				if webproperties.get('items'):
					# Get the first Web Property ID
					self.web_property = webproperties.get('items')[0].get('id')

					# Get a list of all Profiles for the first Web Property of the first Account
					profiles = self.analytics.management().profiles().list(
							accountId=self.account,
							webPropertyId=self.web_property).execute()

					if profiles.get('items'):
						self.profile = profiles.get('items')[0].get('id')
		except:
			pass

