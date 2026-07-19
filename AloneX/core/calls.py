# Copyright (c) 2026 THE SHIV
# Licensed under the MIT License.
# This file is part of MahiMusic
# DEVELOPER - THE SHIV

import asyncio
import aiohttp
from collections import defaultdict

from ntgcalls import (ConnectionNotFound, TelegramServerError,
                      RTMPStreamingUnsupported)
from pyrogram.errors import MessageIdInvalid, FloodWait, MessageNotModified
from pyrogram.types import InputMediaPhoto, Message
from pytgcalls import PyTgCalls, exceptions, types
from pytgcalls.pytgcalls_session import PyTgCallsSession

from AloneX import app, config, db, lang, logger, queue, userbot, yt
from AloneX.helpers import Media, Track, buttons, thumb, utils, vclogger


async def _delete_msg(msg: Message, delay: int = 6):
    try:
        await asyncio.sleep(delay)
        await msg.delete()
    except Exception:
        pass


# ----------------------------------------------------
# 🚀 1. API BASED AUTOPLAY (Find Related Tracks without Cookies)
# ----------------------------------------------------
async def get_related_via_api(video_id: str, history: list):
    api_key = getattr(config, "YOUTUBE_API_KEY", None)
    if not api_key:
        return None
        
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&relatedToVideoId={video_id}&type=video&key={api_key}&maxResults=10"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get("items", []):
                        vid = item.get("id", {}).get("videoId")
                        if vid and vid not in history:
                            title = item.get("snippet", {}).get("title", "Unknown Track")
                            return Track(
                                id=vid,
                                title=title,
                                url=f"https://www.youtube.com/watch?v={vid}",
                                duration="00:00",
                                user="Autoplay",
                                video=False
                            )
    except Exception as e:
        logger.error(f"Autoplay API Error: {e}")
    return None

# ----------------------------------------------------
# 🚀 2. API BASED STREAM URL (Replaces yt.download & Cookies)
# ----------------------------------------------------
async def get_stream_via_api(video_id: str, video: bool = False):
    # 🔗 USING YOUR CUSTOM API URL HERE
    api_url = f"https://teaminflex.xyz/streams/{video_id}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    audio_streams = data.get("audioStreams", [])
                    video_streams = data.get("videoStreams", [])
                    
                    if video and video_streams:
                        # Find 720p or highest available video stream
                        stream = next((s for s in video_streams if s.get("quality") == "720p"), video_streams[0])
                        return stream.get("url")
                    elif audio_streams:
                        # Find highest bitrate audio stream
                        return audio_streams[0].get("url")
    except Exception as e:
        logger.error(f"Stream Fetch API Error: {e}")
    return None


