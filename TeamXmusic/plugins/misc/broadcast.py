
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
from pyrogram.enums import ChatType, ChatMemberStatus

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

# Helper function to check if bot can send messages to a chat
async def can_send_message(client: Client, chat_id: int) -> bool:
    """Check if bot can send messages to a specific chat"""
    try:
        chat = await client.get_chat(chat_id)
        
        # For users (DM), check if user exists and not blocked
        if chat.type == ChatType.PRIVATE:
            return True
        
        # For groups and channels, check bot permissions
        try:
            bot_member = await client.get_chat_member(chat_id, "me")
            
            # Check if bot is banned or restricted
            if bot_member.status in [ChatMemberStatus.BANNED, ChatMemberStatus.RESTRICTED]:
                return False
            
            # For channels, check if bot can post
            if chat.type == ChatType.CHANNEL:
                return bot_member.privileges and bot_member.privileges.can_post_messages
            
            # For groups, bot should be able to send messages if not restricted
            return bot_member.status in [
                ChatMemberStatus.MEMBER, 
                ChatMemberStatus.ADMINISTRATOR, 
                ChatMemberStatus.OWNER
            ]
            
        except UserNotParticipant:
            # Bot is not in the chat
            return False
        except Exception:
            # Default to False if we can't determine permissions
            return False
            
    except Exception:
        return False

