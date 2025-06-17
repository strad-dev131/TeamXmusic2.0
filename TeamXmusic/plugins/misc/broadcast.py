import asyncio
import random
import logging
import time
from pyrogram import Client, filters
from pyrogram.errors import (
    FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid, 
    ChatWriteForbidden, ChatAdminRequired, ChannelPrivate, UserDeactivated,
    ChatInvalid, RPCError, ChannelInvalid, UserNotParticipant
)
from pyrogram.enums import ChatType

from TeamXmusic import app
from TeamXmusic.utils.database import get_served_users

# Get authorized users from config
AUTHORIZED_IDS = set()
try:
    from config import OWNER_ID, SUDO_USERS, LOGGER_ID
    if OWNER_ID:
        AUTHORIZED_IDS.add(int(OWNER_ID))
    if SUDO_USERS:
        if isinstance(SUDO_USERS, (list, tuple, set)):
            for uid in SUDO_USERS:
                try:
                    AUTHORIZED_IDS.add(int(uid))
                except (ValueError, TypeError):
                    continue
        else:
            for uid in str(SUDO_USERS).replace(",", " ").split():
                try:
                    AUTHORIZED_IDS.add(int(uid))
                except (ValueError, TypeError):
                    continue
except Exception:
    pass

if not AUTHORIZED_IDS:
    logging.warning("No authorized user IDs specified for broadcasts.")

