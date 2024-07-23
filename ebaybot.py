import requests
import os
import sys
from time import sleep
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Hier den erhaltenen API-Token einfügen
TELEGRAM_API_TOKEN = os.getenv('TELEGRAM_API')

if not TELEGRAM_API_TOKEN:
    print("\033[91mERROR: Telegram API-Token not set in the current runtime! Aborting...\033[0m")
    sleep(2)
    sys.exit(1)

# Funktion zum Scrapen von eBay-Angeboten mit zusätzlichen Parametern
def scrape_ebay(keyword, min_price=None, max_price=None, condition=None, listing_type=None):
    url = f"https://www.ebay.de/sch/i.html?_nkw={keyword}"
    
    if min_price:
        url += f"&_udlo={min_price}"
    if max_price:
        url += f"&_udhi={max_price}"
    if condition:
        url += f"&_nkw={keyword} {condition}"
    if listing_type:
        if listing_type == "auction":
            url += "&LH_Auction=1"
        elif listing_type == "buyitnow":
            url += "&LH_BIN=1"

    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    items = []
    
    for item in soup.find_all('li', class_='s-item'):
        title = item.find('h3', class_='s-item__title')
        
        # Check for alternative title containers if the title is missing
        if not title or not title.get_text().strip():
            title = item.find('div', class_='s-item__title')
        if not title or not title.get_text().strip():
            title = item.find('span', class_='s-item__title')
        
        title_text = title.get_text().strip() if title and title.get_text().strip() else "Kein Titel"

        price = item.find('span', class_='s-item__price')
        price_text = price.get_text().strip() if price else "Kein Preis"

        link = item.find('a', class_='s-item__link')['href']
        
        items.append({'title': title_text, 'price': price_text, 'link': link})
    
    return items

# Funktion zum Senden von eBay-Angeboten
def send_ebay_offers(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    args = context.args
    if not args:
        update.message.reply_text("Bitte gib einen Suchbegriff ein. Beispiel: /ebay laptop")
        return

    keyword = args[0]
    min_price = None
    max_price = None
    condition = None
    listing_type = None

    # Verarbeiten der optionalen Argumente
    for arg in args[1:]:
        if arg.startswith("min:"):
            min_price = arg.split("min:")[1]
        elif arg.startswith("max:"):
            max_price = arg.split("max:")[1]
        elif arg.startswith("condition:"):
            condition = arg.split("condition:")[1]
        elif arg.startswith("type:"):
            listing_type = arg.split("type:")[1]

    items = scrape_ebay(keyword, min_price, max_price, condition, listing_type)
    
    if not items:
        context.bot.send_message(chat_id=chat_id, text="Keine Angebote gefunden.")
        return
    
    message = ""
    details = {}
    
    for idx, item in enumerate(items):
        message += f"{idx+1}. {item['title']} - Preis: {item['price']}\n"
        details[str(idx+1)] = item['link']
        
        # Check if the message length exceeds the Telegram limit (4096 characters)
        if len(message) > 4000:
            context.bot.send_message(chat_id=chat_id, text=message)
            message = ""

    if message:
        context.bot.send_message(chat_id=chat_id, text=message)
    
    context.user_data['details'] = details

# Funktion zum Bereitstellen der Detailansicht
def detail(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    args = update.message.text.split(" ")
    if len(args) < 2:
        context.bot.send_message(chat_id=chat_id, text="Bitte gib eine gültige Nummer an. Beispiel: /detail 1")
        return

    query = args[1]  # Annahme: Der Benutzer gibt "/detail <Nummer>" ein
    
    details = context.user_data.get('details', {})
    link = details.get(query, None)
    
    if link:
        context.bot.send_message(chat_id=chat_id, text=f"Hier ist der Link: {link}")
    else:
        context.bot.send_message(chat_id=chat_id, text="Ungültige Nummer. Bitte versuche es erneut.")

# Funktion zum Senden der Hilfe-Nachricht
def help_command(update: Update, context: CallbackContext):
    help_text = (
        "Hallo! Ich bin dein eBay-Scraping-Bot. Hier sind die verfügbaren Befehle:\n\n"
        "/start - Starte den Bot\n"
        "/help - Zeigt diese Hilfe-Nachricht an\n"
        "/ebay <Suchbegriff> [min:<Preis>] [max:<Preis>] [condition:<Zustand>] [type:<Angebotsformat>] - Suche nach eBay-Angeboten\n"
        "/detail <Nummer> - Zeigt den Link zu einem bestimmten Angebot an\n\n"
        "Beispiele:\n"
        "/ebay laptop min:100 max:500 condition:neu type:buyitnow\n"
        "/detail 1"
    )
    update.message.reply_text(help_text)

def start(update: Update, context: CallbackContext):
    update.message.reply_text('Hallo! Ich bin dein eBay-Scraping-Bot. Verwende den Befehl /help, um zu erfahren, wie du mich verwenden kannst.')

def main():
    updater = Updater(token=TELEGRAM_API_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('help', help_command))
    dp.add_handler(CommandHandler('ebay', send_ebay_offers))
    dp.add_handler(CommandHandler('detail', detail))
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
