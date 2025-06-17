import asyncio
import random
import logging
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid, ChatWriteForbidden, ChatAdminRequired

from TeamXmusic import app
from TeamXmusic.utils.database import get_served_chats, get_served_users

AUTHORIZED_IDS = set()
try:
    from config import OWNER_ID
    AUTHORIZED_IDS.add(int(OWNER_ID))
except Exception:
    pass
try:
    from config import SUDO_USERS
    if isinstance(SUDO_USERS, (list, tuple, set)):
        for uid in SUDO_USERS:
            AUTHORIZED_IDS.add(int(uid))
    else:
        for uid in str(SUDO_USERS).replace(",", " ").split():
            AUTHORIZED_IDS.add(int(uid))
except Exception:
    pass

if not AUTHORIZED_IDS:
    logging.warning("No authorized user IDs specified for broadcasts.")

@app.on_message(filters.command("broadcast") & filters.user(list(AUTHORIZED_IDS)))
async def broadcast_message(client: Client, message):
    if not message.reply_to_message and len(message.text.split()) < 2:
        return await message.reply_text("Reply to a message or provide text/media to broadcast.")

    target_message = None
    caption_override = None
    broadcast_text = None

    if message.reply_to_message:
        target_message = message.reply_to_message
        if message.text and ' ' in message.text:
            caption_override = message.text.split(' ', 1)[1]
    elif message.media:
        target_message = message
        if message.caption:
            caption_override = message.caption.split(' ', 1)[1] if ' ' in message.caption else ""
    else:
        broadcast_text = message.text.split(' ', 1)[1]

    all_chats = await get_served_chats()
    all_users = await get_served_users()
    broadcast_ids = []

    for chat in all_chats or []:
        try:
            cid = int(chat["chat_id"]) if isinstance(chat, dict) else int(chat)
            broadcast_ids.append(cid)
        except Exception:
            continue
    for user in all_users or []:
        try:
            uid = int(user["user_id"]) if isinstance(user, dict) else int(user)
            broadcast_ids.append(uid)
        except Exception:
            continue

    broadcast_ids = list({x for x in broadcast_ids if isinstance(x, int)})
    success_count = 0
    fail_count = 0

    for chat_id in broadcast_ids:
        try:
            if target_message:
                await target_message.copy(chat_id, caption=caption_override if caption_override is not None else None)
            else:
                await client.send_message(chat_id, broadcast_text)
            success_count += 1
            await asyncio.sleep(random.uniform(0.2, 0.6))
        except FloodWait as e:
            wait_time = int(getattr(e, "value", getattr(e, "x", 0)) or 5)
            await asyncio.sleep(wait_time + random.randint(2, 5))
            try:
                if target_message:
                    await target_message.copy(chat_id, caption=caption_override if caption_override is not None else None)
                else:
                    await client.send_message(chat_id, broadcast_text)
                success_count += 1
            except Exception:
                fail_count += 1
        except (InputUserDeactivated, UserIsBlocked, PeerIdInvalid, ChatWriteForbidden, ChatAdminRequired):
            fail_count += 1
            continue
        except Exception as err:
            logging.error(f"Failed to broadcast to {chat_id}: {err}")
            fail_count += 1
            continue

    summary_text = f"**Broadcast Completed!**\n✅ Sent: `{success_count}`\n❌ Failed: `{fail_count}`"
    try:
        await message.reply_text(summary_text)
    except:
        pass
