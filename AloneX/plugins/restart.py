# Copyright (c) 2026 THE SHIV
# Licensed under the MIT License.
# This file is part of MahiMusic
# DEVELOPER - THE SHIV

import os
import sys
import shutil
import asyncio

from pyrogram import filters, types
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from AloneX import app, db, lang, stop


@app.on_message(filters.command(["logs"]) & app.sudoers)
@lang.language()
async def _logs(_, m: types.Message):
    sent = await m.reply_text(m.lang["log_fetch"])
    if not os.path.exists("log.txt"):
        return await sent.edit_text(m.lang["log_not_found"])

    await m.reply_document(
        document="log.txt",
        caption=m.lang["log_sent"].format(app.name),
    )
    await sent.delete()


@app.on_message(filters.command(["logger"]) & app.sudoers)
@lang.language()
async def _logger(_, m: types.Message):
    if len(m.command) < 2:
        return await m.reply_text(m.lang["logger_usage"].format(m.command[0]))
    if m.command[1] not in ("on", "off"):
        return await m.reply_text(m.lang["logger_usage"].format(m.command[0]))

    if m.command[1] == "on":
        await db.set_logger(True)
        await m.reply_text(m.lang["logger_on"])
    else:
        await db.set_logger(False)
        await m.reply_text(m.lang["logger_off"])


# ==========================================
# 🔄 RESTART COMMAND WITH INLINE BUTTONS
# ==========================================
@app.on_message(filters.command(["restart"]) & app.sudoers)
@lang.language()
async def _restart(_, m: types.Message):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔄 ʀᴇsᴛᴀʀᴛ", callback_data="bot_reboot"),
                InlineKeyboardButton("⬇️ ᴜᴘᴅᴀᴛᴇ", callback_data="bot_update")
            ],
            [
                InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data="bot_cancel")
            ]
        ]
    )
    
    await m.reply_text(
        "<blockquote><b>⚠️ ᴡʜᴀᴛ ᴅᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴅᴏ ᴡɪᴛʜ ᴛʜᴇ ʙᴏᴛ?</b></blockquote>",
        reply_markup=keyboard
    )


# ==========================================
# 🛠️ CALLBACK HANDLERS FOR RESTART MENU 🛠️
# ==========================================

# Yeh function humara common restart logic run karega
async def reboot_system():
    for directory in ["cache", "downloads"]:
        shutil.rmtree(directory, ignore_errors=True)

    asyncio.create_task(stop())
    await asyncio.sleep(2)

    try:
        os.remove("log.txt")
    except:
        pass

    os.execl(sys.executable, sys.executable, "-m", "AloneX")


@app.on_callback_query(filters.regex("^bot_reboot$") & app.sudoers)
async def restart_cb(_, query: types.CallbackQuery):
    await query.message.edit_text("<blockquote><b>🔄 ʀᴇsᴛᴀʀᴛɪɴɢ ʙᴏᴛ... ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ.</b></blockquote>")
    await reboot_system()


@app.on_callback_query(filters.regex("^bot_update$") & app.sudoers)
async def update_cb(_, query: types.CallbackQuery):
    await query.message.edit_text("<blockquote><b>⬇️ ꜰᴇᴛᴄʜɪɴɢ ᴜᴘᴅᴀᴛᴇs ꜰʀᴏᴍ ɢɪᴛ (ꜰᴏʀᴄᴇ ᴘᴜʟʟ)...</b></blockquote>")
    try:
        # 🛠️ FIXED: Added Force Pull & Clean logic so it never gets stuck
        cmd = "git fetch --all && git reset --hard HEAD && git clean -fd && git pull"
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        # Combining both stdout and stderr for better error detection
        out = (stdout.decode() + stderr.decode()).strip()
        
        # Checking Git Output
        if "Already up to date." in out:
            return await query.message.edit_text("<blockquote><b>✅ ʙᴏᴛ ɪs ᴀʟʀᴇᴀᴅʏ ᴜᴘ-ᴛᴏ-ᴅᴀᴛᴇ!\n\nɴᴏ ɴᴇᴇᴅ ᴛᴏ ʀᴇsᴛᴀʀᴛ.</b></blockquote>")
            
        elif "fatal:" in out or "error:" in out.lower():
            return await query.message.edit_text(f"<blockquote><b>❌ ᴜᴘᴅᴀᴛᴇ ꜰᴀɪʟᴇᴅ:</b>\n\n<code>{out[:1000]}</code></blockquote>")
            
        else:
            await query.message.edit_text(f"<blockquote><b>✅ ᴜᴘᴅᴀᴛᴇ sᴜᴄᴄᴇssꜰᴜʟ!</b>\n\n<code>{out[:1000]}</code>\n\n<b>🔄 ʀᴇsᴛᴀʀᴛɪɴɢ ɴᴏᴡ...</b></blockquote>")
            await reboot_system()
            
    except Exception as e:
        await query.message.edit_text(f"<blockquote><b>❌ ᴜᴘᴅᴀᴛᴇ ᴇʀʀᴏʀ:</b>\n\n<code>{str(e)}</code></blockquote>")


@app.on_callback_query(filters.regex("^bot_cancel$") & app.sudoers)
async def cancel_cb(_, query: types.CallbackQuery):
    await query.answer("❌ ᴀᴄᴛɪᴏɴ ᴄᴀɴᴄᴇʟʟᴇᴅ", show_alert=False)
    await query.message.delete()
