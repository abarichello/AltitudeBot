import config

from os import environ
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InlineKeyboardButton,
 InlineKeyboardMarkup)
from telegram import InlineQueryResultArticle as InlineResult
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, Job, BaseFilter, InlineQueryHandler
from googlemaps import convert, elevation
from pprint import pprint
import logging, requests, json, sys, pymongo

updater = Updater(token=config.TOKEN)
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

conn = pymongo.MongoClient(config.MONGODB_URI)
db = conn.get_default_database()
collection = db.altitudes
blacklist = db.blacklist

def start(bot, update):
    button = KeyboardButton("Send your location", request_location=True)
    keyboard = ReplyKeyboardMarkup([[button]],resize_keyboard=True,one_time_keyboard=True)
    START_STRING = ("""Hi! Press the button to send me your location!
Or see the current rank with /lowest and /highest""")
    update.message.reply_text(START_STRING, reply_markup=keyboard)

def location(bot, update):
    location = update.message.location
    elevation(bot, update, location.latitude, location.longitude)

def elevation(bot, update, latitude, longitude):
    userId = update.message.chat.id
    username = update.message.from_user.username
    if not username:
        fName = update.message.from_user.first_name
        lName = update.message.from_user.last_name
        if not lName:
            lName = ' '
        username = f'{fName} {lName}'
    
    update.message.reply_text("Fetching your location...")
    
    if check_eligibility(userId) and check_blacklist(userId):
        # Handle elevation
        elv_response = requests.get(
            f'https://maps.googleapis.com/maps/api/elevation/json?locations={latitude},{longitude}&key={config.GKEY}')
        elevation_data = elv_response.json()
        altitude = (elevation_data["results"][0]["elevation"])
        rounded_alt = round(altitude, 3)
        
        # Handle city
        result_type = 'country|administrative_area_level_1|administrative_area_level_2'
        geo_response = requests.get(
            'https://maps.googleapis.com/maps/api/geocode/json?latlng={},{}&key={}'.format(
                latitude, longitude, config.GKEY))
        geo_data = geo_response.json()
        try:
            user_location = (geo_data['results'][1]['formatted_address'])
        except IndexError as e:
            print(e)
            print(geo_data)
            update.message.reply_text("Something went wrong with your location.")
            update.message.reply_text("Try another location or forward it to @aBARICHELLO")

        # Respond with altitude
        update.message.reply_text(
                "Hi, @{}!{}Your current height is: {} meters at the location of {}".format(
                    username, "\n", rounded_alt, user_location))
        
        # Check and add to database
        if check_altitude(rounded_alt) and check_repeated(update, rounded_alt):
            add_to_database(bot, username, userId, rounded_alt, user_location)
            update.message.reply_text("Location added to database")
        elif not check_altitude(altitude):
            update.message.reply_text("There's something wrong with that location! Contact @aBARICHELLO")    
        elif not check_repeated(update, rounded_alt):
            update.message.reply_text("That location was already added! :/")
    elif not check_blacklist(userId):
            update.message.reply_text("I'm sorry but you are blacklisted ;)")
    else:
        update.message.reply_text("You've reached the limit of entries. Contact @aBARICHELLO for deletions or use /clear to delete ALL")

def check_altitude(altitude): # Returns false for an unusual location.
    return config.MINVALUE <= altitude <= config.MAXVALUE

def check_repeated(update, rounded_alt): # Checks if the user has already sent this location
    userId = update.message.chat.id
    cursor = collection.find({'userId': userId, 'altitude': rounded_alt}).count()

    return cursor is 0
        
def check_eligibility(userId): # Checks if the user has more entries than allowed to
    userCount = 0
    cursor = collection.find({'userId': userId})

    for document in cursor:
        userCount += 1
    
    return userCount <= config.MAXENTRIES

def check_blacklist(userId): # Checks if the user is in the blacklisted database
    cursor = blacklist.find({'userId': userId})

    for document in cursor:
        return False
    return True

def add_to_database(bot, username, userId, rounded_alt, user_location):
    doc ={"username": username,
    "userId": userId,
    "altitude": rounded_alt,
    "city": user_location}
    collection.insert_one(doc)

    bot.send_message(chat_id=config.DEBUG_CHANNEL ,text="{}|{}|{}".format(
        username, rounded_alt, user_location))

def sorted_entries(bot, update, order):
    cursor = collection.find().sort('altitude', order)

    final_string = doc_cursor(cursor)
    update.message.reply_text(final_string)

def lowest(bot, update):
    sorted_entries(bot, update, pymongo.ASCENDING)

def highest(bot, update):
    sorted_entries(bot, update, pymongo.DESCENDING)

def my_altitudes(bot, update):
    username = update.message.from_user.username
    cursor = collection.find({'username': username}).sort(username, pymongo.DESCENDING)
    cursor.limit(20)

    a = 1
    altered_string = []
    for document in cursor:
        if len(altered_string) < 20:
            alt = (document["altitude"])
            cty = (document["city"])
            
            string = f"{a} - {alt} meters at {cty}"
            altered_string.append(string)
            a += 1
    final_string = '\n'.join(altered_string)
    update.message.reply_text(final_string)
    
def doc_cursor(cursor): # Method used to navigate the database.
    a = 1
    altered_string = []
    added_users = []
    for document in cursor:
        if len(altered_string) <= config.CURSOR_SIZE:
            usr = (document["username"])
            alt = (document["altitude"])
            cty = (document["city"])
            
            if ' ' in usr:
                symbol = '-'
            else:
                symbol = '@'

            string = f"{a}. {symbol}{usr} with {alt} meters at {cty}"
            if usr not in added_users:
                added_users.append(usr)
                altered_string.append(string)
                a += 1
    final_string = '\n'.join(altered_string)
    return final_string
    
def clear(bot, update):
    userId = update.message.chat.id
    update.message.reply_text("Deleted all your locations! :(")
    collection.delete_many({'userId': userId})

def help(bot, update):
	bot.send_message(chat_id=update.message.chat_id, text=HELP_STRING)

def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="That command does not exist!")

dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(MessageHandler(Filters.location & (~Filters.forwarded) & Filters.reply, location))
dispatcher.add_handler(CommandHandler('lowest', lowest))
dispatcher.add_handler(CommandHandler('highest', highest))
dispatcher.add_handler(CommandHandler('myaltitudes', my_altitudes))
dispatcher.add_handler(CommandHandler('clear', clear))
dispatcher.add_handler(CommandHandler('help', help))

updater.start_webhook(listen='0.0.0.0', port=config.PORT, url_path=config.TOKEN)
updater.bot.setWebhook("https://" + config.APPNAME + ".herokuapp.com/" + config.TOKEN)
updater.idle()