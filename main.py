import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from collections import defaultdict
import threading
import time

TOKEN = "8066106264:AAG3557fe91lz54EWtjAbfSNbd6YWEs9x_s"
bot = telebot.TeleBot(TOKEN)

inventory = {
    "Motor Boat": 6,
    "Solo Kayak": 6,
    "Double Kayak": 7,
    "Canoe": 4,
    "SUP": 16,
    "BBQ Boat": 2
}
rental_counter = defaultdict(int)
active_rentals = []

def rental_id(name):
    rental_counter[name] += 1
    return f"{name} #{rental_counter[name]}"

@bot.message_handler(commands=['start'])
def welcome(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🚤 Rent a Boat", callback_data="rent"))
    bot.send_message(message.chat.id, "Welcome to Captain Sirot! Choose an action:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "rent")
def choose_boat_type(call):
    markup = InlineKeyboardMarkup()
    for item in inventory:
        if inventory[item] > 0:
            markup.add(InlineKeyboardButton(item, callback_data=f"choose_{item}"))
    bot.edit_message_text("Choose a boat to rent:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("choose_"))
def choose_duration(call):
    boat_type = call.data.split("_", 1)[1]
    markup = InlineKeyboardMarkup()
    durations = [0.5, 1, 2, 4, 8]  # 8 = full day
    for d in durations:
        label = f"{d}h" if d < 8 else "All Day"
        markup.add(InlineKeyboardButton(label, callback_data=f"duration_{boat_type}_{d}"))
    bot.edit_message_text(f"Select rental duration for {boat_type}:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("duration_"))
def confirm_rental(call):
    _, boat_type, hours = call.data.split("_")
    hours = float(hours)
    if inventory[boat_type] <= 0:
        bot.answer_callback_query(call.id, "Not available.")
        return

    name = rental_id(boat_type)
    start = datetime.now()
    end = start + timedelta(hours=hours)
    rental = {
        "chat_id": call.message.chat.id,
        "message_id": None,
        "name": name,
        "type": boat_type,
        "start": start,
        "end": end,
        "timer_msg": None,
        "cancel_stage": False
    }
    active_rentals.append(rental)
    inventory[boat_type] -= 1

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Returned", callback_data=f"returned_{name}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{name}")
    )

    msg = bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"✅ *{name}* rented until *{end.strftime('%H:%M')}*",
        parse_mode="Markdown",
        reply_markup=markup
    )
    rental["message_id"] = msg.message_id

    threading.Thread(target=countdown_timer, args=(rental,), daemon=True).start()

def countdown_timer(rental):
    while True:
        now = datetime.now()
        if now >= rental["end"]:
            remaining = "⏰ Time's up!"
        else:
            remaining = str(rental["end"] - now).split('.')[0]
        try:
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("✅ Returned", callback_data=f"returned_{rental['name']}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{rental['name']}")
            )
            bot.edit_message_text(
                chat_id=rental["chat_id"],
                message_id=rental["message_id"],
                text=f"🛶 *{rental['name']}*\n⏳ Time left: *{remaining}*",
                parse_mode="Markdown",
                reply_markup=markup
            )
        except:
            pass
        time.sleep(30)
        if rental not in active_rentals:
            break

@bot.callback_query_handler(func=lambda call: call.data.startswith("returned_"))
def handle_return(call):
    name = call.data.split("_", 1)[1]
    for rental in active_rentals:
        if rental["name"] == name:
            active_rentals.remove(rental)
            inventory[rental["type"]] += 1
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                text=f"✅ *{name}* was returned.",
                parse_mode="Markdown")
            break

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_"))
def confirm_cancel(call):
    name = call.data.split("_", 1)[1]
    for rental in active_rentals:
        if rental["name"] == name:
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("✅ Yes, cancel", callback_data=f"cancel_yes_{name}"),
                InlineKeyboardButton("❌ No", callback_data=f"cancel_no_{name}")
            )
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                text=f"⚠️ Are you sure you want to cancel *{name}*?",
                parse_mode="Markdown",
                reply_markup=markup)
            break

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_yes_"))
def cancel_yes(call):
    name = call.data.split("_", 2)[2]
    for rental in active_rentals:
        if rental["name"] == name:
            active_rentals.remove(rental)
            inventory[rental["type"]] += 1
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                text=f"❌ *{name}* has been canceled.",
                parse_mode="Markdown")
            break

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_no_"))
def cancel_no(call):
    name = call.data.split("_", 2)[2]
    for rental in active_rentals:
        if rental["name"] == name:
            countdown_timer(rental)
            break

bot.infinity_polling()
