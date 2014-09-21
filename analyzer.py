#!/usr/bin/python

import sys
import getopt
import csv
import re
import datetime
from termcolor import colored
import cPickle as pickle


path = ''
pattern = ''
exclude = ''
from_date = datetime.datetime.min
to_date = datetime.datetime.max

try:
	opts, args = getopt.getopt(sys.argv[1:], "i:", ["pattern=","exclude=","from=","to="])
except getopt.GetoptError:
	print 'analyzer.py -i <file> [-pattern <regex>] [-after <dd-mm-yyyy>]'
	sys.exit(2)
for opt, arg in opts:
	if opt == "-i":
		path = arg
	elif opt == "--pattern":
		pattern = arg
	elif opt == "--exclude":
		exclude = arg
	elif opt == "--from":
		from_date = datetime.datetime.strptime(arg, "%d-%m-%Y")
	elif opt == "--to":
		to_date = datetime.datetime.strptime(arg, "%d-%m-%Y")

regex = re.compile(pattern, re.IGNORECASE)
exclude_regex = re.compile(exclude, re.IGNORECASE)

def extract_date(transaction):
	match = re.search(r'\d\d-\d\d-\d\d \d\d:\d\d', transaction['Naam / Omschrijving'])
	if match:
		return datetime.datetime.strptime(match.group(0), "%d-%m-%y %H:%M")
	else:
		
		match = re.search(r'\d{8}', transaction['Datum'])
		return datetime.datetime.strptime(match.group(0), "%Y%m%d")

def get_category(transaction):
	with open('categories', 'rb') as f:
		reader = csv.DictReader(f)
		for row in reader:
			match=transaction.find(row["Name"])
			if match>=0:
				return row["Category"]
		return ""

def clean_description(transaction):
	if re.match('\d\d-\d\d-\d\d \d\d:\d\d BETAALAUTOMAAT', transaction['Naam / Omschrijving']):
		return "{}\t{}".format(transaction['Mededelingen'][:-61],transaction['Mededelingen'][-60:-47])
	if re.match('Naam: (?P<bank>.+) Omschrijving: (?P<omschrijving>.+) Kenmerk: (?P<kenmerk>.+) IBAN: (?P<iban>.+)', transaction['Mededelingen']):
		return re.match('Naam: (?P<bank>.+) Omschrijving: (?P<omschrijving>.+) Kenmerk: (?P<kenmerk>.+) IBAN: (?P<iban>.+)', transaction['Mededelingen']).group('omschrijving').strip()
	elif re.match('Naam: (?P<bank>.+) Omschrijving: (?P<omschrijving>.+) IBAN: (?P<iban>.+)', transaction['Mededelingen']):
		matches = re.match('Naam: (?P<bank>.+) Omschrijving: (?P<omschrijving>.+) IBAN: (?P<iban>.+)', transaction['Mededelingen'])
		return "{} ({})".format(matches.group('omschrijving').strip(), matches.group('bank').strip())
	else:
		return transaction['Mededelingen'].strip()

def print_transaction(transaction):
	sign = "+" if transaction['Af Bij'] == "Bij" else '-'
	color = 'red' if sign == '-' else 'green'
	s = '{cat}\t{sign}{bedrag}\t{date}\t{description}'.format(
		description=clean_description(transaction),
		sign=colored(sign, color, attrs=['bold']), 
		bedrag=colored(transaction['Bedrag (EUR)'], color, attrs=['bold']),
		date=extract_date(transaction).strftime("%d-%m-%Y"),
		cat=get_category(transaction['Mededelingen'][:-61]))

	print s
			
transactions = 0
matches = 0
total_spent = 0.0
total_received = 0.0
total = 0.0
with open(path, 'rb') as f:
	reader = csv.DictReader(f)
	for row in reader:
		transactions += 1
		if	extract_date(row) >= from_date and \
			extract_date(row) < to_date and \
			(regex.search(row['Mededelingen']) or \
			regex.search(row['Naam / Omschrijving'])) and \
			(exclude == '' or (not (exclude_regex.search(row['Mededelingen']) or \
			exclude_regex.search(row['Naam / Omschrijving'])))):

			matches += 1
			
			amount = float(row['Bedrag (EUR)'].replace(",", "."))
			if row['Af Bij'] == 'Bij':
				total += amount
				total_received += amount
			else:
				total -= amount
				total_spent += amount

			print_transaction(row)

print ""
print "Matched {}/{} transactions".format(matches, transactions)
print "Total received: {0:.2f} EUR".format(total_received)
print "Total spent: {0:.2f} EUR".format(total_spent)
print "Total: {}".format(colored("{0:.2f} EUR".format(total), ('green' if total >= 0 else 'red'), attrs=['bold']))
