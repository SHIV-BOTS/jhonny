import random
import re
from pyrogram import enums, types
from pyrogram.enums import ButtonStyle

from AloneX import app, config, lang
from AloneX.core.lang import lang_codes

# Safe fallback if PREMIUM_EMOJIS is not defined in config
PREMIUM_EMOJIS = getattr(config, "PREMIUM_EMOJIS", None)

def time_to_seconds(time_str: str) -> int:
    """Helper function to convert time string to seconds"""
    try:
        parts = time_str.split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 1:
            return int(parts[0])
    except:
        return 0
    return 0


class Inline:
    def __init__(self):
        self.ikm = types.InlineKeyboardMarkup
        self.ikb = types.InlineKeyboardButton

    # 🎨 Dynamic Row-Wise Color Generator
    def get_row_styles(self):
        styles = [ButtonStyle.PRIMARY, ButtonStyle.SUCCESS, ButtonStyle.DANGER]
        random.shuffle(styles)
        return styles

    # 🎵 Custom Progress Bar Generator 
    def get_progress_bar(self, played_str: str, dur_str: str) -> str:
        played_sec = time_to_seconds(str(played_str))
        if str(dur_str).lower() in ["live", "unknown", "0", "00:00"]:
            duration_sec = 0
        else:
            duration_sec = time_to_seconds(str(dur_str))
        
        total_blocks = 10
        if duration_sec > 0:
            filled_blocks = int((played_sec / duration_sec) * total_blocks)
        else:
            filled_blocks = 0
            
        filled_blocks = min(max(filled_blocks, 0), total_blocks)
        
        # Smooth progress bar with music note 🎵 leading the way
        if filled_blocks == 0:
            bar = "🎵" + "▱" * (total_blocks - 1)
        elif filled_blocks == total_blocks:
            bar = "▰" * (total_blocks - 1) + "🎵"
        else:
            bar = "▰" * filled_blocks + "🎵" + "▱" * (total_blocks - filled_blocks - 1)
            
        return bar

    def cancel_dl(self, text) -> types.InlineKeyboardMarkup:
        return self.ikm([[self.ikb(text=text, callback_data=f"cancel_dl")]])

    # 🆕 Naya Autoplay Panel System (Purana Hata Diya Gaya Hai)
    def autoplay_panel_markup(self, chat_id: int, enabled: bool) -> types.InlineKeyboardMarkup:
        status = "🟢 𝐄ɴᴀʙʟᴇᴅ" if enabled else "🔴 𝐃ɪsᴀʙʟᴇᴅ"
        
        return self.ikm(
            [
                [
                    self.ikb(
                        text="𝐀ᴜᴛᴏ 𝐏ʟᴀʏ 𝐄ɴᴀʙʟᴇ",
                        callback_data=f"AUTOPLAY_ENABLE|{chat_id}",
                        style=ButtonStyle.SUCCESS,
                        icon_custom_emoji_id=random.choice(PREMIUM_EMOJIS) if PREMIUM_EMOJIS else None
                    ),
                    self.ikb(
                        text="𝐀ᴜᴛᴏ 𝐏ʟᴀʏ 𝐃ɪsᴀʙʟᴇ",
                        callback_data=f"AUTOPLAY_DISABLE|{chat_id}",
                        style=ButtonStyle.DANGER,
                        icon_custom_emoji_id=random.choice(PREMIUM_EMOJIS) if PREMIUM_EMOJIS else None
                    ),
                ],
                [
                    self.ikb(
                        text=f"𝐀ᴜᴛᴏ 𝐏ʟᴀʏ : {status}",
                        callback_data="AUTOPLAY_STATUS",
                        style=ButtonStyle.PRIMARY,
                        icon_custom_emoji_id=random.choice(PREMIUM_EMOJIS) if PREMIUM_EMOJIS else None
                    )
                ],
                [
                    self.ikb(
                        text="⌯ 𝐂ʟσsє ⌯",
                        callback_data="autoplay_panel close",
                        style=ButtonStyle.SECONDARY
                    )
                ]
            ]
        )

    def controls(
        self,
        chat_id: int,
        status: str = None,
        timer: str = None,
        remove: bool = False,
        _lang: dict = None,
    ) -> types.InlineKeyboardMarkup:
        keyboard = []
        style = self.get_row_styles()

        if status:
            keyboard.append(
                [self.ikb(text=status, callback_data=f"controls status {chat_id}", style=style[0])]
            )
        elif timer:
            # 🎵 Forcefully inject the new progress bar using Regex
            try:
                times = re.findall(r'\d+:\d+(?::\d+)?', timer)
                if len(times) == 2:
                    played_str = times[0]
                    dur_str = times[1]
                    new_bar = self.get_progress_bar(played_str, dur_str)
                    timer = f"{played_str} {new_bar} {dur_str}"
                elif len(times) == 1 and "live" in timer.lower():
                    played_str = times[0]
                    new_bar = self.get_progress_bar(played_str, "0")
                    timer = f"{played_str} {new_bar} Live"
            except Exception:
                pass

            keyboard.append(
                [self.ikb(text=timer, callback_data=f"controls status {chat_id}", style=style[0])]
            )

        if not remove:
            # Step 2: Controls row
            keyboard.append(
                [
                    self.ikb(text="▷", callback_data=f"controls resume {chat_id}", style=style[1]),
                    self.ikb(text="II", callback_data=f"controls pause {chat_id}", style=style[1]),
                    self.ikb(text="⥁", callback_data=f"controls replay {chat_id}", style=style[1]),
                    self.ikb(text="‣‣I", callback_data=f"controls skip {chat_id}", style=style[1]),
                    self.ikb(text="▢", callback_data=f"controls stop {chat_id}", style=style[1]),
                ]
            )
            
            # Step 3: Autoplay & Clone row
            keyboard.append(
                [
                    self.ikb(text="ᴀᴜᴛᴏ-ᴘʟᴀʏ", callback_data="help autoplay", style=style[2]),
                    self.ikb(text="ᴄʟᴏɴᴇ-ᴍᴇ", url="https://t.me/clone_MUSICrobot", style=style[2]),
                ]
            )
            
            if not _lang:
                _lang = lang.languages["en"]
                
            # Step 4: Add Me & Close row
            keyboard.append(
                [
                    self.ikb(
                        text="➕ Add Me",
                        url=f"https://t.me/{app.username}?startgroup=true",
                        style=style[0],
                    ),
                    self.ikb(
                        text=_lang.get("close", "⌯ 𝐂ʟσsє ⌯"),
                        callback_data="help close",
                        style=style[0],
                    ),
                ]
            )
        return self.ikm(keyboard)

    def help_markup(
        self, _lang: dict, back: bool = False
    ) -> types.InlineKeyboardMarkup:
        style = self.get_row_styles()
        
        if back:
            rows = [
                [
                    self.ikb(text=_lang["back"], callback_data="help back", style=style[0]),
                    self.ikb(text=_lang.get("home_btn", "🏠 Home"), callback_data="help home", style=style[0]),
                    self.ikb(text=_lang["close"], callback_data="help close", style=style[0]),
                ]
            ]
        else:
            cbs = ["admins", "auth", "blist", "lang", "ping", "play", "queue", "stats", "sudo", "autoplay", "vclogger"]
            rows = []
            
            for i in range(0, len(cbs), 3):
                row_cbs = cbs[i : i + 3]
                row_style = style[(i // 3) % 3]
                rows.append([
                    self.ikb(text=_lang[f"help_{cb}"], callback_data=f"help {cb}", style=row_style)
                    for cb in row_cbs
                ])
                
            last_style = style[len(rows) % 3]
            rows.append(
                [
                    self.ikb(text=_lang.get("home_btn", "🏠 Home"), callback_data="help home", style=last_style),
                    self.ikb(text=_lang["close"], callback_data="help close", style=last_style),
                ]
            )

        return self.ikm(rows)

    def lang_markup(self, _lang: str) -> types.InlineKeyboardMarkup:
        style = self.get_row_styles()
        langs = list(lang.get_languages().items())

        rows = []
        for i in range(0, len(langs), 2):
            row_langs = langs[i : i + 2]
            row_style = style[(i // 2) % 3]
            rows.append([
                self.ikb(
                    text=f"{name} ({code}) {'✔️' if code == _lang else ''}",
                    callback_data=f"lang_change {code}",
                    style=row_style
                )
                for code, name in row_langs
            ])
            
        return self.ikm(rows)

    def ping_markup(self, text: str) -> types.InlineKeyboardMarkup:
        return self.ikm([[self.ikb(text=text, url=config.SUPPORT_CHAT)]])

    def play_queued(
        self, chat_id: int, item_id: str, _text: str
    ) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(
                        text=_text,
                        callback_data=f"controls force {chat_id} {item_id}",
                        style=ButtonStyle.SUCCESS,
                    )
                ]
            ]
        )

    def queue_markup(
        self, chat_id: int, _text: str, playing: bool
    ) -> types.InlineKeyboardMarkup:
        _action = "pause" if playing else "resume"
        return self.ikm(
            [
                [
                    self.ikb(
                        text=_text,
                        callback_data=f"controls {_action} {chat_id} q",
                        style=ButtonStyle.SUCCESS,
                    )
                ]
            ]
        )

    def settings_markup(
        self, lang: dict, admin_only: bool, cmd_delete: bool, language: str, chat_id: int
    ) -> types.InlineKeyboardMarkup:
        style = self.get_row_styles()
        return self.ikm(
            [
                [
                    self.ikb(text=lang["play_mode"] + " ➜", callback_data="settings", style=style[0]),
                    self.ikb(text=admin_only, callback_data="settings play", style=style[0]),
                ],
                [
                    self.ikb(text=lang["cmd_delete"] + " ➜", callback_data="settings", style=style[1]),
                    self.ikb(text=cmd_delete, callback_data="settings delete", style=style[1]),
                ],
                [
                    self.ikb(text=lang["language"] + " ➜", callback_data="settings", style=style[2]),
                    self.ikb(text=lang_codes[language], callback_data="language", style=style[2]),
                ],
            ]
        )

    def start_key(
        self, lang: dict, private: bool = False
    ) -> types.InlineKeyboardMarkup:
        style = self.get_row_styles()
        rows = [
            [
                self.ikb(
                    text=lang["add_me"],
                    url=f"https://t.me/{app.username}?startgroup=true", 
                    style=style[0]
                )
            ],
            [self.ikb(text=lang["help"], callback_data="help", style=style[1])],
        ]
        
        if private:
            rows += [
                [
                    self.ikb(text=lang["support"], url=config.SUPPORT_CHAT, style=style[2]),
                    self.ikb(text=lang["channel"], url=config.SUPPORT_CHANNEL, style=style[2]),
                ],
                [
                    self.ikb(text="THE SHIV", url=config.OWNER_USERNAME, style=style[0]),
                ]
            ]
        else:
            rows += [
                [
                    self.ikb(text=lang["support"], url=config.SUPPORT_CHAT, style=style[2]),
                    self.ikb(text=lang["channel"], url=config.SUPPORT_CHANNEL, style=style[2]),
                ],
                [self.ikb(text=lang["language"], callback_data="language", style=style[0])],
            ]
            
        return self.ikm(rows)

    def yt_key(self, link: str) -> types.InlineKeyboardMarkup:
        style = self.get_row_styles()
        return self.ikm(
            [
                [
                    self.ikb(text="❐", copy_text=link, style=style[0]),
                    self.ikb(text="Youtube", url=link, style=style[0]),
                ],
            ]
        )
