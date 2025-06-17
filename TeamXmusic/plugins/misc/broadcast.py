import asyncio
import random
import logging
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid, ChatWriteForbidden, ChatAdminRequired

from TeamXmusic import app
try:
    from TeamXmusic import userbot  # Assistant userbot client (if available)
except ImportError:
    userbot = None

from TeamXmusic.utils.database import get_served_chats, get_served_users, remove_served_chat, remove_served_user

# Load authorized broadcast sender IDs (owner/sudo) from config or environment
AUTHORIZED_IDS = set()
try:
    from config import OWNER_ID
    AUTHORIZED_IDS.add(int(OWNER_ID))
except Exception:
    pass
try:
    from config import SUDO_USERS
    # SUDO_USERS can be a list/tuple of IDs or a string of IDs separated by space/comma
    if isinstance(SUDO_USERS, (list, tuple, set)):
        for uid in SUDO_USERS:
            AUTHORIZED_IDS.add(int(uid))
    else:
        for uid in str(SUDO_USERS).replace(",", " ").split():
            AUTHORIZED_IDS.add(int(uid))
except Exception:
    pass

# If no specific authorized IDs are found, default to allowing only the bot owner (the one who deployed the bot)
if not AUTHORIZED_IDS:
    logging.warning("No authorized user IDs specified for broadcasts. Defaulting to OWNER_ID only.")
    # Optionally, you could allow broadcast for all admins or a certain role by modifying this logic.

