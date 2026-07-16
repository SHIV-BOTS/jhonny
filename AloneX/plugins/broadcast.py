# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic

import os
import time
import asyncio
from pyrogram import errors, filters, types
from pyrogram.enums import ChatMembersFilter
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# Using standard AloneX imports
from config import MONGO_DB_URI
from AloneX import app, db, lang

IS_BROADCASTING = False

# ==========================================
# PROGRESS BAR HELPER
# ==========================================
def get_progress_bar(current, total, length=20):
    if total == 0:
        return "▱" * length
    percent = current / total
    filled_len = int(length * percent)
    bar = "▰" * filled_len + "▱" * (length - filled_len)
    return bar

# ==========================================
# SELF PROMO DATABASE SETUP
# ==========================================
dbclient = AsyncIOMotorClient(MONGO_DB_URI)
promo_db = dbclient.AloneXPromo
promo_msgs_db = promo_db.promo_messages
promo_toggle_db = promo_db.promo_settings
broadcast_time_db = promo_db.promo_time

async def is_promo_on() -> bool:
    chat = await promo_toggle_db.find_one({"_id": "promo_toggle"})
    if not chat:
        return False
    return chat.get("status", False)

async def set_promo_status(status: bool):
    await promo_toggle_db.update_one({"_id": "promo_toggle"}, {"$set": {"status": status}}, upsert=True)

async def save_promo_msg(chat_id: int, message_id: int):
    await promo_msgs_db.insert_one({"chat_id": chat_id, "message_id": message_id, "timestamp": int(time.time())})

async def get_old_promo_msgs():
    time_limit = int(time.time()) - 172800 # 48 hours
    return promo_msgs_db.find({"timestamp": {"$lt": time_limit}})

async def delete_promo_record(chat_id: int, message_id: int):
    await promo_msgs_db.delete_one({"chat_id": chat_id, "message_id": message_id})

# ==========================================
# SELF PROMO ASSETS
# ==========================================
PROMO_IMAGE = "https://n.uguu.se/EBVPCnuG.jpg"
PROMO_TEXT = """
⊚ ᴛʜɪꜱ ɪꜱ [˹♪ Mariya x Music ♪˼ \[ 💌 \]](https://t.me/royal_musics_bot)

➻ ᴧ ᴘʀєᴍɪᴜᴍ ᴅєꜱɪɢηєᴅ ϻᴜꜱɪᴄ ᴘʟᴧʏєʀ ʙσᴛ ꜰσʀ ᴛєʟєɢʀᴧϻ ɢʀσᴜᴘ & ᴄʜᴧηηєʟ. 
🎧 24x7 ᴍᴜꜱɪᴄ • ꜱᴍᴏᴏᴛʜ ᴀɴᴅ ꜰᴀꜱᴛ ᴘʟᴀʏʙᴀᴄᴋ

⚡️ ᴇɴᴊᴏʏ ᴜɴʟɪᴍɪᴛᴇᴅ ꜱᴏɴɢꜱ, qᴜɪᴄᴋ ʀᴇꜱᴘᴏɴꜱᴇ, ᴀɴᴅ ᴄʟᴇᴀʀ ᴀᴜᴅɪᴏ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ.

ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ, ᴍᴀᴋᴇ ᴍᴇ ᴀᴅᴍɪɴ, ᴀɴᴅ ꜱᴇɴᴅ /play song name ᴛᴏ ꜱᴛᴀʀᴛ ᴛʜᴇ ᴍᴜꜱɪᴄ.
"""
PROMO_BUTTON = InlineKeyboardMarkup(
    [[InlineKeyboardButton("🎵 Aᴅᴅ ᴍᴇ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ 🎧", url=f"https://t.me/{app.username}?startgroup=true")]]
)

