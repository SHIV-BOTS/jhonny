# Copyright (c) 2026 THE SHIV
# Licensed under the MIT License.
# This file is part of MahiMusic
# DEVELOPER - THE SHIV

from pyrogram import Client
from pyrogram.errors import RPCError

from AloneX import config, logger


class Userbot(Client):
    def __init__(self):
        """
        Initializes the userbot with multiple clients.
        This method sets up clients for the userbot using predefined session strings.
        """
        self.clients = []
        self.one = None
        self.two = None
        self.three = None

        if config.SESSION1:
            self.one = Client(
                name="MahiMusicUB1",
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                session_string=config.SESSION1,
            )
        if config.SESSION2:
            self.two = Client(
                name="MahiMusicUB2",
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                session_string=config.SESSION2,
            )
        if config.SESSION3:
            self.three = Client(
                name="MahiMusicUB3",
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                session_string=config.SESSION3,
            )

    async def boot_client(self, num: int, client: Client):
        """
        Boot a client and perform initial setup.
        Args:
            num (int): The client number to boot (1, 2, or 3).
            client (Client): The userbot client instance.
        """
        try:
            await client.start()
        except Exception as e:
            logger.error(f"Assistant {num} failed to start. Your SESSION string has likely expired or is invalid. Error: {e}")
            raise SystemExit(f"Assistant {num} session is dead. Generate a new Pyrogram v2 string!")

        try:
            await client.send_message(config.LOGGER_ID, f"✅ Assistant {num} Started Successfully!")
        except Exception as e:
            logger.error(f"Assistant {num} failed to send message to Log Group. Did you add the assistant to your Logger Group?")
            raise SystemExit(f"Assistant {num} log message failed: {e}")

        client.id = client.me.id
        client.name = client.me.first_name
        client.username = client.me.username
        client.mention = client.me.mention
        self.clients.append(client)

        # Assistant automatically joining support channel
        try:
            if config.SUPPORT_CHANNEL and "t.me/" in config.SUPPORT_CHANNEL:
                chat_link = config.SUPPORT_CHANNEL.split("t.me/")[1]
                await client.join_chat(chat_link)
        except RPCError:
            pass
        except Exception:
            pass

        logger.info(f"Assistant {num} started as {client.name} (@{client.username})")

    async def boot(self):
        """
        Asynchronously starts the assistants.
        """
        if self.one:
            await self.boot_client(1, self.one)
        if self.two:
            await self.boot_client(2, self.two)
        if self.three:
            await self.boot_client(3, self.three)

    async def exit(self):
        """
        Asynchronously stops the assistants.
        """
        if self.one:
            try:
                await self.one.stop()
            except: pass
        if self.two:
            try:
                await self.two.stop()
            except: pass
        if self.three:
            try:
                await self.three.stop()
            except: pass
        logger.info("Assistants stopped.")
