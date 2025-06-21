import asyncio
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ChatMembersFilter
from pyrogram.errors import FloodWait, PeerIdInvalid, ChannelInvalid

from TeamXmusic import app, LOGGER
from TeamXmusic.core.mongo import mongodb as db
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

BROADCAST_FLAGS = ["-pin", "-pinloud", "-nobot", "-assistant", "-user"]


def extract_flags_and_content(message_text):
    query = message_text
    active_flags = []
    for flag in BROADCAST_FLAGS:
        if flag in query:
            active_flags.append(flag)
            query = query.replace(flag, "")
    return query.strip(), active_flags


@app.on_message(filters.command("broadcast") & SUDOERS)
@language
async def broadcast_message(client, message: Message, _):
    global IS_BROADCASTING
    if IS_BROADCASTING:
        return await message.reply_text("A broadcast is already running.")

    if message.reply_to_message:
        x = message.reply_to_message.id
        y = message.chat.id
        query, flags = None, []
    else:
        if len(message.command) < 2:
            return await message.reply_text(_["broad_2"])
        raw_text = message.text.split(None, 1)[1]
        query, flags = extract_flags_and_content(raw_text)
        if not query:
            return await message.reply_text(_["broad_8"])

    IS_BROADCASTING = True
    await message.reply_text(_["broad_1"])

    if "-nobot" not in flags:
        await broadcast_to_chats(client, message, query, flags, x if message.reply_to_message else None, y if message.reply_to_message else None, _)

    if "-user" in flags:
        await broadcast_to_users(client, message, query, x, y, _)

    if "-assistant" in flags:
        await broadcast_via_assistants(message, query, x, y, _)

    IS_BROADCASTING = False


async def broadcast_to_chats(client, message, query, flags, reply_msg_id, reply_chat_id, _):
    sent = pin = err = floodWaitError = floodwaitskipped = floodWaitsleep = to = 0
    chats = [int(chat["chat_id"]) for chat in await get_served_chats()]

    for chat_id in chats:
        to += 1
        try:
            chat = await app.get_chat(chat_id)
            if chat.type not in ["supergroup", "group"] or (chat.permissions and not chat.permissions.can_send_messages):
                continue

            m = (
                await app.forward_messages(chat_id, reply_chat_id, reply_msg_id)
                if reply_msg_id else await app.send_message(chat_id, text=query)
            )

            if "-pin" in flags:
                try:
                    await m.pin(disable_notification=True)
                    pin += 1
                except:
                    continue
            elif "-pinloud" in flags:
                try:
                    await m.pin(disable_notification=False)
                    pin += 1
                except:
                    continue

            sent += 1
            await asyncio.sleep(0.2)

        except FloodWait as fw:
            floodWaitError += 1
            if fw.value > 200:
                floodwaitskipped += 1
                continue
            await asyncio.sleep(fw.value)
            floodWaitsleep += 1
        except (PeerIdInvalid, ChannelInvalid) as e:
            LOGGER(__name__).info(f"Invalid chat skipped: {chat_id} - {e}")
            err += 1
            await db.served_chats.delete_one({"chat_id": chat_id})
            continue
        except Exception as e:
            LOGGER(__name__).info(f"Broadcast error in chat {chat_id}: {e}")
            err += 1
            continue

    try:
        await message.reply_text(_["broad_3"].format(sent, pin))
        await app.send_message(
            message.chat.id,
            f">> Broadcasted to {sent} chats.\nTotal: {to}\nFloodwaits: {floodWaitError}\nSkipped: {floodwaitskipped}\nSlept: {floodWaitsleep}\nErrors: {err}"
        )
    except:
        pass


async def broadcast_to_users(client, message, query, reply_msg_id, reply_chat_id, _):
    susr = 0
    served_users = [int(user["user_id"]) for user in await get_served_users()]
    for user_id in served_users:
        try:
            await app.get_chat(user_id)
            m = (
                await app.forward_messages(user_id, reply_chat_id, reply_msg_id)
                if reply_msg_id else await app.send_message(user_id, text=query)
            )
            susr += 1
            await asyncio.sleep(0.2)
        except FloodWait as fw:
            if fw.value > 200:
                continue
            await asyncio.sleep(fw.value)
        except Exception as e:
            LOGGER(__name__).info(f"User broadcast error {user_id}: {e}")
            continue
    try:
        await message.reply_text(_["broad_4"].format(susr))
    except:
        pass


async def broadcast_via_assistants(message, query, reply_msg_id, reply_chat_id, _):
    aw = await message.reply_text(_["broad_5"])
    text = _["broad_6"]
    from TeamXmusic.core.userbot import assistants

    for num in assistants:
        sent = 0
        client = await get_client(num)
        async for dialog in client.get_dialogs():
            try:
                await client.get_chat(dialog.chat.id)
                await client.forward_messages(dialog.chat.id, reply_chat_id, reply_msg_id) if reply_msg_id else await client.send_message(dialog.chat.id, text=query)
                sent += 1
                await asyncio.sleep(3)
            except FloodWait as fw:
                if fw.value > 200:
                    continue
                await asyncio.sleep(fw.value)
            except Exception as e:
                LOGGER(__name__).info(f"Assistant broadcast error: {e}")
                continue
        text += _["broad_7"].format(num, sent)
    try:
        await aw.edit_text(text)
    except:
        pass


async def startup_clean():
    try:
        served_chats = await get_active_chats()
        for gid in served_chats:
            try:
                await app.get_chat(gid)
            except Exception as e:
                LOGGER(__name__).info(f"Startup auto-clean [GROUP]: {gid} - {e}")
                await db.served_chats.delete_one({"chat_id": gid})
    except Exception as e:
        LOGGER(__name__).error(f"Startup cleaner failed: {e}")


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
asyncio.create_task(startup_clean())