# ==========================================
# MAIN BROADCAST COMMAND (Upgraded)
# ==========================================
@app.on_message(filters.command(["broadcast", "gcast"]) & app.sudoers)
@lang.language()
async def _broadcast(_, message: types.Message):
    global IS_BROADCASTING
    if IS_BROADCASTING:
        return await message.reply_text(message.lang["gcast_active"])

    if message.reply_to_message:
        x = message.reply_to_message.id
        y = message.chat.id
        query = message.text
    else:
        if len(message.command) < 2:
            return await message.reply_text(message.lang["gcast_usage"])
        query = message.text.split(None, 1)[1]
        
        # Checking flags
        if "-pinloud" in query:
            query = query.replace("-pinloud", "")
        elif "-pin" in query:
            query = query.replace("-pin", "")
            
        if "-nobot" in query:
            query = query.replace("-nobot", "")
        if "-user" in query:
            query = query.replace("-user", "")
            
        if query.strip() == "":
            return await message.reply_text("Please provide text to broadcast.")

    IS_BROADCASTING = True
    sent_msg = await message.reply_text(message.lang["gcast_start"])

    # Log to logger group
    await (await app.send_message(
        chat_id=app.logger, 
        text=message.lang["gcast_log"].format(
            message.from_user.id,
            message.from_user.mention,
            message.text,
        )
    )).pin(disable_notification=False)
    
    await asyncio.sleep(2)

    sent, pin, susr = 0, 0, 0
    failed = ""

    # Broadcast to Groups
    if "-nobot" not in message.text:
        chats = await db.get_chats()
        for chat in chats:
            if not IS_BROADCASTING:
                break
            chat_id = chat["chat_id"] if isinstance(chat, dict) else chat
            try:
                m = (
                    await app.forward_messages(chat_id, y, x)
                    if message.reply_to_message
                    else await app.send_message(chat_id, text=query)
                )
                if "-pinloud" in message.text:
                    try:
                        await m.pin(disable_notification=False)
                        pin += 1
                    except Exception:
                        pass
                elif "-pin" in message.text:
                    try:
                        await m.pin(disable_notification=True)
                        pin += 1
                    except Exception:
                        pass
                sent += 1
                await asyncio.sleep(0.1)
            except FloodWait as fw:
                await asyncio.sleep(fw.value + 3)
            except Exception as ex:
                failed += f"{chat_id} - {ex}\n"
                continue

    # Broadcast to Users
    if "-user" in message.text:
        users = await db.get_users()
        for user in users:
            if not IS_BROADCASTING:
                break
            user_id = user["user_id"] if isinstance(user, dict) else user
            try:
                m = (
                    await app.forward_messages(user_id, y, x)
                    if message.reply_to_message
                    else await app.send_message(user_id, text=query)
                )
                susr += 1
                await asyncio.sleep(0.1)
            except FloodWait as fw:
                await asyncio.sleep(fw.value + 3)
            except Exception as ex:
                failed += f"{user_id} - {ex}\n"
                continue

    text = f"**Broadcast Completed!**\n\n**Groups:** {sent} (Pinned: {pin})\n**Users:** {susr}"
    
    # Generate error file if it failed sending to some chats
    if failed:
        with open("errors.txt", "w") as f:
            f.write(failed)
        await message.reply_document(
            document="errors.txt",
            caption=text,
        )
        os.remove("errors.txt")
    else:
        await sent_msg.edit_text(text)
        
    IS_BROADCASTING = False

@app.on_message(filters.command(["stop_gcast", "stop_broadcast"]) & app.sudoers)
@lang.language()
async def _stop_gcast(_, message: types.Message):
    global IS_BROADCASTING
    if not IS_BROADCASTING:
        return await message.reply_text(message.lang["gcast_inactive"])

    IS_BROADCASTING = False
    await (await app.send_message(
        chat_id=app.logger,
        text=message.lang["gcast_stop_log"].format(
            message.from_user.id,
            message.from_user.mention
        )
    )).pin(disable_notification=False)
    await message.reply_text(message.lang["gcast_stop"])

