
import asyncio
import random
import logging
import time
from pyrogram import Client, filters
from pyrogram.errors import (
    FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid, 
    ChatWriteForbidden, ChatAdminRequired, ChannelPrivate, UserDeactivated,
    ChatInvalid, RPCError
)

from TeamXmusic import app
from TeamXmusic.utils.database import get_served_chats, get_served_users

# Get authorized users from config
AUTHORIZED_IDS = set()
try:
    from config import OWNER_ID
    if OWNER_ID:
        AUTHORIZED_IDS.add(int(OWNER_ID))
except Exception:
    pass

try:
    from config import SUDO_USERS
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

# Broadcast command with enhanced features
@app.on_message(filters.command(["broadcast", "gcast"]) & filters.user(list(AUTHORIZED_IDS)))
async def broadcast_message(client: Client, message):
    """Enhanced broadcast command with better error handling and statistics"""
    
    # Validate input
    if not message.reply_to_message and len(message.text.split()) < 2:
        return await message.reply_text(
            "**🔊 Broadcast Usage:**\n\n"
            "• Reply to a message to broadcast it\n"
            "• Or use: `/broadcast your message here`\n"
            "• For users only: `/broadcast -users your message`\n"
            "• For chats only: `/broadcast -chats your message`"
        )

    # Parse command arguments
    command_parts = message.text.split()
    broadcast_type = "all"  # all, users, chats
    
    if len(command_parts) > 1 and command_parts[1].startswith("-"):
        if command_parts[1] == "-users":
            broadcast_type = "users"
        elif command_parts[1] == "-chats":
            broadcast_type = "chats"

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
    elif message.media:
        target_message = message
        if message.caption:
            caption_parts = message.caption.split(' ', 1)
            caption_override = caption_parts[1] if len(caption_parts) > 1 else ""
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
        if broadcast_type in ["all", "chats"]:
            all_chats = await get_served_chats()
            for chat in all_chats or []:
                try:
                    cid = int(chat["chat_id"]) if isinstance(chat, dict) else int(chat)
                    broadcast_ids.append(cid)
                except Exception:
                    continue
        
        if broadcast_type in ["all", "users"]:
            all_users = await get_served_users()
            for user in all_users or []:
                try:
                    uid = int(user["user_id"]) if isinstance(user, dict) else int(user)
                    broadcast_ids.append(uid)
                except Exception:
                    continue
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error gathering targets:** {str(e)}")
        return

    # Remove duplicates and ensure all IDs are integers
    broadcast_ids = list(set(x for x in broadcast_ids if isinstance(x, int)))
    
    if not broadcast_ids:
        await status_msg.edit_text("❌ **No targets found for broadcast!**")
        return

    await status_msg.edit_text(f"📊 **Found {len(broadcast_ids)} targets**\nStarting broadcast...")

    # Broadcast statistics
    success_count = 0
    fail_count = 0
    flood_wait_count = 0
    blocked_count = 0
    deleted_count = 0
    forbidden_count = 0
    start_time = time.time()
    
    # Progress tracking
    total_targets = len(broadcast_ids)
    update_interval = max(10, total_targets // 20)  # Update every 5% or minimum 10

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
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
        except FloodWait as e:
            flood_wait_count += 1
            wait_time = int(getattr(e, "value", getattr(e, "x", 0)) or 5)
            
            # For long waits, skip and continue
            if wait_time > 30:
                fail_count += 1
                continue
                
            await asyncio.sleep(wait_time + random.randint(1, 3))
            
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
            
        except (ChatWriteForbidden, ChatAdminRequired, ChannelPrivate, ChatInvalid):
            forbidden_count += 1
            fail_count += 1
            
        except RPCError as e:
            fail_count += 1
            logging.error(f"RPC Error for {chat_id}: {e}")
            
        except Exception as e:
            fail_count += 1
            logging.error(f"Unexpected error for {chat_id}: {e}")
        
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
    
    # Final summary with detailed statistics
    summary_text = (
        f"🎯 **Broadcast Completed!**\n\n"
        f"📊 **Statistics:**\n"
        f"✅ Successfully sent: `{success_count}`\n"
        f"❌ Total failed: `{fail_count}`\n"
        f"🚫 Blocked/Deleted: `{blocked_count + deleted_count}`\n"
        f"⏳ Flood waits: `{flood_wait_count}`\n"
        f"🔒 Forbidden: `{forbidden_count}`\n"
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

# Broadcast to specific chat/user
@app.on_message(filters.command("bcast") & filters.user(list(AUTHORIZED_IDS)))
async def broadcast_to_specific(client: Client, message):
    """Broadcast to specific chat or user"""
    
    if len(message.command) < 2:
        return await message.reply_text(
            "**📢 Specific Broadcast Usage:**\n\n"
            "`/bcast chat_id your message`\n"
            "or reply to a message with `/bcast chat_id`"
        )
    
    try:
        target_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ Invalid chat/user ID!")
    
    if message.reply_to_message:
        target_message = message.reply_to_message
        try:
            await target_message.copy(target_id)
            await message.reply_text(f"✅ Message sent to `{target_id}`")
        except Exception as e:
            await message.reply_text(f"❌ Failed to send: {str(e)}")
    else:
        if len(message.command) < 3:
            return await message.reply_text("❌ Please provide a message to send!")
        
        text = message.text.split(None, 2)[2]
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
        chats = await get_served_chats()
        users = await get_served_users()
        
        chat_count = len(chats) if chats else 0
        user_count = len(users) if users else 0
        total_count = chat_count + user_count
        
        stats_text = (
            f"📊 **Broadcast Statistics**\n\n"
            f"👥 **Groups/Channels:** `{chat_count}`\n"
            f"👤 **Users:** `{user_count}`\n"
            f"📈 **Total Targets:** `{total_count}`\n\n"
            f"🔧 **Available Commands:**\n"
            f"• `/broadcast` - Broadcast to all\n"
            f"• `/broadcast -users` - Users only\n"
            f"• `/broadcast -chats` - Chats only\n"
            f"• `/bcast chat_id` - Specific target\n"
            f"• `/bstats` - Show statistics"
        )
        
        await status_msg.edit_text(stats_text)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Error getting statistics: {str(e)}")
