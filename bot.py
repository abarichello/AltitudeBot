from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, Job
import logging

updater = Updater(token='')
dispatcher = updater.dispatcher
job = updater.job_queue

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def start(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text="Send ur location lul")

def echo(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Send location with /location")

def location(bot, update):
	bot.send_Message(chat_id=update.message.chat_id, text="Send your location", reply_markup=ReplyKeyboardMarkwup([[KeyboardButton("label", request_location=True)]]))

def help(bot, update):
	bot.send_message(chat_id=update.message.chat_id, text="useful help text")

def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="That command does not exist!")

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

echo_handler = MessageHandler(Filters.text, echo)
dispatcher.add_handler(echo_handler)
 
help_handler = MessageHandler('help', help)
dispatcher.add_handler(help_handler)

location_handler = MessageHandler('location', location)
dispatcher.add_handler(location_handler)

unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(unknown_handler)

updater.start_polling()