# ==========================================
# SELF PROMO BROADCAST LOGIC
# ==========================================
async def run_promo_broadcast(status_message=None):
    await broadcast_time_db.update_one({"_id": "last_run"}, {"$set": {"time": int(time.time())}}, upsert=True)
    
    users = await db.get_users()
    chats = await db.get_chats()

    total_users = len(users)
    total_chats = len(chats)
    total_targets = total_users + total_chats

    u_success, u_failed = 0, 0
    g_success, g_failed = 0, 0
    completed = 0

    async def update_progress():
        if status_message and completed % 10 == 0:  # Update message every 10 sends to avoid floodwait
            bar = get_progress_bar(completed, total_targets)
            percent = int((completed / total_targets) * 100) if total_targets else 100
            text = (
                f"🔄 **Live Promo Broadcasting...**\n\n"
                f"[{bar}] **{percent}%**\n\n"
                f"👥 **Users:** ✅ {u_success} | ❌ {u_failed}\n"
                f"🏘 **Groups:** ✅ {g_success} | ❌ {g_failed}"
            )
            try:
                await status_message.edit_text(text)
            except Exception:
                pass

    for user in users:
        user_id = user["user_id"] if isinstance(user, dict) else user
        try:
            msg = await app.send_photo(chat_id=int(user_id), photo=PROMO_IMAGE, caption=PROMO_TEXT, reply_markup=PROMO_BUTTON)
            await save_promo_msg(int(user_id), msg.id)
            u_success += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            u_failed += 1
        
        completed += 1
        await update_progress()
        await asyncio.sleep(0.5)

    for chat in chats:
        chat_id = chat["chat_id"] if isinstance(chat, dict) else chat
        try:
            msg = await app.send_photo(chat_id=int(chat_id), photo=PROMO_IMAGE, caption=PROMO_TEXT, reply_markup=PROMO_BUTTON)
            await save_promo_msg(int(chat_id), msg.id)
            g_success += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            g_failed += 1
        
        completed += 1
        await update_progress()
        await asyncio.sleep(0.5)

    return u_success, u_failed, g_success, g_failed


@app.on_message(filters.command(["selfpromo", "promo"]) & app.sudoers)
async def promo_toggle_cmd(client, message):
    if len(message.command) != 2:
        return await message.reply_text(
            "**Usage Options:**\n"
            "`/selfpromo on` - Start auto 24-hour broadcast\n"
            "`/selfpromo off` - Stop auto broadcast\n"
            "`/selfpromo run` - Instantly broadcast right now"
        )
    
    state = message.command[1].lower()
    
    if state == "on":
        await set_promo_status(True)
        await message.reply_text("✅ **Auto Self Promo Started!**\nBot will broadcast every 24 hours.")
    elif state == "off":
        await set_promo_status(False)
        await message.reply_text("❌ **Auto Self Promo Stopped!**")
    elif state == "run":
        status_msg = await message.reply_text("🔄 **Calculating stats & initializing broadcast...**")
        try:
            u_success, u_failed, g_success, g_failed = await run_promo_broadcast(status_message=status_msg)
            
            stats_text = (
                f"📢 **Manual Promo Completed** ✅\n\n"
                f"👥 **Users:** ✅ {u_success} | ❌ {u_failed}\n"
                f"🏘 **Groups:** ✅ {g_success} | ❌ {g_failed}"
            )
            await status_msg.edit_text(stats_text)
            
            # Send completion log to Alone logger chat
            if hasattr(app, "logger") and app.logger:
                await app.send_message(app.logger, stats_text)
        except Exception as e:
            await status_msg.edit_text(f"❌ Error: {e}")
    else:
        await message.reply_text("**Invalid argument.** Use `on`, `off`, or `run`.")


# ==========================================
# BACKGROUND TASKS
# ==========================================
async def auto_promo_task():
    while True:
        try:
            old_messages = await get_old_promo_msgs()
            async for doc in old_messages:
                try:
                    await app.delete_messages(chat_id=doc["chat_id"], message_ids=doc["message_id"])
                except Exception:
                    pass
                await delete_promo_record(doc["chat_id"], doc["message_id"])
                await asyncio.sleep(1)

            if await is_promo_on():
                last_run_data = await broadcast_time_db.find_one({"_id": "last_run"})
                last_run = last_run_data["time"] if last_run_data else 0
                
                if (int(time.time()) - last_run) >= 86400: # Runs every 24 hours
                    u_success, u_failed, g_success, g_failed = await run_promo_broadcast()
                    if hasattr(app, "logger") and app.logger:
                        stats_text = f"📢 **Auto Promo Completed**\n\n👥 **Users:** ✅ {u_success} | ❌ {u_failed}\n🏘 **Groups:** ✅ {g_success} | ❌ {g_failed}"
                        await app.send_message(app.logger, stats_text)
        except Exception:
            pass
        await asyncio.sleep(3600) # Re-checks time limit every 1 hour

# Starts background process alongside bot
asyncio.create_task(auto_promo_task())
