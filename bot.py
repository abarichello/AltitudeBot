from config import TOKEN, GKEY
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton)
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, Job
from googlemaps import convert, elevation
from pprint import pprint
import logging, requests, json

updater = Updater(token=TOKEN)
dispatcher = updater.dispatcher
job = updater.job_queue

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

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

    #Log user name and altitude here
    print(response.status_code)
    pprint(data)
    print(username)
    #pprint(update.message.from_user.__dict__)
    #pprint(bot.__dict__)
    print(altitude)

def my_location(bot, update):    
    update.message.reply_text(location)

def echo(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Start me with /start and send me your location.")

def help(bot, update):
	bot.send_message(chat_id=update.message.chat_id, text="useful help text")

def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="That command does not exist!")

dispatcher.add_handler(CommandHandler('start', start))

dispatcher.add_handler(MessageHandler(Filters.location, location))

dispatcher.add_handler(CommandHandler('mylocation', my_location))

dispatcher.add_handler(MessageHandler(Filters.text, echo))

dispatcher.add_handler(CommandHandler('help', help))

dispatcher.add_handler(MessageHandler(Filters.command, unknown))

updater.start_polling()