class TgCall(PyTgCalls):
    def __init__(self):
        self.clients = []
        self.history: dict[int, list[str]] = defaultdict(list)
        self.pending_autoplay: dict[int, Track] = {}
        self.autoplay_prefetching: set[int] = set()
        self.autoplay_failures: dict[int, int] = defaultdict(int)

    async def _prefetch_next(self, chat_id: int) -> None:
        if chat_id in self.autoplay_prefetching:
            return
        self.autoplay_prefetching.add(chat_id)
        try:
            await asyncio.sleep(2) 
            
            # 🚀 MANUAL QUEUE BACKGROUND PREFETCH (USING API)
            try:
                q = queue.get(chat_id)
                if q and isinstance(q, list) and len(q) > 1:
                    next_track = q[1]
                    if not next_track.file_path:
                        try:
                            # Replaced yt.download with API
                            next_track.file_path = await get_stream_via_api(next_track.id, video=next_track.video)
                        except Exception as e:
                            logger.error(f"Prefetch Queue Download Error: {e}")
                    return 
            except Exception:
                pass

            # 🚀 AUTOPLAY BACKGROUND PREFETCH (USING API)
            if await db.get_autoplay(chat_id):
                current = queue.get_current(chat_id)
                if current and isinstance(current, Track):
                    related = await get_related_via_api(current.id, self.history[chat_id])
                    if related:
                        if not related.file_path:
                            try:
                                # Replaced yt.download with API
                                related.file_path = await get_stream_via_api(related.id, video=related.video)
                            except Exception as e:
                                logger.error(f"Prefetch Autoplay Download Error: {e}")
                        self.pending_autoplay[chat_id] = related
        except Exception:
            pass
        finally:
            self.autoplay_prefetching.discard(chat_id)

    async def pause(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        try:
            await db.playing(chat_id, paused=True)
        except:
            pass
        return await client.pause(chat_id)

    async def resume(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        try:
            await db.playing(chat_id, paused=False)
        except:
            pass
        return await client.resume(chat_id)

    async def stop(self, chat_id: int) -> None:
        client = await db.get_assistant(chat_id)
        self.autoplay_failures[chat_id] = 0
        try:
            queue.clear(chat_id)
            await db.remove_call(chat_id)
        except:
            pass
        self.history.pop(chat_id, None)
        self.pending_autoplay.pop(chat_id, None)
        self.autoplay_prefetching.discard(chat_id)
        vclogger.clear_chat(chat_id)
        try:
            await client.leave_call(chat_id, close=False)
        except:
            pass

    async def play_media(self, chat_id: int, message: Message, media: Media | Track, seek_time: int = 0) -> None:
        client = await db.get_assistant(chat_id)
        _lang = await lang.get_lang(chat_id)
        _thumb = await thumb.generate(media) if isinstance(media, Track) else config.DEFAULT_THUMB

        if not media.file_path:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            return await self.play_next(chat_id)

        stream = types.MediaStream(
            media_path=media.file_path,  # This is now a direct HTTP API URL
            audio_parameters=types.AudioQuality.HIGH,
            video_parameters=types.VideoQuality.HD_720p,
            audio_flags=types.MediaStream.Flags.REQUIRED,
            video_flags=(types.MediaStream.Flags.AUTO_DETECT if media.video else types.MediaStream.Flags.IGNORE),
            ffmpeg_parameters=f"-ss {seek_time}" if seek_time > 1 else None,
        )
        try:
            await client.play(chat_id=chat_id, stream=stream, config=types.GroupCallConfig(auto_start=False))
            if not seek_time:
                media.time = 1
                await db.add_call(chat_id)
                play_type = "🎬 Video" if media.video else "🎧 Audio"
                linked_title = f"<a href='{media.url}'>{media.title}</a>"
                text = _lang["play_media"].format(media.url, linked_title, media.duration, media.user, play_type)
                start_timer = f"00:00 {media.duration}"
                keyboard = buttons.controls(chat_id, timer=start_timer)
                
                try:
                    active_msg = await message.edit_media(media=InputMediaPhoto(media=_thumb, caption=text), reply_markup=keyboard)
                except MessageIdInvalid:
                    active_msg = await app.send_photo(chat_id=chat_id, photo=_thumb, caption=text, reply_markup=keyboard)
                media.message_id = active_msg.id
                
                # Start prefetching next track in background via API
                asyncio.create_task(self._prefetch_next(chat_id))

        except Exception:
            await self.play_next(chat_id)

    async def play_next(self, chat_id: int) -> None:
        current = queue.get_current(chat_id)
        if current:
            history = self.history[chat_id]
            history.append(current.id)
            del history[:-20]

        self.autoplay_prefetching.discard(chat_id)
        media = queue.get_next(chat_id)
        
        if not media:
            if current and isinstance(current, Track) and await db.get_autoplay(chat_id):
                related = self.pending_autoplay.pop(chat_id, None)

                if not related:
                    try:
                        related = await get_related_via_api(current.id, self.history[chat_id])
                    except Exception:
                        related = None

                if not related:
                    self.autoplay_failures[chat_id] += 1
                    if self.autoplay_failures[chat_id] >= 4:
                        await app.send_message(chat_id, "⚠️ Autoplay failed 4 times. Stopping stream.")
                        return await self.stop(chat_id)
                else:
                    self.autoplay_failures[chat_id] = 0

                if related:
                    related.user = "Autoplay"
                    queue.add(chat_id, related)
                    media = queue.get_current(chat_id)
                    short_title = media.title[:45] + "..." if len(media.title) > 45 else media.title
                    matched_title = current.title[:45] + "..." if current and current.title else "Unknown Track"
                    
                    _lang = await lang.get_lang(chat_id)
                    
                    autoplay_notice_text = _lang.get(
                        "autoplay_notice", 
                        "<blockquote>▶️ <b>Aᴜᴛᴏᴘʟᴀʏ Nᴇxᴛ :</b>\n🎧 <a href='{url}'><i>{title}</i></a></blockquote>"
                    ).format(url=media.url, title=short_title)
                    
                    notice = await app.send_message(
                        chat_id=chat_id, 
                        text=autoplay_notice_text, 
                        disable_web_page_preview=True
                    )
                    asyncio.create_task(_delete_msg(notice, 6))

                    try:
                        chat_info = await app.get_chat(chat_id)
                        chat_title = chat_info.title
                    except Exception:
                        chat_title = "Unknown Chat"

                    log_text = _lang.get(
                        "autoplay_log",
                        "<blockquote><b>🔁 AUTO-PLAY TRACK STARTED</b>\n\n"
                        "<b>🥀 GROUP :</b> {chat_title} [{chat_id}]\n"
                        "<b>🎵 PLAYING :</b> <a href='{media_url}'>{short_title}</a>\n"
                        "<b>🔗 MATCHED WITH :</b> {matched_title}\n"
                        "<b>⏭ UPCOMING :</b> Autoplay will decide next...</blockquote>"
                    ).format(
                        chat_title=chat_title, 
                        chat_id=chat_id, 
                        media_url=media.url, 
                        short_title=short_title, 
                        matched_title=matched_title
                    )
                    
                    try:
                        if hasattr(config, "LOGGER_ID") and config.LOGGER_ID:
                            await app.send_message(
                                chat_id=config.LOGGER_ID, 
                                text=log_text, 
                                disable_web_page_preview=True
                            )
                    except Exception:
                        pass

            if not media:
                return await self.stop(chat_id)

        _lang = await lang.get_lang(chat_id)
        
        # 🚀 Now using Custom API to fetch stream link instead of yt.download()
        if not media.file_path:
            msg = await app.send_message(chat_id=chat_id, text=_lang["play_next"])
            media.file_path = await get_stream_via_api(media.id, video=media.video)
        else:
            msg = await app.send_message(chat_id=chat_id, text="⚡")

        # Agar stream link null aati hai kisi error ki wajah se
        if not media.file_path:
            await msg.edit_text("⚠️ API Error: Unable to fetch stream URL.")
            return await self.play_next(chat_id)

        media.message_id = msg.id
        await self.play_media(chat_id, msg, media)

    async def ping(self) -> float:
        pings = [client.ping for client in self.clients]
        return round(sum(pings) / len(pings), 2)

    async def decorators(self, client: PyTgCalls) -> None:
        participant_update = getattr(types, "UpdatedGroupCallParticipant", None)

        @client.on_update()
        async def update_handler(_, update: types.Update) -> None:
            if isinstance(update, types.StreamEnded):
                if update.stream_type == types.StreamEnded.Type.AUDIO:
                    await self.play_next(update.chat_id)
            elif isinstance(update, types.ChatUpdate):
                if update.status in [
                    types.ChatUpdate.Status.KICKED,
                    types.ChatUpdate.Status.LEFT_GROUP,
                    types.ChatUpdate.Status.CLOSED_VOICE_CHAT,
                ]:
                    await self.stop(update.chat_id)
            elif participant_update and isinstance(update, participant_update):
                try:
                    if not await db.get_vc_logger(update.chat_id):
                        return
                    action = getattr(update, "action", None)
                    if action is None:
                        action = getattr(update.participant, "action", None)
                    user_id = getattr(update.participant, "user_id", None)
                    if user_id is None:
                        user_id = getattr(update, "user_id", None)
                    if action == types.GroupCallParticipant.Action.JOINED:
                        await vclogger.notify_join(update.chat_id, user_id)
                    elif action == types.GroupCallParticipant.Action.LEFT:
                        await vclogger.notify_leave(update.chat_id, user_id)
                except Exception:
                    pass

    async def boot(self) -> None:
        PyTgCallsSession.notice_displayed = True
        for ub in userbot.clients:
            client = PyTgCalls(ub, cache_duration=100)
            await client.start()
            self.clients.append(client)
            await self.decorators(client)
        logger.info("PyTgCalls client(s) started.")
