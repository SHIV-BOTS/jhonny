# Copyright (c) 2026 THE SHIV
# Licensed under the MIT License.
# This file is part of MahiMusic
# DEVELOPER - THE SHIV

import os
import re
import asyncio
import aiohttp
from py_yt import VideosSearch, Playlist
from AloneX import logger, config
from AloneX.helpers import Track, utils

API_URL = "https://teaminflex.xyz"
DOWNLOAD_DIR = "downloads"

class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )
        self._dl_locks = {}

    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url))

    async def search(self, query: str, m_id: int, video: bool = False) -> Track | None:
        try:
            _search = VideosSearch(query, limit=1)
            results = await _search.next()
            if results and results["result"]:
                data = results["result"][0]
                return Track(
                    id=data.get("id"),
                    channel_name=data.get("channel", {}).get("name"),
                    duration=data.get("duration"),
                    duration_sec=utils.to_seconds(data.get("duration")) if data.get("duration") else 0,
                    message_id=m_id,
                    title=data.get("title")[:25],
                    thumbnail=data.get("thumbnails", [{}])[-1].get("url").split("?")[0],
                    url=data.get("link"),
                    view_count=data.get("viewCount", {}).get("short"),
                    video=video,
                )
        except Exception as e:
            logger.error(f"Search error: {e}")
        return None

    async def playlist(self, limit: int, user: str, url: str, video: bool) -> list[Track]:
        tracks = []
        try:
            plist = await Playlist.get(url)
            for data in plist.get("videos", [])[:limit]:
                track = Track(
                    id=data.get("id"),
                    channel_name=data.get("channel", {}).get("name", ""),
                    duration=data.get("duration"),
                    duration_sec=utils.to_seconds(data.get("duration")) if data.get("duration") else 0,
                    title=data.get("title")[:25],
                    thumbnail=data.get("thumbnails", [{}])[-1].get("url").split("?")[0],
                    url=data.get("link").split("&list=")[0],
                    user=user,
                    view_count="",
                    video=video,
                )
                tracks.append(track)
        except Exception as e:
            logger.error(f"Playlist error: {e}")
        return tracks

    async def download(self, video_id: str, video: bool = False) -> str | None:
        if not video_id or len(video_id) < 3:
            return None

        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        ext = "mkv" if video else "webm"
        file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{ext}")

        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            return file_path

        if video_id in self._dl_locks:
            await self._dl_locks[video_id].wait()
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                return file_path
            return None

        lock_event = asyncio.Event()
        self._dl_locks[video_id] = lock_event

        try:
            max_retries = 3
            retry_delay = 1 
            transient_statuses = {502, 503, 504}

            for attempt in range(1, max_retries + 1):
                try:
                    async with aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as session:
                        payload = {"url": video_id, "type": "video" if video else "audio"}
                        headers = {
                            "Content-Type": "application/json",
                            "X-API-KEY": config.YOUTUBE_API_KEY
                        }

                        async with session.post(f"{API_URL}/download", json=payload, headers=headers) as response:
                            if response.status == 401:
                                logger.error("[API] Invalid API key")
                                return None

                            if response.status in transient_statuses:
                                logger.warning(f"[API] returned {response.status} (attempt {attempt}/{max_retries}) for {video_id}")
                                if attempt < max_retries:
                                    await asyncio.sleep(retry_delay)
                                    continue
                                logger.error(f"[API] gave up after {max_retries} attempts for {video_id}")
                                return None

                            if response.status != 200:
                                logger.error(f"[API] returned {response.status}")
                                return None

                            try:
                                data = await response.json()
                            except Exception as e:
                                logger.warning(f"[API] invalid JSON response (attempt {attempt}/{max_retries}) for {video_id}: {e}")
                                if attempt < max_retries:
                                    await asyncio.sleep(retry_delay)
                                    continue
                                return None

                            if data.get("status") != "success" or not data.get("download_url"):
                                logger.error(f"[API] response error: {data}")
                                if attempt < max_retries:
                                    await asyncio.sleep(retry_delay)
                                    continue
                                return None

                            download_link = f"{API_URL}{data['download_url']}"

                        tmp_path = file_path + ".part"
                        async with session.get(download_link) as file_response:
                            if file_response.status in transient_statuses:
                                logger.warning(f"[API] file download returned {file_response.status} (attempt {attempt}/{max_retries}) for {video_id}")
                                if attempt < max_retries:
                                    await asyncio.sleep(retry_delay)
                                    continue
                                return None

                            if file_response.status != 200:
                                logger.error(f"[API] Download failed ({file_response.status})")
                                if attempt < max_retries:
                                    await asyncio.sleep(retry_delay)
                                    continue
                                return None

                            with open(tmp_path, "wb") as f:
                                async for chunk in file_response.content.iter_chunked(8192):
                                    f.write(chunk)
                                    
                        os.rename(tmp_path, file_path)

                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        return file_path

                    logger.warning(f"[API] downloaded file was empty/missing (attempt {attempt}/{max_retries}) for {video_id}")
                    if os.path.exists(file_path):
                        try: os.remove(file_path)
                        except: pass
                    if attempt < max_retries:
                        await asyncio.sleep(retry_delay)
                        continue
                    return None

                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    logger.warning(f"[API] network error (attempt {attempt}/{max_retries}) for {video_id}: {e}")
                    if os.path.exists(file_path + ".part"):
                        try: os.remove(file_path + ".part")
                        except: pass
                    if attempt < max_retries:
                        await asyncio.sleep(retry_delay)
                        continue
                    return None

                except Exception as e:
                    logger.error(f"Download exception for ID {video_id} (attempt {attempt}/{max_retries}): {e}")
                    if attempt < max_retries:
                        await asyncio.sleep(retry_delay)
                        continue
                    return None

            return None

        finally:
            lock_event.set()
            self._dl_locks.pop(video_id, None)

    def _format_duration(self, seconds: int) -> str:
        seconds = max(int(seconds or 0), 0)
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    def _format_views(self, count) -> str:
        if not count:
            return ""
        count = int(count)
        if count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M views"
        if count >= 1_000:
            return f"{count / 1_000:.1f}K views"
        return f"{count} views"

    # ✅ NEW API-BASED AUTOPLAY FETCH (Replaces yt-dlp & cookies.txt)
    async def _related_from_api(self, video_id: str, played: set[str]) -> Track | None:
        api_key = getattr(config, "YOUTUBE_API_KEY", None)
        if not api_key:
            logger.error("[Autoplay API] YOUTUBE_API_KEY is missing in config!")
            return None
            
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&relatedToVideoId={video_id}&type=video&key={api_key}&maxResults=10"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data.get("items", []):
                            vid = item.get("id", {}).get("videoId")
                            if vid and vid not in played:
                                title = item.get("snippet", {}).get("title", "Unknown Track")
                                channel = item.get("snippet", {}).get("channelTitle", "YouTube")
                                thumbnails = item.get("snippet", {}).get("thumbnails", {})
                                thumb_url = thumbnails.get("high", thumbnails.get("default", {})).get("url")
                                
                                return Track(
                                    id=vid,
                                    channel_name=channel,
                                    duration="00:00",
                                    duration_sec=0,
                                    title=title[:25],
                                    thumbnail=thumb_url,
                                    url=f"https://www.youtube.com/watch?v={vid}",
                                    view_count="",
                                    video=False,
                                )
                    else:
                        logger.error(f"[Autoplay API] Failed to fetch related video. Status: {resp.status}")
        except Exception as e:
            logger.error(f"[Autoplay API] Fetch Error: {e}")
        return None

    async def _related_from_search(
        self, current: Track, played: set[str]
    ) -> Track | None:
        queries = []
        if current.channel_name:
            queries.append(f"{current.channel_name}")
        if current.title:
            queries.append(f"{current.title}")

        for query in queries:
            try:
                _search = VideosSearch(query, limit=8)
                results = await _search.next()
            except Exception as e:
                logger.error(f"[Autoplay] Search fallback failed for {query!r}: {e}")
                continue

            for data in (results or {}).get("result", []):
                eid = data.get("id")
                if not eid or eid in played:
                    continue

                duration_str = data.get("duration")
                duration_sec = utils.to_seconds(duration_str) if duration_str else 0
                if not duration_sec or duration_sec > config.DURATION_LIMIT:
                    continue

                return Track(
                    id=eid,
                    channel_name=data.get("channel", {}).get("name") or "YouTube",
                    duration=duration_str,
                    duration_sec=duration_sec,
                    title=(data.get("title") or "Unknown")[:25],
                    thumbnail=(data.get("thumbnails", [{}])[-1].get("url") or "").split("?")[0] or None,
                    url=data.get("link"),
                    view_count=data.get("viewCount", {}).get("short"),
                    video=False,
                )

        return None

    async def get_related(
        self, current: Track, played: list[str] | None = None
    ) -> Track | None:
        if not current or not current.id:
            return None

        played = set(played or [])
        played.add(current.id)

        # ✅ Call API directly instead of yt-dlp
        related = await self._related_from_api(current.id, played)
        
        if not related:
            logger.info(f"[Autoplay] API returned nothing for {current.id}, trying search fallback.")
            related = await self._related_from_search(current, played)

        if related:
            logger.info(f"[Autoplay] Found next track: {related.title}, pre-download skipped.")
            return related

        logger.warning(f"[Autoplay] No related track found for {current.id}.")
        return None
