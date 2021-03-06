from datetime import date
import json
import csv
import copy
from enum import Enum
from typing import Dict, OrderedDict
from queue import PriorityQueue
import heapq


class Date:
	def __init__(self, date: str, confirmed, deaths, recovered):
		self.date = date
		self.confirmed = confirmed
		self.deaths = deaths
		self.recovered = recovered
		self.json = {}

	def __repr__(self):
		return "Date: % s, Confirmed: % s, Deaths: % s, Recovered: % s" % (
			self.date,
			self.confirmed,
			self.deaths,
			self.recovered,
		)

	def init_reprJSON(self):
		self.json = dict(
			Confirmed=self.confirmed, Deaths=self.deaths, Recovered=self.recovered
		)
		return self.json

	def reprJSON(self):
		return self.json


class State:
	def __init__(self, state_name, country_name):
		self.state_name = state_name
		self.country_name = country_name
		self.total_confirmed = 0
		self.total_deaths = 0
		self.total_recovered = 0
		self.dates = {}
		self.json = {}

	def __repr__(self):
		return "% s, dates: %s" % (self.state_name, self.dates)

	def __eq__(self, other):
		return self.state_name == other.state_name

	def init_reprJSON(self):
		# turns the date objects into json but does not save,
		# this is to prevent calling reprJSON once it was turned into a dict
		# so whenever this is called it might take some take to convert all of it into json
		temp_dates = {}
		for k, v in self.dates.items():
			temp_dates[k] = v.init_reprJSON()

		self.json = dict(
			Country=self.country_name,
			State=self.state_name,
			Total_Confirmed=self.total_confirmed,
			Total_Deaths=self.total_deaths,
			Total_Recovered=self.total_recovered,
			Dates=temp_dates,
		)

		return self.json

	def reprJSON(self):
		return self.json


# Every single province/state after merging all the dates togethers
# TODO: Debating on whether to have a member that is called dates_json, which is a dict and call all the reprJSON
# TODO: find a way for state searches and states' total confirmed cases and etc..
class Country:
	def __init__(self, country_name):
		self.country_name = country_name
		self.states = {}
		self.total_confirmed = 0
		self.total_deaths = 0
		self.total_recovered = 0
		# Some countries don't have a state/province, but if they do we put it into the states list and leave dates in country empty
		# Stores date objs
		self.dates = {}
		self.json = {}

	def __repr__(self):
		return "country name is % s, states are % s, dates are % s" % (
			self.country_name,
			self.states,
			self.dates,
		)

	# TODO: Cache
	def init_reprJSON(self):
		temp_states = {}
		for k, v in self.states.items():
			temp_states[k] = v.init_reprJSON()

		# turns the date objects into json but does not save,
		# this is to prevent calling reprJSON once it was turned into a dict
		# so whenever this is called it might take some take to convert all of it into json
		temp_dates = {}
		for k, v in self.dates.items():
			temp_dates[k] = v.init_reprJSON()

		self.json = dict(
			Country=self.country_name,
			States=temp_states,
			Total_Confirmed=self.total_confirmed,
			Total_Deaths=self.total_deaths,
			Total_Recovered=self.total_recovered,
			Dates=temp_dates,
		)

		return self.json

	def reprJSON(self):
		return self.json

	def __lt__(self, other):
		# (country.total_deaths, country_obj)
		selfPriority = self.total_deaths
		otherPriority = other.total_deaths
		return selfPriority < otherPriority


class Fields(Enum):
	SNo = 0
	ObservationDate = 1
	State = 2
	Country = 3
	LastUpdate = 4
	Confirmed = 5
	Deaths = 6
	Recovered = 7


