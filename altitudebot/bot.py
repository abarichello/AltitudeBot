from config import TOKEN, GKEY, MONGODB_URI, APPNAME, PORT, MAINTANER, MINVALUE, MAXVALUE, DEBUG_CHANNEL
from filters import FilterHighest, FilterLowest
from os import environ
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InlineKeyboardButton,
 InlineKeyboardMarkup)
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, Job, BaseFilter
from googlemaps import convert, elevation
from pprint import pprint
from datetime import datetime
import logging, requests, json, sys, pymongo

updater = Updater(token=TOKEN)
dispatcher = updater.dispatcher
job = updater.job_queue

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

HELP_STRING = ("""
Send me your location and i will rank it! Compete with your friends to see who gets the
highest(or lowest) location on Earth!
Repeated altitudes are not ranked!

/start - Shows the location-sending button
/ranking - Select the rank of highest/lowest user locations
/myaltitudes - Displays your highest altitudes
/help - Shows a really helpful text(this one)

Star me on GitHub!
https://www.github.com/abarichello/altitudebot
Feedback? Questions? Contact me here: https://t.me/aBARICHELLO
""").strip('\n')

filter_lowest = FilterLowest()
filter_highest = FilterHighest()

conn = pymongo.MongoClient(MONGODB_URI)
db = conn.get_default_database()
print('connected')
collection = db.altitudes

def start(bot, update):
    button = KeyboardButton("Send your location", request_location=True)
    keyboard = ReplyKeyboardMarkup([[button]],resize_keyboard=True,one_time_keyboard=True)
    start_text = ("""Hi! Press the button to send me your location!
Or see the current rank with /ranking""")
    update.message.reply_text(start_text, reply_markup=keyboard)

def location(bot, update):
    location = update.message.location
    elevation(bot, update, location.latitude, location.longitude)

def elevation(bot, update, latitude, longitude):
    username = update.message.from_user.username
    if (username == None):
        username = update.message.from_user.first_name
    update.message.reply_text("Fetching your location")
    
    #Handle elevation
    elv_response = requests.get(
        'https://maps.googleapis.com/maps/api/elevation/json?locations={},{}&key={}'.format(latitude, longitude, GKEY))
    elevation_data = elv_response.json()
    altitude = (elevation_data["results"][0]["elevation"])
    rounded_alt = round(altitude, 3)
    
    #Handle city
    geo_response = requests.get(
        'https://maps.googleapis.com/maps/api/geocode/json?latlng={},{}&key={}'.format(latitude, longitude, GKEY))
    geo_data = geo_response.json()
    user_city = (geo_data["results"][0]["address_components"][4]["long_name"])

    if (check_altitude(rounded_alt)):
        update.message.reply_text(
            "Hi, @{}!{}Your current height is: {} meters at the city of {}".format(username, "\n", rounded_alt, user_city))
        doc ={"username": username,
        "altitude": rounded_alt,
        "city": user_city}
        collection.insert_one(doc)
        bot.send_message(chat_id=DEBUG_CHANNEL ,text="{}{}{}".format(username,rounded_alt,user_city,user_city))

        #Logging status codes
        with open("log.txt", "a+") as f:
            f.write(str(elv_response.status_code)+'\n')
            f.write(str(elevation_data)+'\n')
            currentTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(currentTime+'\n')
            f.write('------ \n')

        with open("altitudes.txt", "a+") as altitude_file:
            currentShortTime = datetime.now().strftime('%d-%m-%Y')
            altitude_file.write(str("{},{},{}{}".format(altitude, username,currentShortTime, "\n")))
    else:
        update.message.reply_text("That location seems really odd...")

def ranking(bot, update):
    btn1 = KeyboardButton(text="Lowest")
    btn2 = KeyboardButton(text="Highest")
    keyboard = ReplyKeyboardMarkup([[btn1, btn2]],resize_keyboard=True)
    update.message.reply_text("Select the order", reply_markup=keyboard)

def highest(bot, update):
    cursor = collection.find().sort('altitude', pymongo.DESCENDING).limit(12)
    
    final_string = doc_cursor(cursor)    
    update.message.reply_text(final_string)

def lowest(bot, update):
    cursor = collection.find().sort('altitude', pymongo.ASCENDING).limit(12)
    
    final_string = doc_cursor(cursor)
    update.message.reply_text(final_string)

def my_altitudes(bot, update): #Retrieve only the current user's altitude
    username = update.message.from_user.username
    cursor = collection.find({'username': username}).sort(username, pymongo.DESCENDING)
    cursor.limit(20)

    final_string = doc_cursor(cursor)
    update.message.reply_text(final_string)
    
def doc_cursor(cursor): #Method used to navigate the database.
    a = 1
    altered_string = []
    added_users = []
    for document in cursor:
        usr = (document["username"])
        alt = (document["altitude"])
        cty = (document["city"])
        
        string = "{}. @{} with {} meters at {}".format(a,usr,alt,cty)
        if usr not in added_users:
            added_users.append(usr)
            altered_string.append(string)
            a = a + 1
    final_string = '\n'.join(altered_string)
    return final_string

def check_altitude(altitude): #Returns false for an unusual location.
    if (altitude > int(MAXVALUE) or altitude < int(MINVALUE)):
        return False
    return True

def echo(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="/start me and press the button!")

def help(bot, update):
	bot.send_message(chat_id=update.message.chat_id, text=HELP_STRING)

def clear(bot, update): #test
    user_id = update.message.from_user.id
    if (user_id == MAINTANER):
        collection.remove({})
        update.message.reply_text("Cleared!")
    else:
        update.message.reply_text("Denied")

def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="That command does not exist!")

dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(MessageHandler(Filters.location & (~Filters.forwarded) & Filters.reply, location))
dispatcher.add_handler(CommandHandler('ranking', ranking))
dispatcher.add_handler(MessageHandler(filter_highest, highest))
dispatcher.add_handler(MessageHandler(filter_lowest, lowest))
dispatcher.add_handler(MessageHandler(Filters.text, echo))
dispatcher.add_handler(CommandHandler('myaltitudes', my_altitudes))
dispatcher.add_handler(CommandHandler('help', help))
dispatcher.add_handler(CommandHandler('clear', clear))
dispatcher.add_handler(MessageHandler(Filters.command, unknown))
updater.start_webhook(listen='0.0.0.0', port=int(PORT), url_path=TOKEN)
updater.bot.setWebhook("https://" + APPNAME + ".herokuapp.com/" + TOKEN)
updater.idle()