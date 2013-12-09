# -*- coding: utf-8 -*-

from wtforms.fields import TextField
from wtforms.widgets import TextInput
from flask.ext.admin.model.form import converts
from shelf.model.base import shelf_computed_models, db

import os.path as op
import os

from flask import render_template

class LocalizedTextWidget(TextInput):
	def __call__(self, *args, **kwargs):
		return render_template("shelf-admin/field/localized-string.html", id=args[0].id, data=args[0].data)

_unset_value = object()

class LocalizedTextField(TextField):
	widget = LocalizedTextWidget()
	langs = ("en", "fr")

	def process(self, formdata, data=_unset_value):
		"""
		Process incoming data, calling process_data, process_formdata as needed,
		and run filters.

		If `data` is not provided, process_data will be called on the field's
		default.

		Field subclasses usually won't override this, instead overriding the
		process_formdata and process_data methods. Only override this for
		special advanced processing, such as when a field encapsulates many
		inputs.
		"""
		self.process_errors = []
		if data is _unset_value:
			try:
				data = self.default()
			except TypeError:
				data = self.default

		self.object_data = data

		try:
			self.process_data(data)
		except ValueError as e:
			self.process_errors.append(e.args[0])

		if formdata:
			try:
				self.raw_data = []
				for lang in self.langs:
					if self.name+"-"+lang in formdata:
						self.raw_data.append(formdata.getlist(self.name+"-"+lang)[0])
					
				self.process_formdata(self.raw_data)
			except ValueError as e:
				self.process_errors.append(e.args[0])

		for filter in self.filters:
			try:
				self.data = filter(self.data)
			except ValueError as e:
				self.process_errors.append(e.args[0])

	def process_formdata(self, valuelist):
		self.data = {}
		for i in range(len(valuelist)):
			self.data[self.langs[i]] = valuelist[i]
		print self.data

	def process_data(self, value):
		self.data = {}
		if value:
			self.data[value.lang] = value.value
			for translation in value.trad:
				self.data[translation.lang] = translation.value
		print self.data

	def populate_obj(self, obj, name):
		if getattr(obj, name) is None:
			setattr(obj, name, getattr(obj.__class__, name).mapper.class_(lang="en", value=self.data["en"]))
			db.session.add(getattr(obj, name))
		else:
			getattr(obj, name).value = self.data["en"]

		lstring = getattr(obj, name)
		for lang in self.data:
			if lang == "en":
				continue
			print lang, self.data[lang]
			
			res = None
			for t in lstring.trad:
				if t.lang == lang:
					res = t
					break

			if res is None:
				lstring.trad.append(getattr(obj.__class__, name).mapper.class_(lang=lang, value=self.data[lang]))
			else:
				res.value = self.data[lang]

		#super(LocalizedTextField, self).populate_obj(obj, name)

