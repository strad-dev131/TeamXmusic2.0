import asyncio
import logging
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ChatMembersFilter
from pyrogram.errors import FloodWait, ChannelInvalid, PeerIdInvalid

from TeamXmusic import app, LOGGER
from TeamXmusic.misc import SUDOERS
from TeamXmusic.utils.database import (
    get_active_chats,
    get_authuser_names,
    get_client,
    get_served_chats,
    get_served_users,
)
from TeamXmusic.utils.decorators.language import language
from TeamXmusic.utils.formatters import alpha_to_int
from config import adminlist


IS_BROADCASTING = False


@app.on_message(filters.command("broadcast") & SUDOERS)
@language
async def broadcast_message(client, message: Message, _):
    global IS_BROADCASTING

    # Determine content to broadcast
    if message.reply_to_message:
        x = message.reply_to_message.id
        y = message.chat.id
        query = None
    else:
        if len(message.command) < 2:
            return await message.reply_text(_["broad_2"])
        query = message.text.split(None, 1)[1]
        for flag in ["-pin", "-nobot", "-pinloud", "-assistant", "-user"]:
            query = query.replace(flag, "").strip()
        if not query:
            return await message.reply_text(_["broad_8"])
        x = y = None  # fallback when sending custom message

    IS_BROADCASTING = True
    await message.reply_text(_["broad_1"])

    # Broadcast to group chats
    if "-nobot" not in message.text:
        sent, pin, flood_waits, flood_skips, flood_sleeps, err, total = 0, 0, 0, 0, 0, 0, 0
        chats = [int(chat["chat_id"]) for chat in await get_served_chats()]

        for chat_id in chats:
            total += 1
            try:
                if message.reply_to_message:
                    m = await app.forward_messages(chat_id, y, x)
                else:
                    m = await app.send_message(chat_id, text=query)

                # Handle pinning
                if "-pin" in message.text:
                    try:
                        await m.pin(disable_notification=True)
                        pin += 1
                    except Exception:
                        pass
                elif "-pinloud" in message.text:
                    try:
                        await m.pin(disable_notification=False)
                        pin += 1
                    except Exception:
                        pass

                sent += 1
                await asyncio.sleep(0.2)

            except FloodWait as fw:
                flood_time = int(fw.value)
                flood_waits += 1
                if flood_time > 200:
                    flood_skips += 1
                    continue
                await asyncio.sleep(flood_time)
                flood_sleeps += 1

            except (ChannelInvalid, PeerIdInvalid):
                LOGGER(__name__).warning(f"Invalid chat skipped: {chat_id}")
                err += 1
                continue

            except Exception as e:
                LOGGER(__name__).error(f"Unhandled error in broadcast to {chat_id}: {e}")
                err += 1
                continue

        try:
            await message.reply_text(_["broad_3"].format(sent, pin))
            await app.send_message(
                message.chat.id,
                (
                    f">> Broadcast Summary:\n"
                    f"✅ Sent: {sent}\n📌 Pinned: {pin}\n📊 Total Chats: {total}\n"
                    f"⏳ FloodWaits: {flood_waits}\n⏭️ Skipped: {flood_skips}\n"
                    f"💤 Delayed Sends: {flood_sleeps}\n❌ Errors: {err}"
                ),
            )
        except Exception:
            pass

    # Broadcast to served users
    if "-user" in message.text:
        success = 0
        users = [int(user["user_id"]) for user in await get_served_users()]
        for user_id in users:
            try:
                if message.reply_to_message:
                    await app.forward_messages(user_id, y, x)
                else:
                    await app.send_message(user_id, text=query)
                success += 1
                await asyncio.sleep(0.2)
            except FloodWait as fw:
                if int(fw.value) <= 200:
                    await asyncio.sleep(fw.value)
            except Exception:
                continue
        try:
            await message.reply_text(_["broad_4"].format(success))
        except Exception:
            pass

    # Broadcast via assistant accounts
    if "-assistant" in message.text:
        response = await message.reply_text(_["broad_5"])
        result_text = _["broad_6"]
        from TeamXmusic.core.userbot import assistants

        for num in assistants:
            sent = 0
            client = await get_client(num)
            async for dialog in client.get_dialogs():
                try:
                    if message.reply_to_message:
                        await client.forward_messages(dialog.chat.id, y, x)
                    else:
                        await client.send_message(dialog.chat.id, text=query)
                    sent += 1
                    await asyncio.sleep(3)
                except FloodWait as fw:
                    if int(fw.value) <= 200:
                        await asyncio.sleep(fw.value)
                except Exception:
                    continue
            result_text += _["broad_7"].format(num, sent)
        try:
            await response.edit_text(result_text)
        except Exception:
            pass

    IS_BROADCASTING = False


# Auto-clean task to maintain adminlist
async def auto_clean():
    while not await asyncio.sleep(10):
        try:
            active_chats = await get_active_chats()
            for chat_id in active_chats:
                if chat_id not in adminlist:
                    adminlist[chat_id] = []
                    async for user in app.get_chat_members(
                        chat_id, filter=ChatMembersFilter.ADMINISTRATORS
                    ):
                        if user.privileges.can_manage_video_chats:
                            adminlist[chat_id].append(user.user.id)
                    for user in await get_authuser_names(chat_id):
                        user_id = await alpha_to_int(user)
                        adminlist[chat_id].append(user_id)
        except Exception:
            continue


asyncio.create_task(auto_clean())
