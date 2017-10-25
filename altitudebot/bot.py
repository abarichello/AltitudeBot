import config
import strings

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
    button = KeyboardButton(strings.SEND_LOCATION + config.AMERICAS, request_location=True)
    keyboard = ReplyKeyboardMarkup([[button]],resize_keyboard=True,one_time_keyboard=True)
    START_STRING = (config.RICE + strings.START)
    update.message.reply_text(START_STRING, reply_markup=keyboard)

def location(bot, update):
    location = update.message.location
    elevation(bot, update, location.latitude, location.longitude)

def elevation(bot, update, latitude, longitude):
    user_id = update.message.chat.id
    username = update.message.from_user.username
    if not username:
        fName = update.message.from_user.first_name
        lName = update.message.from_user.last_name
        if not lName:
            lName = ' '
        username = f'{fName} {lName}'
    
    update.message.reply_text(strings.FETCHING)
    
    if check_eligibility(user_id) and check_blacklist(user_id):
        # Handle elevation
        elv_response = requests.get(
            f'https://maps.googleapis.com/maps/api/elevation/json?locations={latitude},{longitude}&key={config.GKEY}')
        elevation_data = elv_response.json()
        altitude = (elevation_data["results"][0]["elevation"])
        rounded_alt = round(altitude, 3)
        
        # Handle city
        # result_type = 'country|administrative_area_level_1|administrative_area_level_2'
        geo_response = requests.get(
            'https://maps.googleapis.com/maps/api/geocode/json?latlng={},{}&key={}'.format(
                latitude, longitude, config.GKEY))
        geo_data = geo_response.json()
        try:
            user_location = (geo_data['results'][1]['formatted_address'])
        except IndexError as e:
            print(e)
            print(geo_data)
            update.message.reply_text(strings.LOCATION_ERROR)
            update.message.reply_text(strings.LOCATION_ERROR1)

        # Respond with altitude
        update.message.reply_text(
                config.WORLD + " Hi, @{}!{}Your current height is: {} meters at the location of {}".format(
                    username, "\n", rounded_alt, user_location))
        
        # Check and add to database
        if check_altitude(rounded_alt) and check_repeated(update, rounded_alt):
            add_to_database(bot, username, user_id, rounded_alt, user_location)
            update.message.reply_text(strings.ADDEDTODB)
        elif not check_altitude(altitude):
            update.message.reply_text(strings.LOCATION_ERROR)    
        elif not check_repeated(update, rounded_alt):
            update.message.reply_text(strings.REPEATED_LOCATION)
    elif not check_blacklist(user_id):
            update.message.reply_text(strings.BLACKLISTED)
    else:
        update.message.reply_text(strings.LIMIT_REACHED)

def check_altitude(altitude): # Returns false for an unusual location.
    return config.MINVALUE <= altitude <= config.MAXVALUE

def check_repeated(update, rounded_alt): # Checks if the user has already sent this location
    user_id = update.message.chat.id
    count = collection.find({'userId': user_id, 'altitude': rounded_alt}).count()

    return count is 0
        
def check_eligibility(user_id): # Checks if the user has more entries than allowed to
    count = collection.find({'userId': user_id}).count()

    return count <= config.MAXENTRIES

def check_blacklist(user_id): # Checks if the user is in the blacklisted database
    cursor = blacklist.find({'userId': user_id})

    for document in cursor:
        return False
    return True

def add_to_database(bot, username, user_id, rounded_alt, user_location):
    doc = {
        "username": username,
        "userId": user_id,
        "altitude": rounded_alt,
        "city": user_location,
    }

    collection.insert_one(doc)

    bot.send_message(chat_id=config.DEBUG_CHANNEL ,text="{}|{}|{}".format(
        username, rounded_alt, user_location))

def sorted_entries(bot, update, order): # Sorts the database (Ascending or Descending)
    cursor = collection.find().sort('altitude', order)

    header = config.MOUNT_FUJI + " Highest players: \n"
    if order is pymongo.ASCENDING:
        header = config.WAVE + " Lowest players \n"
    
    final_string = header + doc_cursor(cursor)
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
    user_id = update.message.chat.id
    update.message.reply_text(strings.DELETED_LOCATION)
    collection.delete_many({'userId': user_id})

def help(bot, update):
	bot.send_message(chat_id=update.message.chat_id, text=HELP_STRING)

def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=strings.NO_COMMAND)

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
