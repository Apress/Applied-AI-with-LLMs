#!/usr/bin/env python3

import os
import sys
import asyncio
import signal
import logging
import feedparser
from google import genai
from google.genai import types
import re
from datetime import datetime, timedelta
from telethon import TelegramClient
from dotenv import load_dotenv

# Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
load_dotenv()

# Environment
api_id = int(os.getenv("api_id"))
api_hash = os.getenv("api_hash")
telegram_channel = int(os.getenv("telegram_channel"))
session_name = os.getenv("session_name")
gemini_api_key = os.getenv("gemini_api_key")

# Global
client = TelegramClient(session_name, api_id, api_hash)
stop_event = asyncio.Event()
scheduled_events = set()  # Track scheduled events to avoid duplicates
# variables
HIGH_IMPACT_KW = ["gdp", "inflation", "employment", "interest rate", "cpi"]
SKIP_KW = [
    "holiday",
    "bank holiday",
    "market closed",
    "speech",
    "conference",
    "meeting",
    "test",
    "maintenance",
]
URL = "https://www.myfxbook.com/rss/forex-economic-calendar-events"

fallback_message = "msg out of context"
# Helpers


def minutes_until(dt: datetime) -> float:
    return (dt - datetime.now()).total_seconds() / 60


def cache_result(cache_key: str, result: str, now: datetime) -> str:
    analysis_cache[cache_key] = (now, result)

    # if the cache exceed the max amount of items we clean it
    if len(analysis_cache) > 100:
        expired_keys = []
        for key, (timestamp, _) in analysis_cache.items():
            age_seconds = (now - timestamp).total_seconds()
            if age_seconds > cache_duration:
                expired_keys.append(key)

        # removing all the expired keys
        for key in expired_keys:
            analysis_cache.pop(key, None)

    return result


def build_fallback_analysis(event):
    event_time_formatted = event['event_time'].strftime('%Y-%m-%d %H:%M')
    return (
        f"- Event: {event['title']}\n"
        f"- Scheduled time: {event_time_formatted}\n"
        f"- Impact: {event['impact']}\n\n"
        "⚠️ This AI system was unable to fetch updated information for this release. "
        "Please monitor official sources or price action for actionable details."
    )


# AI optimization: Cache for duplicate events
analysis_cache = {}
cache_duration = 3600  # 1 hour cache


def load_prompt():
    try:
        with open("prompts/trading_analysis.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        logging.error("Prompt file not found")
        return "invalid economic event"


def shutdown(*_):
    logging.warning("Shutting down...")
    stop_event.set()


signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)


def get_events():
    try:
        feed = feedparser.parse(URL)
        events, current_time = [], datetime.now()

        for entry in feed.entries:
            try:
                title, description = entry.get("title", ""), entry.get(
                    "description", ""
                )

                # Extract time
                time_match = re.search(r"<td[^>]*>([^<]+)</td>", description)
                time_left = time_match.group(1).strip() if time_match else "N/A"

                # if it's a past event we do not care about it
                if time_left.startswith("-"):
                    continue

                # Calculate event time
                hours = (
                    int(re.search(r"(\d+)h", time_left).group(1))
                    if re.search(r"(\d+)h", time_left)
                    else 0
                )
                minutes = (
                    int(re.search(r"(\d+)min", time_left).group(1))
                    if re.search(r"(\d+)min", time_left)
                    else 0
                )
                event_time = current_time + timedelta(hours=hours, minutes=minutes)

                # Extract event info
                words = title.split()
                country, event_name = words[0] if words else "Unknown", (
                    " ".join(words[1:]) if len(words) > 1 else title
                )

                # Determine impact
                impact = "medium"
                    
                if any(kw in event_name.lower() for kw in HIGH_IMPACT_KW):
                    impact = "high"

                if impact in ["high", "medium"]:
                    events.append(
                        {
                            "title": title,
                            "country": country,
                            "event": event_name,
                            "event_time": event_time,
                            "impact": impact,
                            "time_left": time_left,
                        }
                    )
            except:
                continue

        logging.info(f"Found {len(events)} events")
        return events
    except Exception as e:
        logging.error(f"RSS error: {e}")
        return []


def should_skip_event(event):
    event_lower = event["event"].lower()

    if any(kw in event_lower for kw in SKIP_KW):
        logging.info(f"Pre-filtered: {event['title']}")
        return True

    mins = minutes_until(event["event_time"])
    if mins > 24 * 60:
        logging.info(f"Pre-filtered distant: {event['title']} ({mins/60:.1f}h)")
        return True

    return False


def setup_gemini():
    return genai.Client(api_key=gemini_api_key)


async def analyze_event(event, gemini_client):
    cache_key = f"{event['title']}_{event['event_time'].strftime('%Y%m%d_%H%M')}"
    now = datetime.now()

    cached = analysis_cache.get(cache_key)
    
    if cached and (now - cached[0]).total_seconds() < cache_duration:
        logging.info(f"Cached: {event['title']}")
        return cached[1]

    prompt_template = load_prompt()

    if prompt_template == "invalid economic event":
        logging.warning("Prompt file missing, using fallback analysis")
        return cache_result(cache_key, build_fallback_analysis(event), now)

    event_data = (
        f"Event: {event['title']}\n"
        f"Time: {event['event_time']}\n"
        f"Impact: {event['impact']}"
    )

    try:
        response = await gemini_client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_template.format(
                event_data=event_data, fallback=fallback_message
            ),
            config=types.GenerateContentConfig(
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            ),
        )
        analysis = (response.text or "").strip() if response else ""
    except Exception as err:
        logging.error(f"AI error: {err}")
        analysis = ""

    if not analysis or analysis == fallback_message:
        logging.info(f"AI fallback used for: {event['title']}")
        result = build_fallback_analysis(event)
    else:
        result = analysis

    return cache_result(cache_key, result, now)


