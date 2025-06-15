import asyncio
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

    # Parse message
    if message.reply_to_message:
        x = message.reply_to_message.id
        y = message.chat.id
        query = None
    else:
        if len(message.command) < 2:
            return await message.reply_text(_["broad_2"])
        query = message.text.split(None, 1)[1]
        for flag in ["-pin", "-nobot", "-pinloud", "-assistant", "-user"]:
            query = query.replace(flag, "")
        query = query.strip()
        if not query:
            return await message.reply_text(_["broad_8"])
        x = y = None

    IS_BROADCASTING = True
    await message.reply_text(_["broad_1"])

    # Broadcast to chats
    if "-nobot" not in message.text:
        stats = {"sent": 0, "pin": 0, "flood_wait": 0, "skipped": 0, "sleeps": 0, "errors": 0, "total": 0}
        chats = [int(c["chat_id"]) for c in await get_served_chats()]
        for i in chats:
            stats["total"] += 1
            try:
                if message.reply_to_message:
                    m = await app.forward_messages(i, y, x)
                else:
                    m = await app.send_message(i, text=query)

                if "-pin" in message.text:
                    try:
                        await m.pin(disable_notification=True)
                        stats["pin"] += 1
                    except:
                        pass
                elif "-pinloud" in message.text:
                    try:
                        await m.pin(disable_notification=False)
                        stats["pin"] += 1
                    except:
                        pass

                stats["sent"] += 1
                await asyncio.sleep(0.2)

            except FloodWait as fw:
                stats["flood_wait"] += 1
                sleep_time = fw.value
                if sleep_time > 200:
                    stats["skipped"] += 1
                    continue
                await asyncio.sleep(sleep_time)
                stats["sleeps"] += 1

            except (ChannelInvalid, PeerIdInvalid):
                LOGGER(__name__).warning(f"Invalid chat ID skipped: {i}")
                stats["errors"] += 1
                continue

            except Exception as e:
                LOGGER(__name__).error(f"Error in chat {i}: {e}")
                stats["errors"] += 1
                continue

        try:
            await message.reply_text(_["broad_3"].format(stats["sent"], stats["pin"]))
            await app.send_message(
                message.chat.id,
                (
                    f"📣 **Broadcast Report**\n"
                    f"✅ Sent: {stats['sent']}\n📌 Pinned: {stats['pin']}\n"
                    f"📊 Total: {stats['total']}\n⏳ FloodWaits: {stats['flood_wait']}\n"
                    f"⏭️ Skipped: {stats['skipped']}\n💤 Waited: {stats['sleeps']}\n❌ Errors: {stats['errors']}"
                ),
            )
        except:
            pass

    # Broadcast to users
    if "-user" in message.text:
        count = 0
        users = [int(u["user_id"]) for u in await get_served_users()]
        for i in users:
            try:
                if message.reply_to_message:
                    await app.forward_messages(i, y, x)
                else:
                    await app.send_message(i, text=query)
                count += 1
                await asyncio.sleep(0.2)
            except FloodWait as fw:
                if fw.value <= 200:
                    await asyncio.sleep(fw.value)
            except:
                continue
        try:
            await message.reply_text(_["broad_4"].format(count))
        except:
            pass

    # Broadcast via assistant userbots
    if "-assistant" in message.text:
        ack = await message.reply_text(_["broad_5"])
        response_text = _["broad_6"]
        from TeamXmusic.core.userbot import assistants

        for num in assistants:
            count = 0
            client = await get_client(num)
            async for dialog in client.get_dialogs():
                try:
                    if message.reply_to_message:
                        await client.forward_messages(dialog.chat.id, y, x)
                    else:
                        await client.send_message(dialog.chat.id, text=query)
                    count += 1
                    await asyncio.sleep(3)
                except FloodWait as fw:
                    if fw.value <= 200:
                        await asyncio.sleep(fw.value)
                except:
                    continue
            response_text += _["broad_7"].format(num, count)
        try:
            await ack.edit_text(response_text)
        except:
            pass

    IS_BROADCASTING = False


# Auto adminlist cleaner
async def auto_clean():
    while not await asyncio.sleep(10):
        try:
            for chat_id in await get_active_chats():
                if chat_id not in adminlist:
                    adminlist[chat_id] = []
                    async for user in app.get_chat_members(chat_id, filter=ChatMembersFilter.ADMINISTRATORS):
                        if user.privileges.can_manage_video_chats:
                            adminlist[chat_id].append(user.user.id)
                    for user in await get_authuser_names(chat_id):
                        user_id = await alpha_to_int(user)
                        adminlist[chat_id].append(user_id)
        except:
            continue

asyncio.create_task(auto_clean())
