import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from collections import defaultdict, Counter

TOKEN = '8066106264:AAG3557fe91lz54EWtjAbfSNbd6YWEs9x_s'
bot = telebot.TeleBot(TOKEN)

inventory_template = {
    "Motor Boat": 6,
    "Solo Kayak": 6,
    "Double Kayak": 7,
    "Canoe": 4,
    "SUP": 16,
    "BBQ Boat": 2
}
inventory = inventory_template.copy()
rental_id_counter = defaultdict(int)
active_rentals = []
rental_history = []

def format_time(dt):
    return dt.strftime('%H:%M')

def get_rental_name(r_type):
    rental_id_counter[r_type] += 1
    return f"{r_type} #{rental_id_counter[r_type]}"

def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🚤 Rent Boat", "📦 Inventory")
    markup.row("🕒 Active Rentals", "✅ Return")
    markup.row("📊 Daily Stats")
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Ahoy Captain!\nWhat would you like to do?", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def handle_menu(message):
    text = message.text

    if text == "📦 Inventory":
        msg = "*Available Inventory:*\n"
        for item, count in inventory.items():
            msg += f"- {item}: {count}\n"
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")

    elif text == "🚤 Rent Boat":
        markup = InlineKeyboardMarkup()
        for item in inventory:
            if inventory[item] > 0:
                markup.add(InlineKeyboardButton(f"Rent {item}", callback_data=f"select_{item}"))
        bot.send_message(message.chat.id, "Choose item to rent:", reply_markup=markup)

    elif text == "🕒 Active Rentals":
        if not active_rentals:
            bot.send_message(message.chat.id, "No active rentals.")
            return
        msg = "*Active Rentals:*\n"
        now = datetime.now()
        for rental in active_rentals:
            left = rental["end"] - now
            if left.total_seconds() > 0:
                time_left = str(left).split('.')[0]
                msg += f"- {rental['name']}: {time_left} left\n"
            else:
                overdue = str(-left).split('.')[0]
                msg += f"- 🔴 {rental['name']}: ⏰ Time’s up! ({overdue} overdue)\n"
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")

    elif text == "✅ Return":
        markup = InlineKeyboardMarkup()
        for rental in active_rentals:
            markup.add(InlineKeyboardButton(f"Return {rental['name']}", callback_data=f"return_{rental['name']}"))
        bot.send_message(message.chat.id, "Select item to return:", reply_markup=markup)

    elif text == "📊 Daily Stats":
        today = datetime.now().date()
        rentals_today = [r for r in rental_history if r["start"].date() == today]
        returns_today = [r for r in rentals_today if isinstance(r["end"], datetime)]
        overdue = [r for r in active_rentals if r["start"].date() == today and r["end"] < datetime.now()]

        counter = Counter(r["type"] for r in rentals_today)
        total_hours = sum((r["end"] - r["start"]).total_seconds() for r in returns_today) / 3600

        msg = f"📅 *Daily Summary – {today.strftime('%d.%m.%Y')}*\n\n"
        msg += f"🔄 Rentals Today: {len(rentals_today)}\n"
        msg += f"✅ Returns: {len(returns_today)}\n"
        msg += f"⏰ Overdue: {len(overdue)}\n\n"
        msg += "*Top Rented:*\n"
        for t, c in counter.most_common():
            msg += f"- {t}: {c} times\n"
        msg += f"\n🕓 Total Rental Time: {round(total_hours, 1)} hours"

        bot.send_message(message.chat.id, msg, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_"))
def select_item(call):
    item = call.data.split("_", 1)[1]
    markup = InlineKeyboardMarkup()
    for i in range(1, 13):
        hours = i * 0.5
        markup.add(InlineKeyboardButton(f"{hours}h", callback_data=f"rent_{item}_{hours}"))
    bot.edit_message_text(f"Select rental duration for {item}:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("rent_"))
def confirm_rental(call):
    _, item, hours = call.data.split("_")
    hours = float(hours)
    if inventory[item] <= 0:
        bot.answer_callback_query(call.id, "Not available.")
        return

    rental_name = get_rental_name(item)
    return_time = datetime.now() + timedelta(hours=hours)
    active_rentals.append({
        "name": rental_name,
        "type": item,
        "user": call.from_user.id,
        "start": datetime.now(),
        "end": return_time
    })
    rental_history.append({
        "type": item,
        "start": datetime.now(),
        "end": return_time
    })
    inventory[item] -= 1
    msg = f"✅ *{rental_name}* rented for *{hours}h*\n⏳ Return by: *{format_time(return_time)}*"
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("return_"))
def handle_return(call):
    name = call.data.split("_", 1)[1]
    for rental in active_rentals:
        if rental["name"] == name:
            inventory[rental["type"]] += 1
            overdue = max(datetime.now() - rental["end"], timedelta(0))
            msg = f"✅ {name} returned.\n⌛ Delay: {str(overdue).split('.')[0]}" if overdue > timedelta(0) else f"✅ {name} returned on time."
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id)
            rental_history.append({
                "type": rental["type"],
                "start": rental["start"],
                "end": datetime.now()
            })
            active_rentals.remove(rental)
            return

bot.infinity_polling()
