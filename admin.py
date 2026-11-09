import json
import re
import time
from datetime import datetime
import requests
from telebot import types
from config import ADMINS, CHANNEL_ID
from database import cur, conn, get_giveaway
import texts
import logger

drafts = {}
admin_states = {} 

GIFTS = {
    "heart": {"emoji": "❤️", "name": "Сердце", "price": 15, "id": 5170145012310081615},
    "bear": {"emoji": "🧸", "name": "Мишка", "price": 15, "id": 5170233102089322756},
    "gift": {"emoji": "🎁", "name": "Подарок", "price": 25, "id": 5170250947678437525},
    "rose": {"emoji": "🌹", "name": "Роза", "price": 25, "id": 5168103777563050263},
    "cake": {"emoji": "🎂", "name": "Торт", "price": 50, "id": 5170144170496491616},
    "bouquet": {"emoji": "💐", "name": "Букет", "price": 50, "id": 5170314324215857265},
    "rocket": {"emoji": "🚀", "name": "Ракета", "price": 50, "id": 5170564780938756245},
    "champagne": {"emoji": "🍾", "name": "Шампанское", "price": 50, "id": 60286016306662853006},
    "cup": {"emoji": "🏆", "name": "Кубок", "price": 100, "id": 5168043875654172773},
    "ring": {"emoji": "💍", "name": "Кольцо", "price": 100, "id": 5170690322832818290},
    "diamond": {"emoji": "💎", "name": "Алмаз", "price": 100, "id": 5170521118301225164},
}