async def ensure_connection():
    if not client.is_connected():
        await client.connect()

    if not await client.is_user_authorized():
        logging.error("Telegram not authorized")
        sys.exit(1)


async def send_message(text):
    try:
        await client.send_message(telegram_channel, text)
        logging.info("Message sent")
    except Exception as e:
        logging.error(f"Send error: {e}")


async def send_notification(event, analysis):
    try:
        event_time_formatted = event['event_time'].strftime('%Y-%m-%d %H:%M')
        message = f"""🚨 **ECONOMIC EVENT IN 1 HOUR** 🚨

📅 **{event['title']}**
⏰ **Time**: {event_time_formatted}

{analysis}

---
*AI Trading Assistant*"""
        await send_message(message)
    except Exception as e:
        logging.error(f"Notification error: {e}")


async def schedule_and_send(event, analysis, delay_seconds):
    try:
        if delay_seconds > 0:
            logging.info(
                f"Notification for {event['title']} in {delay_seconds/60:.1f} min"
            )
            await asyncio.sleep(delay_seconds)
        await send_notification(event, analysis)
    except asyncio.CancelledError:
        logging.warning(f"Notification task cancelled: {event['title']}")
    except Exception as e:
        logging.error(f"Delayed notification error: {e}")


def schedule_notification(event, analysis):
    try:
        event_time = event["event_time"]

        if event_time <= datetime.now():
            return

        # Create unique key for this event
        event_key = f"{event['title']}_{event_time.strftime('%Y%m%d_%H%M')}"
        
        # Skip if already scheduled
        if event_key in scheduled_events:
            logging.debug(f"Already scheduled: {event['title']}")
            return

        notification_time = event_time - timedelta(hours=1)
        delay_seconds = (notification_time - datetime.now()).total_seconds()

        loop = asyncio.get_running_loop()

        if delay_seconds > 0:
            loop.create_task(schedule_and_send(event, analysis, delay_seconds))
            scheduled_events.add(event_key)
            logging.info(f"Scheduled: {event['title']} at {notification_time}")
        else:
            loop.create_task(schedule_and_send(event, analysis, 0))
            scheduled_events.add(event_key)

    except Exception as e:
        logging.error(f"Schedule error: {e}")


def cleanup_past_events():
    # Remove past events from scheduled_events set to prevent memory growth
    now = datetime.now()
    keys_to_remove = []
    
    for event_key in scheduled_events:
        # Extract datetime from key format: "title_YYYYMMDD_HHMM"
        try:
            parts = event_key.rsplit('_', 2)
            if len(parts) >= 3:
                date_str = parts[-2] + '_' + parts[-1]
                event_dt = datetime.strptime(date_str, '%Y%m%d_%H%M')
                # Remove if event time has passed (with 2 hour buffer)
                if event_dt < now - timedelta(hours=2):
                    keys_to_remove.append(event_key)
        except:
            # If parsing fails, keep the key
            pass
    
    for key in keys_to_remove:
        scheduled_events.discard(key)
    
    if keys_to_remove:
        logging.debug(f"Cleaned up {len(keys_to_remove)} past events from schedule")


async def process_events():
    try:
        # Clean up past events first
        cleanup_past_events()
        
        gemini_client = setup_gemini()
        events = []
        now = datetime.now()

        for event in get_events():
            event_time = event.get("event_time")

            if event_time is None:
                continue

            if event_time <= now:
                continue

            if should_skip_event(event):
                continue

            events.append(event)

        if not events:
            logging.info("No valid events to process")
            return

        logging.info(f"Processing {len(events)} events")

        for event in events:
            try:
                analysis = await analyze_event(event, gemini_client)
                if analysis:
                    schedule_notification(event, analysis)
            except Exception as e:
                logging.error(f"Event error: {e}")
                continue

        logging.info(f"Scheduled {len(events)} notifications")
    except Exception as e:
        logging.error(f"Processing error: {e}")


async def main():
    logging.info("🚀 Starting Economic Calendar Bot")

    try:
        await client.start()
        await ensure_connection()
        
        # Process events immediately on startup
        await process_events()

        # Periodic check for new events (every 30 minutes)
        check_interval = 30 * 60  # 30 minutes in seconds
        
        logging.info("⏰ Starting periodic event checks (every 30 minutes)...")
        
        while not stop_event.is_set():
            try:
                # Wait for check interval or stop event
                done, pending = await asyncio.wait(
                    [asyncio.create_task(asyncio.sleep(check_interval)),
                     asyncio.create_task(stop_event.wait())],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancel pending tasks
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                
                # If stop event was set, break
                if stop_event.is_set():
                    break
                
                # Process new events
                logging.info("🔄 Checking for new events...")
                await process_events()
                
            except Exception as e:
                logging.error(f"Periodic check error: {e}")
                # Wait a bit before retrying to avoid tight error loops
                await asyncio.sleep(60)
                
    except Exception as e:
        logging.error(f"App error: {e}")
    finally:
        await client.disconnect()
        logging.info("✅ Stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"Script error: {e}")
        sys.exit(1)