# TODO: add range based search
class DataLayer:
	def __init__(self):
		# key = country_name : value = country_obj
		self.countries_data = {}
		# helper list to help us sort
		self.countries_list = []
		# holds all the country objects created(kinda like a bootleg database)
		self.country_objects = []
		# used to calcualte percentage of cases for a country, country total / global total
		self.global_total_types = {
			"Total_Confirmed": 0,
			"Total_Deaths": 0,
			"Total_Recovered": 0,
		}
		self.top_5_death_pq = PriorityQueue()
		self.only_country_analytic_pq = PriorityQueue()
		self.top_5_death_heap = []
		self.top_5_confirmed_heap = []

	def test(self):
		print("works")

	def load_json(self):
		# Testing relative path stuff
		# import os

		# cwd = os.getcwd()  # Get the current working directory (cwd)
		# files = os.listdir(cwd)  # Get all the files in that directory
		# print("Files in %r: %s" % (cwd, files))

		with open("api/data_layer/countries.json") as file:
			data = json.load(file)

		self.countries_list = data["Countries/Regions"]
		# print(self.countries_list)

	# here we read the original copy of the csv, but after the backup we need to read the copy
	def initLoadCSV(self, csv_name: str):
		countries_dict = {}
		self.load_json()

		for country in self.countries_list:
			countries_dict[country] = []

		with open(csv_name, "r") as infile:
			for line in infile.readlines():
				row_values = line.split(",")
				row_values[Fields.Recovered.value] = row_values[Fields.Recovered.value].strip("\n")
				if row_values[Fields.Country.value] in countries_dict:
					countries_dict[row_values[Fields.Country.value]].append(row_values)

		for key, value in countries_dict.items():
			# country_obj => is a tmp country object to pass into function
			country_obj = Country(key)

			# state is a dict
			for state in value:
				# print(state)
				# convert the date and cases into a date obj
				date_obj = Date(
					state[Fields.ObservationDate.value],
					state[Fields.Confirmed.value],
					state[Fields.Deaths.value],
					state[Fields.Recovered.value],
				)
				temp_state = State(state[Fields.State.value], key)
				# Add the dates to the states that already exist
				if state[Fields.State.value] in country_obj.states:
					country_obj.states[state[Fields.State.value]].dates[
						state[Fields.ObservationDate.value]
					] = date_obj

				elif state[Fields.State.value] not in country_obj.states:
					temp_state.dates[state[Fields.ObservationDate.value]] = date_obj
					country_obj.states[state[Fields.State.value]] = temp_state
					# print(country_obj.states)

				# if there is no value for state/province then add to country obj
				elif state[Fields.State.value] == "":
					country_obj.dates[state[Fields.ObservationDate.value]] = date_obj

			self.countries_data[key] = country_obj
			# self.country_objects.append(country_obj)
		print("Finish loading csv")


	# Returns the lists of all countries
	def get_countries(self):
		return self.countries_data

	# for updating the countries data
	def set_countries(self, countries):
		self.countries_data = copy.deepcopy(countries)

	# Intialize all the total type attributes for each country and state based off its nested objects
	def initTotals(self):
		countries = self.countries_data
		global_confirmed = 0
		global_deaths = 0
		global_recovered = 0
		# go through all a country's states and initialize all the totals,
		# then use those total to init the totals in the countries
		for country_obj in countries.values():
			for state_obj in country_obj.states.values():
				# since cases are cumulative, then get the max number in the list as that is the total
				# if that is a the case, isnt the last object the largest? assuming the list is sorted by date
				# This is true, the last object is the largest / the total
				# get last date object in a state's dates dict
				# if state_obj.state_name == "California":
				total = list(state_obj.dates.values())[-1]
				state_obj.total_confirmed = total.confirmed
				state_obj.total_deaths = total.deaths
				state_obj.total_recovered = total.recovered
				# print(total)
				# Now sum up all the country's state's totals and put it inside the country's totals attributes
				country_obj.total_confirmed += float(state_obj.total_confirmed)
				country_obj.total_deaths += float(state_obj.total_deaths)
				country_obj.total_recovered += float(state_obj.total_recovered)

				# if country_obj.country_name == "US":
				# 	print(
				# 		country_obj.total_confirmed, country_obj.total_deaths, country_obj.total_recovered
				# 	)
			# add to the glocal total of cases
			global_confirmed += country_obj.total_confirmed
			global_deaths += country_obj.total_deaths
			global_recovered += country_obj.total_recovered

		# at the end set the values to the global total types
		self.global_total_types["Total_Confirmed"] = global_confirmed
		self.global_total_types["Total_Deaths"] = global_deaths
		self.global_total_types["Total_Recovered"] = global_recovered

	# TODO: need to update this every call

	def init_top_5_country(self):
		countries = self.countries_data
		heapq.heapify(self.top_5_death_heap)
		heapq.heapify(self.top_5_confirmed_heap)
		for country_obj in countries.values():
			heapq.heappush(self.top_5_death_heap, (-country_obj.total_deaths, country_obj))
			heapq.heappush(self.top_5_confirmed_heap, (-country_obj.total_confirmed, country_obj))
		

	def init_reprJSON(self):
		countries = self.countries_data
		for country_obj in countries.values():
			country_obj.init_reprJSON()
		print("Finish init_reprJSON")

