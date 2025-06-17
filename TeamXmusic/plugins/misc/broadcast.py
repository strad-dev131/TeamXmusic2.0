import asyncio
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ChatMembersFilter
from pyrogram.errors import FloodWait, PeerIdInvalid, ChannelInvalid

from TeamXmusic import app, LOGGER
from TeamXmusic.misc import dbb as db  # ✅ Fix here

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
    if message.reply_to_message:
        x = message.reply_to_message.id
        y = message.chat.id
    else:
        if len(message.command) < 2:
            return await message.reply_text(_["broad_2"])
        query = message.text.split(None, 1)[1]
        for flag in ["-pin", "-nobot", "-pinloud", "-assistant", "-user"]:
            query = query.replace(flag, "")
        if query.strip() == "":
            return await message.reply_text(_["broad_8"])

    IS_BROADCASTING = True
    await message.reply_text(_["broad_1"])

    if "-nobot" not in message.text:
        sent = 0
        pin = 0
        err = 0
        floodWaitError = 0
        floodwaitskipped = 0
        floodWaitsleep = 0
        to = 0

        chats = [int(chat["chat_id"]) for chat in await get_served_chats()]
        for i in chats:
            to += 1
            try:
                chat = await app.get_chat(i)

                # Skip non-group chats or where bot can't send messages
                if chat.type not in ["supergroup", "group"]:
                    continue
                if hasattr(chat, 'permissions') and chat.permissions and not chat.permissions.can_send_messages:
                    continue

                m = (
                    await app.forward_messages(i, y, x)
                    if message.reply_to_message
                    else await app.send_message(i, text=query)
                )

                if "-pin" in message.text:
                    try:
                        await m.pin(disable_notification=True)
                        pin += 1
                    except Exception:
                        continue
                elif "-pinloud" in message.text:
                    try:
                        await m.pin(disable_notification=False)
                        pin += 1
                    except Exception:
                        continue

                sent += 1
                await asyncio.sleep(0.2)

            except FloodWait as fw:
                floodWaitError += 1
                flood_time = int(fw.value)
                if flood_time > 200:
                    floodwaitskipped += 1
                    continue
                await asyncio.sleep(flood_time)
                floodWaitsleep += 1
            except (PeerIdInvalid, ChannelInvalid) as e:
                LOGGER(__name__).info(f"Invalid chat skipped: {i} - {e}")
                err += 1
                # Auto-remove from MongoDB
                await db.served_chats.delete_one({"chat_id": i})
                continue
            except Exception as e:
                LOGGER(__name__).info(f"Broadcast error in chat {i}: {e}")
                err += 1
                continue

        try:
            await message.reply_text(_["broad_3"].format(sent, pin))
            await app.send_message(
                message.chat.id,
                f">> Broadcasted message to {sent}. \n Total chats: {to} \n Floodwait: {floodWaitError} \n FloodwaitSkipped: {floodwaitskipped} \n Floodwaitsleep: {floodWaitsleep} \n Other Errors: {err}"
            )
        except:
            pass

    if "-user" in message.text:
        susr = 0
        served_users = [int(user["user_id"]) for user in await get_served_users()]
        for i in served_users:
            try:
                await app.get_chat(i)
                m = (
                    await app.forward_messages(i, y, x)
                    if message.reply_to_message
                    else await app.send_message(i, text=query)
                )
                susr += 1
                await asyncio.sleep(0.2)
            except FloodWait as fw:
                if fw.value > 200:
                    continue
                await asyncio.sleep(int(fw.value))
            except Exception as e:
                LOGGER(__name__).info(f"User broadcast error {i}: {e}")
                continue
        try:
            await message.reply_text(_["broad_4"].format(susr))
        except:
            pass

    if "-assistant" in message.text:
        aw = await message.reply_text(_["broad_5"])
        text = _["broad_6"]
        from TeamXmusic.core.userbot import assistants
        for num in assistants:
            sent = 0
            client = await get_client(num)
            async for dialog in client.get_dialogs():
                try:
                    await client.get_chat(dialog.chat.id)
                    await client.forward_messages(dialog.chat.id, y, x) if message.reply_to_message else await client.send_message(dialog.chat.id, text=query)
                    sent += 1
                    await asyncio.sleep(3)
                except FloodWait as fw:
                    if fw.value > 200:
                        continue
                    await asyncio.sleep(int(fw.value))
                except Exception as e:
                    LOGGER(__name__).info(f"Assistant broadcast error: {e}")
                    continue
            text += _["broad_7"].format(num, sent)
        try:
            await aw.edit_text(text)
        except:
            pass

    IS_BROADCASTING = False


async def auto_clean():
    while not await asyncio.sleep(10):
        try:
            served_chats = await get_active_chats()
            for chat_id in served_chats:
                if chat_id not in adminlist:
                    adminlist[chat_id] = []
                    async for user in app.get_chat_members(chat_id, filter=ChatMembersFilter.ADMINISTRATORS):
                        if user.privileges.can_manage_video_chats:
                            adminlist[chat_id].append(user.user.id)
                    authusers = await get_authuser_names(chat_id)
                    for user in authusers:
                        user_id = await alpha_to_int(user)
                        adminlist[chat_id].append(user_id)
        except:
            continue

asyncio.create_task(auto_clean())