@app.on_message(filters.command("broadcast") & filters.user(list(AUTHORIZED_IDS)))
async def broadcast_message(client: Client, message):
    """Broadcast command to send a message or media to all served chats and users."""
    # Ensure there's content to broadcast (either via reply or text/media in the command message)
    if not message.reply_to_message and not message.media and len(message.text.split()) < 2:
        return await message.reply_text("**Usage:** Reply to a message or provide text/media to broadcast.", quote=True)
    
    # Determine the content to broadcast
    target_message = None   # The Message object to copy (if broadcasting media or replied content)
    caption_override = None # New caption text if we need to override media caption
    broadcast_text = None   # Text to send if broadcasting a plain text message
    
    if message.reply_to_message:
        # If command is in reply to another message, use that message as the content
        target_message = message.reply_to_message
        # If the broadcast command message has additional text, treat it as a caption override
        if message.text and ' ' in message.text:
            caption_override = message.text.split(' ', 1)[1]
    elif message.media:
        # If the command message itself contains media (photo, video, etc.), use it as content
        target_message = message  # We'll copy this message to targets
        if message.caption is not None:
            # Use anything after the command in the caption as the new caption (or empty if none)
            if ' ' in message.caption:
                caption_override = message.caption.split(' ', 1)[1]
            else:
                caption_override = ""  # Remove the command from caption, leave it empty
    else:
        # Otherwise, it's a text broadcast (command followed by text)
        broadcast_text = message.text.split(' ', 1)[1]
    
    # Fetch all served chats and users from database
    all_chats = await get_served_chats()  # Expecting an iterable of chat IDs or dicts with "chat_id"
    all_users = await get_served_users()  # Expecting an iterable of user IDs or dicts with "user_id"
    broadcast_ids = []
    # Collect chat IDs
    for chat in all_chats or []:
        try:
            cid = int(chat["chat_id"]) if isinstance(chat, dict) else int(chat)
            broadcast_ids.append(cid)
        except Exception as err:
            logging.error(f"Error parsing chat from served list: {err}")
    # Collect user IDs
    for user in all_users or []:
        try:
            uid = int(user["user_id"]) if isinstance(user, dict) else int(user)
            broadcast_ids.append(uid)
        except Exception as err:
            logging.error(f"Error parsing user from served list: {err}")
    # Remove duplicates and invalid IDs
    broadcast_ids = list({x for x in broadcast_ids if isinstance(x, int)})
    
    # Optionally include assistant bot's user ID and authorized IDs in targets
    if userbot:
        try:
            assistant = await userbot.get_me()
            if assistant.id not in broadcast_ids:
                broadcast_ids.append(assistant.id)
        except Exception as err:
            logging.warning(f"Failed to get assistant bot ID: {err}")
    for admin_id in AUTHORIZED_IDS:
        if admin_id not in broadcast_ids:
            broadcast_ids.append(admin_id)
    
    # Initialize counters for summary
    success_count = 0
    fail_count = 0
    
    # Iterate through each target chat/user ID and send the broadcast
    for chat_id in broadcast_ids:
        try:
            if target_message:
                # Copy the target message (media or replied content) to the destination
                await target_message.copy(chat_id, caption=caption_override if caption_override is not None else None)
            else:
                # Send the text message to the destination
                await client.send_message(chat_id, broadcast_text)
            success_count += 1
            # Add a small random delay to mitigate FloodWait (acts human-like)
            await asyncio.sleep(random.uniform(0.2, 0.6))
        except FloodWait as e:
            # Telegram is telling us to slow down
            wait_seconds = int(getattr(e, "value", getattr(e, "x", 0)))
            if wait_seconds <= 0:
                wait_seconds = int(getattr(e, "seconds", 0)) or 5
            delay = wait_seconds + random.randint(2, 5)  # add a random buffer
            logging.warning(f"FloodWait of {wait_seconds}s triggered! Pausing broadcast for {delay}s...")
            await asyncio.sleep(delay)
            # Retry sending to the same chat_id after wait
            try:
                if target_message:
                    await target_message.copy(chat_id, caption=caption_override if caption_override is not None else None)
                else:
                    await client.send_message(chat_id, broadcast_text)
                success_count += 1
                await asyncio.sleep(random.uniform(0.2, 0.5))  # minor delay after retry
            except FloodWait as e2:
                # If we immediately hit another FloodWait, skip this target for now
                logging.error(f"Second FloodWait for {chat_id}: skipping this target. Error: {e2}")
                fail_count += 1
                continue
            except InputUserDeactivated:
                # The user account is deactivated, remove from database
                logging.info(f"User {chat_id} is deactivated. Removing from served list.")
                fail_count += 1
                await remove_served_user(chat_id)
                continue
            except UserIsBlocked:
                # Bot is blocked by this user
                logging.info(f"Bot is blocked by user {chat_id}. Removing user from served list.")
                fail_count += 1
                await remove_served_user(chat_id)
                continue
            except ChatWriteForbidden:
                # Bot cannot write in this chat (e.g., not admin or muted in a group)
                logging.info(f"Write forbidden in chat {chat_id}. Removing chat from served list.")
                fail_count += 1
                await remove_served_chat(chat_id)
                continue
            except ChatAdminRequired:
                # Bot lost admin privileges in a channel/chat
                logging.info(f"Admin privileges required in chat {chat_id}. Removing chat from served list.")
                fail_count += 1
                await remove_served_chat(chat_id)
                continue
            except PeerIdInvalid:
                # The target ID is invalid (user might have not started bot or chat no longer exists)
                if str(chat_id).startswith("-100") or chat_id < 0:
                    logging.info(f"Chat {chat_id} no longer valid. Removing from served list.")
                    await remove_served_chat(chat_id)
                else:
                    logging.info(f"User {chat_id} no longer valid. Removing from served list.")
                    await remove_served_user(chat_id)
                fail_count += 1
                continue
            except Exception as ex:
                # Log any other exception and count as failed
                logging.error(f"Error after FloodWait retry for {chat_id}: {ex}")
                fail_count += 1
                continue
            # Continue to next chat_id after handling the FloodWait retry
            continue
        except InputUserDeactivated:
            logging.info(f"User {chat_id} is deactivated. Removing from served list.")
            fail_count += 1
            await remove_served_user(chat_id)
            continue
        except UserIsBlocked:
            logging.info(f"Bot was blocked by user {chat_id}. Removing user from served list.")
            fail_count += 1
            await remove_served_user(chat_id)
            continue
        except ChatWriteForbidden:
            logging.info(f"Cannot send to chat {chat_id} (write forbidden). Removing chat from served list.")
            fail_count += 1
            await remove_served_chat(chat_id)
            continue
        except ChatAdminRequired:
            logging.info(f"Missing admin rights in chat {chat_id}. Removing chat from served list.")
            fail_count += 1
            await remove_served_chat(chat_id)
            continue
        except PeerIdInvalid:
            # Target not found or invalid
            if str(chat_id).startswith("-100") or chat_id < 0:
                logging.info(f"Chat {chat_id} is invalid or no longer exists. Removing from served list.")
                await remove_served_chat(chat_id)
            else:
                logging.info(f"User {chat_id} is invalid or has not started the bot. Removing from served list.")
                await remove_served_user(chat_id)
            fail_count += 1
            continue
        except Exception as err:
            # Catch-all for any other errors
            logging.error(f"Failed to broadcast to {chat_id}: {err}")
            fail_count += 1
            continue
    # end for loop
    
    # Send a summary of the broadcast results
    summary_text = (f"**Broadcast Completed!**\n\n"
                    f"**Successful deliveries:** `{success_count}`\n"
                    f"**Failed deliveries:** `{fail_count}`")
    try:
        await message.reply_text(summary_text, quote=True)
    except Exception as err:
        logging.error(f"Could not send broadcast summary to initiator: {err}")
        # If replying in the context fails, attempt to send the summary to the owner (first authorized user)
        if AUTHORIZED_IDS:
            try:
                await client.send_message(list(AUTHORIZED_IDS)[0], summary_text)
            except Exception:
                pass
