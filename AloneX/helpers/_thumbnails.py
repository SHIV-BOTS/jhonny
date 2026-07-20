# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic

from AloneX.helpers import Track

class Thumbnail:
    async def generate(self, song: Track) -> str:
        # Har song ke liye directly aapki static image return karega
        return "https://h.uguu.se/KUEpvTNX.jpg"
