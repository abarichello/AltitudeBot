from telegram.ext import BaseFilter

class FilterLowest(BaseFilter):
    def filter(self, message):
        return 'Lowest' in message.text

class FilterHighest(BaseFilter):
    def filter(self, message):
        return 'Highest' in message.text