def register(bot):
    def is_admin(uid): 
        return uid in ADMINS

    def guard(step):
        def f(message):
            d = drafts.get(message.from_user.id)
            return d and d.get("step") == step
        return f

    # Исправленная функция меню с безопасными методами .get()
    def send_conditions_menu(chat_id, admin_id):
        d = drafts[admin_id]
        sub_mark = "✅" if d.get("channels") else "⬜"
        inv_mark = "✅" if d.get("invite_count") else "⬜"
        none_mark = "✅" if d.get("no_conditions") else "⬜"
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton(f"{sub_mark} Подписка на канал", callback_data="cond:sub"),
            types.InlineKeyboardButton(f"{inv_mark} Пригласить друзей", callback_data="cond:inv"),
            types.InlineKeyboardButton(f"{none_mark} Нет условий", callback_data="cond:none"),
            types.InlineKeyboardButton("➡️ Далее", callback_data="cond:next"),
            types.InlineKeyboardButton("❌ Отменить", callback_data="adm:cancel"),
        )
        bot.send_message(chat_id, texts.ADMIN_CONDITIONS, parse_mode="HTML", reply_markup=markup)

    def send_preview(chat_id, admin_id):
        d = drafts[admin_id]
        text = d["post_text"]
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🎉 Участвовать (0)", url="https://t.me"))

        if isinstance(d["prize_photo"], tuple) and d["prize_photo"][0] == "video":
            bot.send_video(chat_id, d["prize_photo"][1], caption=text, parse_mode="HTML", reply_markup=markup)
        elif isinstance(d["prize_photo"], tuple) and d["prize_photo"][0] == "animation":
            bot.send_animation(chat_id, d["prize_photo"][1], caption=text, parse_mode="HTML", reply_markup=markup)
        elif d["prize_photo"]:
            bot.send_photo(chat_id, d["prize_photo"], caption=text, parse_mode="HTML", reply_markup=markup)
        else:
            bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)

        pm = types.InlineKeyboardMarkup(row_width=1)
        pm.add(
            types.InlineKeyboardButton("✅ Опубликовать", callback_data="preview:publish"),
            types.InlineKeyboardButton("❌ Отмена", callback_data="adm:cancel"),
        )
        bot.send_message(chat_id, texts.ADMIN_PREVIEW, reply_markup=pm)

    @bot.message_handler(commands=["admin"])
    def admin_cmd(message):
        if not is_admin(message.from_user.id): return
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🎁 Создать розыгрыш", callback_data="adm:create"),
            types.InlineKeyboardButton("📊 Мои розыгрыши", callback_data="adm:list"),
        )
        markup.add(
            types.InlineKeyboardButton("⭐ Выдать спины", callback_data="adm:give_spins"),
            types.InlineKeyboardButton("🎁 Выдать подарок", callback_data="adm:give_gift"),
        )
        markup.add(
            types.InlineKeyboardButton("🎟 Создать промокод", callback_data="adm:create_promo"),
            types.InlineKeyboardButton("📈 Статистика", callback_data="adm:stats"),
        )
        markup.add(
            types.InlineKeyboardButton("📢 Рассылка", callback_data="adm:broadcast"),
        )
        bot.send_message(message.chat.id, texts.ADMIN_PANEL, parse_mode="HTML", reply_markup=markup)

    # --- ВЫДАТЬ СПИНЫ ---
    @bot.callback_query_handler(func=lambda c: c.data == "adm:give_spins")
    def adm_give_spins(call):
        if not is_admin(call.from_user.id): return
        admin_states[call.from_user.id] = "give_spins_input"
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "⭐ Введи ID пользователя и количество спинов через пробел.\n\nПример: `728960655 5`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_give_spins)

    def process_give_spins(message):
        if message.from_user.id not in admin_states: return
        admin_states.pop(message.from_user.id, None)
        try:
            user_id_str, count_str = message.text.strip().split()
            user_id = int(user_id_str)
            count = int(count_str)
            success = 0
            for _ in range(count):
                try:
                    res = requests.post("http://localhost:8080/api/add-spin", json={"user_id": str(user_id)})
                    if res.status_code == 200: success += 1
                except: pass
            if success > 0:
                bot.reply_to(message, f"✅ Успешно начислено {success} спинов пользователю `{user_id}`.", parse_mode="Markdown")
                try: bot.send_message(user_id, f"🎁 Администратор выдал вам {success} спинов!")
                except: pass
                
                admin_name = message.from_user.username or message.from_user.id
                logger.log_admin(f"Админ @{admin_name} выдал {success} спинов пользователю {user_id}.")
            else:
                bot.reply_to(message, "⚠️ Не удалось начислить спины. Сервер недоступен.")
        except ValueError:
            bot.reply_to(message, "❌ Неверный формат. Нужно два числа через пробел.")

    # --- ВЫДАТЬ ПОДАРОК ---
    @bot.callback_query_handler(func=lambda c: c.data == "adm:give_gift")
    def adm_give_gift(call):
        if not is_admin(call.from_user.id): return
        admin_states[call.from_user.id] = "give_gift_input"
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "🎁 Введи ID пользователя и ID подарка через пробел.\n\nПример: `728960655 5170233102089322756`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_give_gift)

    def process_give_gift(message):
        if message.from_user.id not in admin_states: return
        admin_states.pop(message.from_user.id, None)
        try:
            user_id_str, gift_id_str = message.text.strip().split()
            user_id = int(user_id_str)
            gift_id = gift_id_str
            cur.execute("INSERT INTO winners (giveaway_id, user_id, gift_id, status) VALUES (?, ?, ?, 'pending')", (0, user_id, gift_id))
            conn.commit()
            bot.reply_to(message, f"✅ Подарок `{gift_id}` записан для пользователя `{user_id}`. Юзербот выдаст его, когда человек напишет @Biograv.", parse_mode="Markdown")
            try: bot.send_message(user_id, f"🎁 Администратор выдал вам подарок! Напишите @Biograv, чтобы получить его.")
            except: pass

            admin_name = message.from_user.username or message.from_user.id
            logger.log_admin(f"Админ @{admin_name} выдал подарок {gift_id} пользователю {user_id}.")
        except ValueError:
            bot.reply_to(message, "❌ Неверный формат. Нужно два значения через пробел.")

    # --- СОЗДАТЬ ПРОМОКОД ---
    @bot.callback_query_handler(func=lambda c: c.data == "adm:create_promo")
    def adm_create_promo(call):
        if not is_admin(call.from_user.id): return
        admin_states[call.from_user.id] = "promo_code"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🎟 Введи название промокода (например, `BIOGRAV`):", parse_mode="Markdown")

    @bot.message_handler(func=lambda m: m.from_user.id in admin_states and admin_states[m.from_user.id] == "promo_code")
    def process_promo_code(message):
        admin_states[message.from_user.id] = {"step": "promo_type", "code": message.text.strip().upper()}
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("⭐ Спины", callback_data="promo_type:spin"),
            types.InlineKeyboardButton("💎 Звёзды", callback_data="promo_type:stars")
        )
        bot.send_message(message.chat.id, "Что должно выдаваться по этому промокоду?", reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("promo_type:"))
    def process_promo_type(call):
        if not is_admin(call.from_user.id): return
        ptype = call.data.split(":")[1]
        d = admin_states.get(call.from_user.id)
        if not isinstance(d, dict): return
        
        d["type"] = ptype
        d["step"] = "promo_value"
        bot.answer_callback_query(call.id)
        
        if ptype == "spin":
            bot.send_message(call.message.chat.id, "Сколько спинов выдавать? (число)")
        else:
            bot.send_message(call.message.chat.id, "Сколько звёзд выдавать? (число)")

    @bot.message_handler(func=lambda m: m.from_user.id in admin_states and isinstance(admin_states[m.from_user.id], dict) and admin_states[m.from_user.id].get("step") == "promo_value")
    def process_promo_value(message):
        d = admin_states.get(message.from_user.id)
        if not d: return
        d["value"] = message.text.strip()
        d["step"] = "promo_limit"
        bot.send_message(message.chat.id, "Сколько раз можно использовать этот промокод? (введи число, например, 50)")

    @bot.message_handler(func=lambda m: m.from_user.id in admin_states and isinstance(admin_states[m.from_user.id], dict) and admin_states[m.from_user.id].get("step") == "promo_limit")
    def process_promo_limit(message):
        d = admin_states.pop(message.from_user.id, None)
        if not d: return
        try:
            limit = int(message.text.strip())
            cur.execute("INSERT INTO promocodes (code, reward_type, reward_value, max_uses) VALUES (?, ?, ?, ?)",
                (d["code"], d["type"], d["value"], limit))
            conn.commit()
            bot.send_message(message.chat.id, f"✅ Промокод `{d['code']}` создан на {limit} активаций!", parse_mode="Markdown")
            
            admin_name = message.from_user.username or message.from_user.id
            logger.log_admin(f"Админ @{admin_name} создал промокод {d['code']} (награда: {d['type']} {d['value']}, лимит: {limit}).")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка при сохранении промокода: {e}")

    # --- СТАТИСТИКА ---
    @bot.callback_query_handler(func=lambda c: c.data == "adm:stats")
    def adm_stats(call):
        if not is_admin(call.from_user.id): return
        cur.execute("SELECT COUNT(*) FROM users")
        users = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM giveaways WHERE status='active'")
        active_gws = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM winners")
        total_wins = cur.fetchone()[0]
        text = (
            f"📈 <b>Статистика бота</b>\n\n"
            f"👥 Пользователей: {users}\n"
            f"🎁 Активных розыгрышей: {active_gws}\n"
            f"🏆 Всего выигрышей: {total_wins}"
        )
        bot.send_message(call.message.chat.id, text, parse_mode="HTML")

    # --- РАССЫЛКА ---
    @bot.callback_query_handler(func=lambda c: c.data == "adm:broadcast")
    def adm_broadcast(call):
        if not is_admin(call.from_user.id): return
        admin_states[call.from_user.id] = "broadcast"
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "📢 Введи текст рассылки (можно с картинкой):")
        bot.register_next_step_handler(msg, process_broadcast)

    def process_broadcast(message):
        admin_states.pop(message.from_user.id, None)
        cur.execute("SELECT user_id FROM users")
        users = cur.fetchall()
        success = 0
        for (uid,) in users:
            try:
                bot.copy_message(uid, message.chat.id, message.message_id)
                success += 1
                time.sleep(0.05)
            except: pass
        bot.reply_to(message, f"✅ Рассылка завершена. Доставлено: {success} из {len(users)}.")
        
        admin_name = message.from_user.username or message.from_user.id
        logger.log_admin(f"Админ @{admin_name} сделал рассылку (доставлено {success} из {len(users)}).")

    # --- СОЗДЕНИЕ РОЗЫГРЫША (FSM С ВЫБОРОМ ПОДАРКА) ---
    @bot.callback_query_handler(func=lambda c: c.data == "adm:create")
    def adm_create(call):
        if not is_admin(call.from_user.id): return
        drafts[call.from_user.id] = {
            "step": "gift_type", 
            "channels": [], 
            "invite_count": 0, 
            "no_conditions": False,
            "gift_type": None,
            "gift_id": None
        }
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("💎 NFT подарок", callback_data="gift_type:nft"),
            types.InlineKeyboardButton("🎁 Обычный подарок", callback_data="gift_type:regular")
        )
        markup.add(types.InlineKeyboardButton("❌ Отменить", callback_data="adm:cancel"))
        
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🎁 <b>Выбери тип розыгрыша:</b>\n\nКакая награда будет выдаваться победителям?", parse_mode="HTML", reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("gift_type:"))
    def process_gift_type(call):
        if not is_admin(call.from_user.id): return
        d = drafts.get(call.from_user.id)
        if not d or d.get("step") != "gift_type": return
        
        gtype = call.data.split(":")[1]
        bot.answer_callback_query(call.id)
        
        if gtype == "nft":
            d["gift_type"] = "nft"
            d["step"] = "post_text"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("❌ Отменить", callback_data="adm:cancel"))
            msg = bot.send_message(call.message.chat.id, "📝 <b>Шаг 1 из 6 — Пост</b>\n\nПришли мне текст розыгрыша или перешли готовый пост.", parse_mode="HTML", reply_markup=markup)
            d["last_msg_id"] = msg.message_id
            
        elif gtype == "regular":
            d["gift_type"] = "regular"
            d["step"] = "select_regular_gift"
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            buttons = []
            for key, gift_info in GIFTS.items():
                buttons.append(types.InlineKeyboardButton(
                    f"{gift_info['emoji']} {gift_info['name']}", 
                    callback_data=f"select_gift:{key}"
                ))
            markup.add(*buttons)
            markup.add(types.InlineKeyboardButton("❌ Отменить", callback_data="adm:cancel"))
            
            bot.send_message(call.message.chat.id, "🧸 <b>Выбери, какой именно подарок выдать автоматически:</b>", parse_mode="HTML", reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("select_gift:"))
    def process_select_gift(call):
        if not is_admin(call.from_user.id): return
        d = drafts.get(call.from_user.id)
        if not d or d.get("step") != "select_regular_gift": return
        
        gift_key = call.data.split(":")[1]
        if gift_key in GIFTS:
            d["gift_id"] = GIFTS[gift_key]["id"]
            d["gift_name"] = GIFTS[gift_key]["name"]
            
        d["step"] = "post_text"
        bot.answer_callback_query(call.id, f"Выбран: {d.get('gift_name', gift_key)}")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Отменить", callback_data="adm:cancel"))
        msg = bot.send_message(call.message.chat.id, f"✅ Подарок выбран успешно.\n\n📝 <b>Шаг 1 из 6 — Пост</b>\n\nПришли мне текст розыгрыша или перешли готовый пост.", parse_mode="HTML", reply_markup=markup)
        d["last_msg_id"] = msg.message_id

    @bot.message_handler(func=guard("post_text"), content_types=["text", "photo", "video", "animation"])
    def step_post_text(message):
        html_text = message.html_text if message.html_text else message.text
        d = drafts[message.from_user.id]
        d["post_text"] = html_text
        if message.content_type == "photo": d["prize_photo"] = message.photo[-1].file_id
        elif message.content_type == "video": d["prize_photo"] = ("video", message.video.file_id)
        elif message.content_type == "animation": d["prize_photo"] = ("animation", message.animation.file_id)
        else: d["prize_photo"] = None
        d["step"] = "winners"
        bot.send_message(message.chat.id, texts.ADMIN_STEP_WINNERS, parse_mode="HTML")

    @bot.message_handler(func=guard("winners"))
    def step_winners(message):
        try:
            n = int(message.text.strip())
            assert 1 <= n <= 100
        except Exception:
            bot.send_message(message.chat.id, texts.ADMIN_WINNERS_BAD)
            return
        drafts[message.from_user.id]["winners_count"] = n
        drafts[message.from_user.id]["step"] = "conditions"
        send_conditions_menu(message.chat.id, message.from_user.id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("cond:"))
    def cond_handler(call):
        if not is_admin(call.from_user.id): return
        d = drafts.get(call.from_user.id)
        if not d or d["step"] != "conditions": return
        action = call.data.split(":")[1]
        if action == "sub":
            d["step"] = "channels_input"
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, texts.ADMIN_CHANNELS_INPUT)
        elif action == "inv":
            d["step"] = "invite_count"
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, texts.ADMIN_INVITE_COUNT)
        elif action == "none":
            d["no_conditions"] = True
            d["channels"] = []
            d["invite_count"] = 0
            bot.answer_callback_query(call.id, "Условия сброшены")
            send_conditions_menu(call.message.chat.id, call.from_user.id)
        elif action == "next":
            if not d.get("no_conditions") and not d.get("channels") and not d.get("invite_count"):
                bot.answer_callback_query(call.id, texts.ADMIN_NEED_CONDITION, show_alert=True)
                return
            d["step"] = "end_at"
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, texts.ADMIN_END_AT, parse_mode="HTML")

    @bot.message_handler(func=guard("channels_input"))
    def step_channels(message):
        if message.text == "/done":
            d = drafts[message.from_user.id]
            if not d["channels"]:
                bot.send_message(message.chat.id, "Ты не добавил ни одного канала.")
                return
            d["step"] = "conditions"
            bot.send_message(message.chat.id, "✅ Каналы добавлены.")
            send_conditions_menu(message.chat.id, message.from_user.id)
            return
        line = message.text.strip()
        if "|" in line:
            chat_id, link = [x.strip() for x in line.split("|", 1)]
            entry = {"chat_id": chat_id, "invite_link": link}
        else:
            if not line.startswith("@"):
                bot.send_message(message.chat.id, "Публичный канал должен начинаться с @")
                return
            entry = {"chat_id": line, "invite_link": f"https://t.me{line[1:]}"}
        drafts[message.from_user.id]["channels"].append(entry)
        bot.send_message(message.chat.id, f"✅ Добавлен {entry['chat_id']}. Пришли следующий или /done")

    @bot.message_handler(func=guard("invite_count"))
    def step_invite_count(message):
        try:
            n = int(message.text.strip())
            assert 1 <= n <= 50
        except Exception:
            bot.send_message(message.chat.id, texts.ADMIN_INVITE_BAD)
            return
        drafts[message.from_user.id]["invite_count"] = n
        drafts[message.from_user.id]["step"] = "conditions"
        bot.send_message(message.chat.id, f"✅ Нужно пригласить: {n} новых друга.")
        send_conditions_menu(message.chat.id, message.from_user.id)

    @bot.message_handler(func=guard("end_at"))
    def step_end_at(message):
        try:
            dt = datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        except ValueError:
            bot.send_message(message.chat.id, texts.ADMIN_END_AT_BAD)
            return
        if dt <= datetime.now():
            bot.send_message(message.chat.id, texts.ADMIN_END_AT_PAST)
            return
        drafts[message.from_user.id]["end_at"] = dt.strftime("%Y-%m-%d %H:%M")
        drafts[message.from_user.id]["step"] = "preview"
        send_preview(message.chat.id, message.from_user.id)

    @bot.callback_query_handler(func=lambda c: c.data == "preview:publish")
    def preview_publish(call):
        if not is_admin(call.from_user.id): return
        d = drafts.get(call.from_user.id)
        if not d: return

        bot_username = bot.get_me().username
        text = d["post_text"]
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🎉 Участвовать (0)", url=f"https://t.me{bot_username}?start=join_pending"))

        if isinstance(d["prize_photo"], tuple) and d["prize_photo"][0] == "video":
            msg = bot.send_video(CHANNEL_ID, d["prize_photo"][1], caption=text, parse_mode="HTML", reply_markup=markup)
        elif isinstance(d["prize_photo"], tuple) and d["prize_photo"][0] == "animation":
            msg = bot.send_animation(CHANNEL_ID, d["prize_photo"][1], caption=text, parse_mode="HTML", reply_markup=markup)
        elif d["prize_photo"]:
            msg = bot.send_photo(CHANNEL_ID, d["prize_photo"], caption=text, parse_mode="HTML", reply_markup=markup)
        else:
            msg = bot.send_message(CHANNEL_ID, text, parse_mode="HTML", reply_markup=markup)

        cur.execute(
            "INSERT INTO giveaways (status, prize_text, prize_photo, winners_count, required_channels, invite_count, no_conditions, end_at, channel_id, message_id, gift_type, gift_id) "
            "VALUES ('active',?,?,?,?,?,?,?,?,?,?,?)",
            (
                text, str(d["prize_photo"]) if d["prize_photo"] else None, d["winners_count"],
                json.dumps(d["channels"]), d["invite_count"],
                1 if d["no_conditions"] else 0,
                d["end_at"], str(CHANNEL_ID), msg.message_id,
                d.get("gift_type"), d.get("gift_id")
            )
        )
        conn.commit()
        gid = cur.lastrowid

        new_markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🎉 Участвовать (0)", url=f"https://t.me{bot_username}?start=join_{gid}"))
        try:
            bot.edit_message_reply_markup(CHANNEL_ID, msg.message_id, reply_markup=new_markup)
        except: pass

        drafts.pop(call.from_user.id, None)
        bot.answer_callback_query(call.id, "✅ Опубликовано")
        bot.send_message(call.message.chat.id, texts.ADMIN_PUBLISHED.format(gid=gid))

        admin_name = call.from_user.username or call.from_user.id
        logger.log_admin(f"Админ @{admin_name} создал розыгрыш #{gid}.")

    @bot.callback_query_handler(func=lambda c: c.data in ["adm:cancel", "preview:cancel"])
    def cancel_handler(call):
        drafts.pop(call.from_user.id, None)
        bot.answer_callback_query(call.id, "Отменено")
        bot.send_message(call.message.chat.id, "❌ Действие отменено.")

    @bot.callback_query_handler(func=lambda c: c.data == "adm:list")
    def adm_list(call):
        if not is_admin(call.from_user.id): return
        cur.execute("SELECT id, status, prize_text FROM giveaways WHERE status!='deleted' ORDER BY id DESC LIMIT 20")
        rows = cur.fetchall()
        if not rows:
            bot.send_message(call.message.chat.id, "Розыгрышей пока нет.")
            return
        markup = types.InlineKeyboardMarkup(row_width=1)
        for gid, status, prize in rows:
            emoji = {"active": "🟢", "finished": "⚪"}.get(status, "⚪")
            clean_prize = re.sub('<[^>]+>', '', prize or "")[:30]
            markup.add(types.InlineKeyboardButton(f"{emoji} #{gid} — {clean_prize}...", callback_data=f"admgw:{gid}"))
        bot.send_message(call.message.chat.id, "📊 Твои розыгрыши:", reply_markup=markup)

    # --- УПРАВЛЕНИЕ КОНКРЕТНЫМ РОЗЫГРЫШЕМ ---
    @bot.callback_query_handler(func=lambda c: c.data.startswith("admgw:"))
    def adm_gw(call):
        if not is_admin(call.from_user.id): return
        gid = int(call.data.split(":")[1])
        gw = get_giveaway(gid)
        cur.execute("SELECT COUNT(*) FROM participants WHERE giveaway_id=?", (gid,))
        participants = cur.fetchone()[0]
        
        text = (
            f"🎁 <b>Розыгрыш #{gid}</b>\n\n"
            f"👥 Участников: {participants}\n"
            f"🏆 Победителей: {gw['winners_count']}\n"
            f"⏰ Итоги: {texts.format_date(gw['end_at'])}\n"
            f"Статус: {gw['status']}"
        )
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🛑 Завершить досрочно", callback_data=f"admfinish:{gid}"),
            types.InlineKeyboardButton("🗑 Удалить", callback_data=f"admdel:{gid}"),
            types.InlineKeyboardButton("⬅️ Назад", callback_data="adm:list"),
        )
        bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("admfinish:"))
    def adm_finish(call):
        gid = int(call.data.split(":")[1])
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("✅ Да, завершить", callback_data=f"admfinish_yes:{gid}"),
            types.InlineKeyboardButton("❌ Отмена", callback_data=f"admgw:{gid}"),
        )
        bot.send_message(call.message.chat.id, f"⚠️ Завершить розыгрыш #{gid} досрочно?", reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("admfinish_yes:"))
    def adm_finish_yes(call):
        gid = int(call.data.split(":")[1])
        from tasks import finish_giveaway
        finish_giveaway(bot, gid, admin_chat_id=call.message.chat.id)
        bot.answer_callback_query(call.id, "✅ Завершено")
        
        admin_name = call.from_user.username or call.from_user.id
        logger.log_admin(f"Админ @{admin_name} завершил розыгрыш #{gid} досрочно.")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("admdel:"))
    def adm_del(call):
        gid = int(call.data.split(":")[1])
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("✅ Да, удалить", callback_data=f"admdel_yes:{gid}"),
            types.InlineKeyboardButton("❌ Отмена", callback_data=f"admgw:{gid}"),
        )
        bot.send_message(call.message.chat.id, f"⚠️ Удалить розыгрыш #{gid}?", reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("admdel_yes:"))
    def adm_del_yes(call):
        gid = int(call.data.split(":")[1])
        gw = get_giveaway(gid)
        if gw:
            try: 
                bot.delete_message(gw["channel_id"], gw["message_id"])
            except Exception: 
                pass
            cur.execute("UPDATE giveaways SET status='deleted' WHERE id=?", (gid,))
            conn.commit()
        bot.send_message(call.message.chat.id, "🗑 Розыгрыш удалён.")
        
        # ЛОГ В КАНАЛ
        admin_name = call.from_user.username or call.from_user.id
        logger.log_admin(f"Админ @{admin_name} удалил розыгрыш #{gid}.")

    return None

