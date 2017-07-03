from config import TOKEN, GKEY
from os import environ
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton)
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, Job
from googlemaps import convert, elevation
from pprint import pprint
from datetime import datetime
from pymongo import MongoClient

import logging, requests, json, sys

updater = Updater(token=TOKEN)
dispatcher = updater.dispatcher
job = updater.job_queue

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

MONGODB_URI = environ['MONGODB_URI']

client = MongoClient()
db = client.get_default_database

HELP_STRING = ("""
helpfull text
""").strip('\n')

f = open("log.txt", "a+")
altitudes_file = open("altitudes.txt", "r")

def start(bot, update):
    button = KeyboardButton("Send your location", request_location=True)
    keyboard = ReplyKeyboardMarkup([[button]])
    update.message.reply_text("Hi! Press the button to send me your location!", reply_markup=keyboard)

def location(bot, update):
    location = update.message.location
    elevation(bot, update, location.latitude, location.longitude)

def elevation(bot, update, latitude, longitude):
    username = update.message.from_user.username
    update.message.reply_text("latitude: {}, longitude: {}".format(latitude, longitude))
    response = requests.get('https://maps.googleapis.com/maps/api/elevation/json?locations={},{}&key={}'.format(latitude,longitude,GKEY))
    data = response.json()
    
    altitude = (data["results"][0]["elevation"])
    update.message.reply_text("Hi, @{}! your current height is: {} meters".format(username,altitude))
    #Log user name, altitude and city here

    #Open and write status_code to logger.txt    
    f.write(str(response.status_code)+'\n')
    f.write(str(data)+'\n')
    currentTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    f.write(currentTime+'\n')
    f.write('\n')

    currentShortTime = datetime.now().strftime('%d-%m-%Y')
    print(str(altitude)+ ' @'+username+' Date:'+ currentShortTime)

def echo(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Start me with /start and send me your location.")

def help(bot, update):
	bot.send_message(chat_id=update.message.chat_id, text=HELP_STRING)

def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="That command does not exist!")

dispatcher.add_handler(CommandHandler('start', start))

dispatcher.add_handler(MessageHandler(Filters.location, location))

dispatcher.add_handler(MessageHandler(Filters.text, echo))

dispatcher.add_handler(CommandHandler('help', help))

dispatcher.add_handler(MessageHandler(Filters.command, unknown))

updater.start_polling()