# Copyright (c) 2026 THE SHIV
# Licensed under the MIT License.
# This file is part of MahiMusic
# DEVELOPER - THE SHIV

import asyncio
from pyrogram import enums, filters, types
from pyrogram.errors import MessageNotModified

from AloneX import app, config, db, lang
from AloneX.helpers import buttons, utils


@app.on_message(filters.command(["help"]) & filters.private & ~app.bl_users)
@lang.language()
async def _help(_, m: types.Message):
    await m.reply_text(
        text=m.lang["help_menu"],
        reply_markup=buttons.help_markup(m.lang),
        quote=True,
    )


@app.on_message(filters.command(["start"]))
@lang.language()
async def start(_, message: types.Message):
    if message.from_user.id in app.bl_users and message.from_user.id not in db.notified:
        return await message.reply_text(message.lang["bl_user_notify"])

    private = message.chat.type == enums.ChatType.PRIVATE

    # --- LOADING ANIMATION SEQUENCE FOR PRIVATE CHAT ---
    if private:
        loading_1 = await message.reply_text("<b>ᴌᴏᴀᴅɪɴɢ....</b>")
        await asyncio.sleep(0.3)
        await loading_1.edit_text("<b>ꜱᴛᴀʀᴛɪɴɢ..ʙᴀʙʏ.❤️❤️</b>")
        await asyncio.sleep(0.3)
        await loading_1.edit_text("<b>ɪ ᴀᴍ ᴀʟɪᴠᴇ ʙᴀʙʏ❤️😌🫣🫣</b>")
        await asyncio.sleep(0.5)
        await loading_1.edit_text("<b>𝐙𝐀𝐘𝐍 ʙᴏᴛs🫣🫣.</b>")
        await asyncio.sleep(0.5)
        await loading_1.delete()

    # --- HANDLE /start help ---
    if len(message.command) > 1 and message.command[1] == "help":
        if private:
            # Sticker Before Image in /start help
            await message.reply_sticker("CAACAgUAAxkBAAFJgZ1qBGwx9Z9vW5BhG3dw0l1A5j4CyQACXRYAAuc-wVWs4--9DGlDKzsE")
        return await _help(_, message)

    _text = (
        message.lang["start_pm"].format(message.from_user.first_name, app.name)
        if private
        else message.lang["start_gp"].format(app.name)
    )

    key = buttons.start_key(message.lang, private)
    
    # --- SEND IMAGE BELOW TEXT ---
    await message.reply_photo(
        photo=config.START_IMG,
        caption=_text,
        reply_markup=key,
        quote=not private
    )

    if private:
        if await db.is_user(message.from_user.id):
            return
        await utils.send_log(message)
        await db.add_user(message.from_user.id)
    else:
        if await db.is_chat(message.chat.id):
            return
        await utils.send_log(message, True)
        await db.add_chat(message.chat.id)


@app.on_message(filters.command(["playmode", "settings"]) & filters.group & ~app.bl_users)
@lang.language()
async def settings(_, message: types.Message):
    admin_only = await db.get_play_mode(message.chat.id)
    cmd_delete = await db.get_cmd_delete(message.chat.id)
    _language = await db.get_lang(message.chat.id)
    await message.reply_text(
        text=message.lang["start_settings"].format(message.chat.title),
        reply_markup=buttons.settings_markup(
            message.lang, admin_only, cmd_delete, _language, message.chat.id
        ),
        quote=True,
    )


@app.on_message(filters.new_chat_members, group=7)
@lang.language()
async def _new_member(_, message: types.Message):
    if message.chat.type != enums.ChatType.SUPERGROUP:
        return await message.chat.leave()

    await asyncio.sleep(3)
    for member in message.new_chat_members:
        if member.id == app.id:
            if await db.is_chat(message.chat.id):
                return
            await utils.send_log(message, True)
            await db.add_chat(message.chat.id)


# ==========================================
# 🛠️ EDIT SYSTEM FOR HELP, START & CLOSE 🛠️
# ==========================================

@app.on_callback_query(filters.regex(r"^help(?: (.*))?$") & ~app.bl_users)
@lang.language()
async def unified_help_menu_cb(_, query: types.CallbackQuery):
    module = query.matches[0].group(1)
    private = query.message.chat.type == enums.ChatType.PRIVATE

    try:
        if not module: 
            await query.message.edit_caption(
                caption=query.lang["help_menu"],
                reply_markup=buttons.help_markup(query.lang)
            )
        elif module == "home": 
            _text = (
                query.lang["start_pm"].format(query.from_user.first_name, app.name)
                if private
                else query.lang["start_gp"].format(app.name)
            )
            await query.message.edit_caption(
                caption=_text,
                reply_markup=buttons.start_key(query.lang, private)
            )
        else: 
            await query.message.edit_caption(
                caption=query.lang[f"help_{module}"],
                reply_markup=buttons.help_markup(query.lang, back=True)
            )
    except MessageNotModified:
        pass
    except Exception as e:
        print(f"Edit Error: {e}")
        
    await query.answer()

@app.on_callback_query(filters.regex("^(close|close_panel)$") & ~app.bl_users)
async def close_menu_cb(_, query: types.CallbackQuery):
    try:
        await query.message.delete()
    except Exception:
        pass
    await query.answer()
