from config import TOKEN, GKEY
from os import environ
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton)
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, Job
from googlemaps import convert, elevation
from pprint import pprint
from datetime import datetime

import logging, requests, json, sys, pymongo

updater = Updater(token=TOKEN)
dispatcher = updater.dispatcher
job = updater.job_queue

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

HELP_STRING = ("""
helpfull text
""").strip('\n')

try:
    conn = pymongo.MongoClient()
    print('connected')
except pymongo.errors.ConnectionFailure:
    print("could not connect")
    pass
 		 
db = conn['altitudes']
collection = db.altitude

def start(bot, update):
    button = KeyboardButton("Send your location", request_location=True)
    keyboard = ReplyKeyboardMarkup([[button]],resize_keyboard=True,one_time_keyboard=True)
    update.message.reply_text("Hi! Press the button to send me your location!", reply_markup=keyboard)

def location(bot, update):
    location = update.message.location
    elevation(bot, update, location.latitude, location.longitude)

def elevation(bot, update, latitude, longitude):
    username = update.message.from_user.username

    update.message.reply_text("Fetching your location.")
    response = requests.get('https://maps.googleapis.com/maps/api/elevation/json?locations={},{}&key={}'.format(latitude,longitude,GKEY))
    data = response.json()
    altitude = (data["results"][0]["elevation"])
    rounded_alt = round(altitude, 3)
    update.message.reply_text("Hi, @{}!{}Your current height is: {} meters".format(username,"\n",alti))
    #Log user name, altitude and city here
    collection.insert_one({
        "username": "{}".format(username), "altitude": "{}".format(rounded_alt)
    })

    #Open and write status_code to logger.txt    
    with open("log.txt", "a+") as f:
        f.write(str(response.status_code)+'\n')
        f.write(str(data)+'\n')
        currentTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(currentTime+'\n')
        f.write('------ \n')

    with open("altitudes.txt", "a+") as altitude_file:
        currentShortTime = datetime.now().strftime('%d-%m-%Y')
        altitude_file.write(str("{},{},{}{}".format(altitude, username,currentShortTime, "\n")))

def highest(bot, update):
    update.message.reply_text("Highest altitudes recorded: ")
    cursor = collection.find({})
    cursor.sort([('altitude', pymongo.DESCENDING)])
    cursor.limit(10)
    
    a = 1
    altered_string = []
    for document in cursor:
        usr = (document['username'])
        alt = (document['altitude'])
        string = "{}. @{} with {} meters".format(a,usr,alt,"\n")
        altered_string.append(string)
        a = a + 1
    final_string = '\n'.join(altered_string)
    update.message.reply_text(final_string)
    #join highest and lowest methods.
def lowest(bot, update):
    update.message.reply_text("Lowest altitudes recorded: ")
    cursor = collection.find({})
    cursor.sort([("altitude", pymongo.ASCENDING)])
    cursor.limit(10)

    a = 1
    altered_string = []
    for document in cursor:
        usr = (document['username'])
        alt = (document['altitude'])
        string = "{}. @{} with {} meters".format(a,usr,alt,"\n")
        altered_string.append(string)
        a = a + 1
    final_string = '\n'.join(altered_string)
    update.message.reply_text(final_string)

def echo(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Start me with /start and send me your location.")

def help(bot, update):
	bot.send_message(chat_id=update.message.chat_id, text=HELP_STRING)

def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="That command does not exist!")

dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(MessageHandler(Filters.location, location))
dispatcher.add_handler(MessageHandler(Filters.text, echo))
dispatcher.add_handler(CommandHandler('highest', highest))
dispatcher.add_handler(CommandHandler('lowest', lowest))
dispatcher.add_handler(CommandHandler('help', help))
dispatcher.add_handler(MessageHandler(Filters.command, unknown))
updater.start_polling()