# Enhanced broadcast command for DMs and log group only
@app.on_message(filters.command(["broadcast", "gcast"]) & filters.user(list(AUTHORIZED_IDS)))
async def broadcast_message(client: Client, message):
    """Broadcast command for DMs and log group only"""

    # Validate input
    if not message.reply_to_message and len(message.text.split()) < 2:
        return await message.reply_text(
            "**🔊 Broadcast Usage:**\n\n"
            "• Reply to a message to broadcast it\n"
            "• Or use: `/broadcast your message here`\n"
            "• For users only: `/broadcast -users your message`\n"
            "• For log group: `/broadcast -log your message`"
        )

    # Parse command arguments
    command_parts = message.text.split()
    broadcast_type = "users"  # Default to users only

    if len(command_parts) > 1 and command_parts[1].startswith("-"):
        if command_parts[1] == "-users":
            broadcast_type = "users"
        elif command_parts[1] == "-log":
            broadcast_type = "log"
        else:
            broadcast_type = "users"  # Default fallback

    # Determine what to broadcast
    target_message = None
    caption_override = None
    broadcast_text = None

    if message.reply_to_message:
        target_message = message.reply_to_message
        # Check if there's custom caption
        text_parts = message.text.split(' ', 1)
        if len(text_parts) > 1 and not text_parts[1].startswith('-'):
            caption_override = text_parts[1]
        elif len(text_parts) > 2 and text_parts[1].startswith('-'):
            caption_override = text_parts[2] if len(command_parts) > 2 else None
    else:
        # Text broadcast
        text_parts = message.text.split(' ', 1)
        if len(text_parts) > 1:
            if text_parts[1].startswith('-') and len(command_parts) > 2:
                broadcast_text = ' '.join(command_parts[2:])
            elif not text_parts[1].startswith('-'):
                broadcast_text = text_parts[1]

        if not broadcast_text:
            return await message.reply_text("❌ Please provide text to broadcast!")

    # Send initial status message
    status_msg = await message.reply_text("🔄 **Starting broadcast...**\nGathering targets...")

    # Get broadcast targets
    broadcast_ids = []

    try:
        if broadcast_type == "users":
            # Get all users for DM broadcast
            all_users = await get_served_users()
            for user in all_users or []:
                try:
                    uid = int(user["user_id"]) if isinstance(user, dict) else int(user)
                    broadcast_ids.append(uid)
                except Exception:
                    continue
        elif broadcast_type == "log":
            # Only send to log group
            try:
                if LOGGER_ID:
                    broadcast_ids.append(int(LOGGER_ID))
            except Exception:
                pass
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error gathering targets:** {str(e)}")
        return

    # Remove duplicates
    broadcast_ids = list(set(broadcast_ids))

    if not broadcast_ids:
        await status_msg.edit_text("❌ **No targets found for broadcast!**")
        return

    await status_msg.edit_text(f"📊 **Found {len(broadcast_ids)} targets**\n🚀 Starting broadcast...")

    # Broadcast statistics
    success_count = 0
    fail_count = 0
    flood_wait_count = 0
    blocked_count = 0
    deleted_count = 0
    start_time = time.time()

    # Progress tracking
    total_targets = len(broadcast_ids)
    update_interval = max(5, total_targets // 20)

    for i, chat_id in enumerate(broadcast_ids):
        try:
            # Send the message
            if target_message:
                if target_message.text:
                    await client.send_message(
                        chat_id, 
                        target_message.text if caption_override is None else caption_override
                    )
                elif target_message.photo:
                    await target_message.copy(chat_id, caption=caption_override)
                elif target_message.video:
                    await target_message.copy(chat_id, caption=caption_override)
                elif target_message.audio:
                    await target_message.copy(chat_id, caption=caption_override)
                elif target_message.document:
                    await target_message.copy(chat_id, caption=caption_override)
                elif target_message.voice:
                    await target_message.copy(chat_id, caption=caption_override)
                elif target_message.video_note:
                    await target_message.copy(chat_id, caption=caption_override)
                elif target_message.sticker:
                    await target_message.copy(chat_id)
                elif target_message.animation:
                    await target_message.copy(chat_id, caption=caption_override)
                else:
                    await target_message.copy(chat_id, caption=caption_override)
            else:
                await client.send_message(chat_id, broadcast_text)

            success_count += 1

            # Random delay to avoid flood
            await asyncio.sleep(random.uniform(0.05, 0.15))

        except FloodWait as e:
            flood_wait_count += 1
            wait_time = int(getattr(e, "value", getattr(e, "x", 0)) or 3)

            # For long waits, skip and continue
            if wait_time > 15:
                fail_count += 1
                continue

            await asyncio.sleep(wait_time + random.randint(1, 2))

            # Retry after flood wait
            try:
                if target_message:
                    await target_message.copy(chat_id, caption=caption_override)
                else:
                    await client.send_message(chat_id, broadcast_text)
                success_count += 1
            except Exception:
                fail_count += 1

        except (UserIsBlocked, UserDeactivated):
            blocked_count += 1
            fail_count += 1

        except (InputUserDeactivated, PeerIdInvalid):
            deleted_count += 1
            fail_count += 1
            # Clean up invalid users
            from TeamXmusic.utils.database import usersdb
            try:
                await usersdb.delete_one({"user_id": chat_id})
            except Exception:
                pass

        except Exception as e:
            fail_count += 1
            error_msg = str(e).lower()
            logging.error(f"Error sending to {chat_id}: {e}")

            # Clean up invalid entries
            if any(word in error_msg for word in ["invalid", "not found", "peer_id"]):
                from TeamXmusic.utils.database import usersdb
                try:
                    await usersdb.delete_one({"user_id": chat_id})
                except Exception:
                    pass

        # Update progress periodically
        if (i + 1) % update_interval == 0 or i == total_targets - 1:
            progress = ((i + 1) / total_targets) * 100
            try:
                await status_msg.edit_text(
                    f"📊 **Broadcast Progress:** {progress:.1f}%\n"
                    f"✅ Sent: `{success_count}`\n"
                    f"❌ Failed: `{fail_count}`\n"
                    f"⏳ Remaining: `{total_targets - i - 1}`"
                )
            except Exception:
                pass

    # Calculate broadcast duration
    end_time = time.time()
    duration = int(end_time - start_time)

    # Final summary
    summary_text = (
        f"🎯 **Broadcast Completed!**\n\n"
        f"📊 **Statistics:**\n"
        f"✅ Successfully sent: `{success_count}`\n"
        f"❌ Total failed: `{fail_count}`\n"
        f"🚫 Blocked/Deleted: `{blocked_count + deleted_count}`\n"
        f"⏳ Flood waits: `{flood_wait_count}`\n"
        f"🎯 Total targets: `{total_targets}`\n"
        f"⏱ Duration: `{duration}s`\n"
        f"📈 Success rate: `{(success_count/total_targets*100):.1f}%`"
    )

    try:
        await status_msg.edit_text(summary_text)
    except Exception:
        try:
            await message.reply_text(summary_text)
        except Exception:
            pass

# Broadcast to specific user/log group
@app.on_message(filters.command("bcast") & filters.user(list(AUTHORIZED_IDS)))
async def broadcast_to_specific(client: Client, message):
    """Broadcast to specific user or log group"""

    if len(message.command) < 2:
        return await message.reply_text(
            "**📢 Specific Broadcast Usage:**\n\n"
            "`/bcast user_id your message` - Send to specific user\n"
            "`/bcast -log your message` - Send to log group\n"
            "or reply to a message with `/bcast user_id` or `/bcast -log`"
        )

    target_param = message.command[1]

    if target_param == "-log":
        try:
            target_id = int(LOGGER_ID) if LOGGER_ID else None
            if not target_id:
                return await message.reply_text("❌ Log group ID not configured!")
        except Exception:
            return await message.reply_text("❌ Invalid log group configuration!")
    else:
        try:
            target_id = int(target_param)
            if target_id < 0:
                return await message.reply_text("❌ Only user IDs and log group are allowed!")
        except ValueError:
            return await message.reply_text("❌ Invalid user ID!")

    if message.reply_to_message:
        target_message = message.reply_to_message
        try:
            await target_message.copy(target_id)
            await message.reply_text(f"✅ Message sent to `{target_id}`")
        except Exception as e:
            await message.reply_text(f"❌ Failed to send: {str(e)}")
    else:
        start_idx = 3 if target_param == "-log" else 2
        if len(message.command) < start_idx + 1:
            return await message.reply_text("❌ Please provide a message to send!")

        text = message.text.split(None, start_idx)[start_idx]
        try:
            await client.send_message(target_id, text)
            await message.reply_text(f"✅ Message sent to `{target_id}`")
        except Exception as e:
            await message.reply_text(f"❌ Failed to send: {str(e)}")

# Get broadcast statistics
@app.on_message(filters.command("bstats") & filters.user(list(AUTHORIZED_IDS)))
async def broadcast_stats(client: Client, message):
    """Get broadcast target statistics"""

    status_msg = await message.reply_text("📊 Gathering broadcast statistics...")

    try:
        users = await get_served_users()
        user_count = len(users) if users else 0

        log_status = "✅ Configured" if LOGGER_ID else "❌ Not configured"

        stats_text = (
            f"📊 **Broadcast Statistics**\n\n"
            f"👤 **Users (DMs):** `{user_count}`\n"
            f"📋 **Log Group:** `{log_status}`\n\n"
            f"🔧 **Available Commands:**\n"
            f"• `/broadcast message` - Broadcast to all users\n"
            f"• `/broadcast -users message` - Users only\n"
            f"• `/broadcast -log message` - Log group only\n"
            f"• `/bcast user_id message` - Specific user\n"
            f"• `/bcast -log message` - Log group\n"
            f"• `/bstats` - Show statistics\n\n"
            f"**Note:** Groups are not supported to avoid permission issues."
        )

        await status_msg.edit_text(stats_text)

    except Exception as e:
        await status_msg.edit_text(f"❌ Error getting statistics: {str(e)}")

# Clean up invalid users from database
@app.on_message(filters.command("cleanup_users") & filters.user(list(AUTHORIZED_IDS)))
async def cleanup_invalid_users(client: Client, message):
    """Clean up invalid users from database"""

    status_msg = await message.reply_text("🧹 **Starting user database cleanup...**")

    try:
        from TeamXmusic.utils.database import get_served_users, usersdb

        all_users = await get_served_users()
        cleaned_users = 0
        total_checked = 0

        if all_users:
            for user in all_users:
                total_checked += 1
                try:
                    user_id = int(user["user_id"]) if isinstance(user, dict) else int(user)
                    # Try to get user info
                    try:
                        await client.get_users(user_id)
                    except Exception:
                        # User doesn't exist or bot can't access
                        await usersdb.delete_one({"user_id": user_id})
                        cleaned_users += 1
                except Exception:
                    # Invalid user entry
                    try:
                        user_id = int(user["user_id"]) if isinstance(user, dict) else int(user)
                        await usersdb.delete_one({"user_id": user_id})
                        cleaned_users += 1
                    except Exception:
                        pass

                # Update progress every 50 checks
                if total_checked % 50 == 0:
                    try:
                        await status_msg.edit_text(
                            f"🧹 **Cleaning user database...**\n"
                            f"📊 Checked: `{total_checked}`\n"
                            f"🗑 Cleaned: `{cleaned_users}`"
                        )
                    except Exception:
                        pass

        cleanup_summary = (
            f"🧹 **User Database Cleanup Completed!**\n\n"
            f"📊 **Results:**\n"
            f"✅ Total checked: `{total_checked}`\n"
            f"🗑 Invalid users removed: `{cleaned_users}`\n"
            f"📈 Database is now cleaner!"
        )

        await status_msg.edit_text(cleanup_summary)

    except Exception as e:
        await status_msg.edit_text(f"❌ **Cleanup failed:** {str(e)}")