# Broadcast command with enhanced features
@app.on_message(filters.command(["broadcast", "gcast"]) & filters.user(list(AUTHORIZED_IDS)))
async def broadcast_message(client: Client, message):
    """Enhanced broadcast command with better error handling and private group support"""
    
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

    await status_msg.edit_text(f"📊 **Found {len(broadcast_ids)} targets**\nValidating permissions...")

    # Pre-validate which chats we can send to
    valid_targets = []
    invalid_count = 0
    
    for chat_id in broadcast_ids:
        if await can_send_message(client, chat_id):
            valid_targets.append(chat_id)
        else:
            invalid_count += 1
    
    if not valid_targets:
        await status_msg.edit_text("❌ **No valid targets found! Bot may not have permissions or chats are invalid.**")
        return

    await status_msg.edit_text(
        f"📊 **Validation Complete:**\n"
        f"✅ Valid targets: `{len(valid_targets)}`\n"
        f"❌ Invalid/No permission: `{invalid_count}`\n"
        f"🚀 Starting broadcast..."
    )

    # Broadcast statistics
    success_count = 0
    fail_count = 0
    flood_wait_count = 0
    blocked_count = 0
    deleted_count = 0
    forbidden_count = 0
    start_time = time.time()
    
    # Progress tracking
    total_targets = len(valid_targets)
    update_interval = max(5, total_targets // 20)  # Update every 5% or minimum 5

    for i, chat_id in enumerate(valid_targets):
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
            await asyncio.sleep(random.uniform(0.05, 0.2))
            
        except FloodWait as e:
            flood_wait_count += 1
            wait_time = int(getattr(e, "value", getattr(e, "x", 0)) or 3)
            
            # For long waits, skip and continue
            if wait_time > 20:
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
            
        except (ChatWriteForbidden, ChatAdminRequired, ChannelPrivate, ChatInvalid, ChannelInvalid):
            forbidden_count += 1
            fail_count += 1
            
        except RPCError as e:
            error_msg = str(e).lower()
            if any(err in error_msg for err in ["channel_invalid", "chat_invalid", "peer_id_invalid"]):
                # Channel/chat doesn't exist anymore, remove from database
                from TeamXmusic.utils.database import chatsdb, usersdb
                try:
                    if chat_id < 0:  # It's a chat/channel
                        await chatsdb.delete_one({"chat_id": chat_id})
                    else:  # It's a user
                        await usersdb.delete_one({"user_id": chat_id})
                except Exception:
                    pass
                deleted_count += 1
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
        f"🎯 Valid targets: `{total_targets}`\n"
        f"🚫 Invalid targets: `{invalid_count}`\n"
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

# Test broadcast command for debugging
@app.on_message(filters.command("testcast") & filters.user(list(AUTHORIZED_IDS)))
async def test_broadcast(client: Client, message):
    """Test broadcast permissions for specific chat"""
    
    if len(message.command) < 2:
        return await message.reply_text(
            "**🧪 Test Broadcast Usage:**\n\n"
            "`/testcast chat_id` - Test permissions for specific chat\n"
            "`/testcast -all` - Test all served chats"
        )
    
    if message.command[1] == "-all":
        status_msg = await message.reply_text("🧪 Testing all served chats...")
        
        all_chats = await get_served_chats()
        valid_chats = []
        invalid_chats = []
        
        for chat in all_chats or []:
            try:
                chat_id = int(chat["chat_id"]) if isinstance(chat, dict) else int(chat)
                if await can_send_message(client, chat_id):
                    valid_chats.append(chat_id)
                else:
                    invalid_chats.append(chat_id)
            except Exception:
                invalid_chats.append(str(chat))
        
        result_text = (
            f"🧪 **Test Results:**\n\n"
            f"✅ Valid chats: `{len(valid_chats)}`\n"
            f"❌ Invalid chats: `{len(invalid_chats)}`\n\n"
            f"**Sample invalid chats:**\n"
        )
        
        for i, chat_id in enumerate(invalid_chats[:5]):
            result_text += f"• `{chat_id}`\n"
        
        if len(invalid_chats) > 5:
            result_text += f"• ... and {len(invalid_chats) - 5} more"
            
        await status_msg.edit_text(result_text)
    else:
        try:
            chat_id = int(message.command[1])
            can_send = await can_send_message(client, chat_id)
            
            try:
                chat_info = await client.get_chat(chat_id)
                chat_type = chat_info.type.name
                chat_title = getattr(chat_info, 'title', 'N/A')
            except Exception:
                chat_type = "Unknown"
                chat_title = "Unknown"
            
            result_text = (
                f"🧪 **Test Result for `{chat_id}`:**\n\n"
                f"📋 **Chat Info:**\n"
                f"• Type: `{chat_type}`\n"
                f"• Title: `{chat_title}`\n"
                f"• Can send: `{'✅ Yes' if can_send else '❌ No'}`"
            )
            
            await message.reply_text(result_text)
            
        except ValueError:
            await message.reply_text("❌ Invalid chat ID!")

# Database cleanup command
@app.on_message(filters.command("cleanup_db") & filters.user(list(AUTHORIZED_IDS)))
async def cleanup_invalid_chats(client: Client, message):
    """Clean up invalid chats/users from database"""
    
    status_msg = await message.reply_text("🧹 **Starting database cleanup...**")
    
    try:
        from TeamXmusic.utils.database import get_served_chats, get_served_users, chatsdb, usersdb
        
        # Get all chats and users
        all_chats = await get_served_chats()
        all_users = await get_served_users()
        
        cleaned_chats = 0
        cleaned_users = 0
        total_checked = 0
        
        # Check chats
        if all_chats:
            for chat in all_chats:
                total_checked += 1
                try:
                    chat_id = int(chat["chat_id"]) if isinstance(chat, dict) else int(chat)
                    if not await can_send_message(client, chat_id):
                        try:
                            await chatsdb.delete_one({"chat_id": chat_id})
                            cleaned_chats += 1
                        except Exception:
                            pass
                except Exception:
                    try:
                        chat_id = int(chat["chat_id"]) if isinstance(chat, dict) else int(chat)
                        await chatsdb.delete_one({"chat_id": chat_id})
                        cleaned_chats += 1
                    except Exception:
                        pass
                
                # Update progress every 20 checks
                if total_checked % 20 == 0:
                    try:
                        await status_msg.edit_text(
                            f"🧹 **Cleaning database...**\n"
                            f"📊 Checked: `{total_checked}`\n"
                            f"🗑 Cleaned chats: `{cleaned_chats}`\n"
                            f"🗑 Cleaned users: `{cleaned_users}`"
                        )
                    except Exception:
                        pass
        
        cleanup_summary = (
            f"🧹 **Database Cleanup Completed!**\n\n"
            f"📊 **Results:**\n"
            f"✅ Total checked: `{total_checked}`\n"
            f"🗑 Invalid chats removed: `{cleaned_chats}`\n"
            f"🗑 Invalid users removed: `{cleaned_users}`\n"
            f"📈 Database is now cleaner!"
        )
        
        await status_msg.edit_text(cleanup_summary)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ **Cleanup failed:** {str(e)}")

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
    
    # Check permissions first
    if not await can_send_message(client, target_id):
        return await message.reply_text(f"❌ Cannot send message to `{target_id}`. Bot may not have permissions or chat is invalid.")
    
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
            f"• `/testcast chat_id` - Test permissions\n"
            f"• `/testcast -all` - Test all chats\n"
            f"• `/bstats` - Show statistics\n"
            f"• `/cleanup_db` - Clean invalid chats"
        )
        
        await status_msg.edit_text(stats_text)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Error getting statistics: {str(e)}")
