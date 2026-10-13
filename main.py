
import os
import asyncio
import logging
import time
from zoneinfo import ZoneInfo

import aiohttp
import discord
import yt_dlp
from discord.ext import commands, tasks

# =====================================================
# ANIME WEATHER ULTIMATE
# Persistent button panel + automatic weather + music
# =====================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("anime-weather")

TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
WEATHER_CHANNEL_ID = int(os.getenv("WEATHER_CHANNEL_ID", "0") or 0)
PANEL_CHANNEL_ID = int(os.getenv("PANEL_CHANNEL_ID", "0") or 0)
MUSIC_VOICE_CHANNEL_ID = int(os.getenv("MUSIC_VOICE_CHANNEL_ID", "0") or 0)
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0") or 0)

AUTO_MUSIC_QUERY = os.getenv(
    "AUTO_MUSIC_QUERY", "anime lofi morning mix"
).strip()
MUSIC_MINUTES = max(1, int(os.getenv("AUTO_MUSIC_MINUTES", "30") or 30))
MORNING_HOUR = int(os.getenv("MORNING_HOUR", "7") or 7)
MORNING_MINUTE = int(os.getenv("MORNING_MINUTE", "0") or 0)

KST = ZoneInfo("Asia/Seoul")
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
PANEL_MARKER = "ANIME_WEATHER_PANEL_V1"

CITIES = {
    "kr": {
        "name": "Daejeon",
        "label": "대전 · Daejeon",
        "flag": "🇰🇷",
        "lat": 36.3504,
        "lon": 127.3845,
        "timezone": "Asia/Seoul",
        "gif": "ANIME_KR_IMAGE",
    },
    "vn": {
        "name": "Đà Nẵng",
        "label": "Đà Nẵng · Da Nang",
        "flag": "🇻🇳",
        "lat": 16.0544,
        "lon": 108.2022,
        "timezone": "Asia/Ho_Chi_Minh",
        "gif": "ANIME_VN_IMAGE",
    },
}

WEATHER = {
    0: ("Trời quang", "☀️", 0xFFD98A),
    1: ("Ít mây", "🌤️", 0xFFD98A),
    2: ("Mây rải rác", "⛅", 0x9BCBFF),
    3: ("Nhiều mây", "☁️", 0xA9B7C6),
    45: ("Sương mù", "🌫️", 0xB9C7D5),
    48: ("Sương muối", "🌫️", 0xB9C7D5),
    51: ("Mưa phùn nhẹ", "🌦️", 0x8B9DFF),
    53: ("Mưa phùn", "🌦️", 0x8B9DFF),
    55: ("Mưa phùn dày", "🌧️", 0x8B9DFF),
    56: ("Mưa băng nhẹ", "🌧️", 0x8B9DFF),
    57: ("Mưa băng mạnh", "🌧️", 0x8B9DFF),
    61: ("Mưa nhẹ", "🌧️", 0x8B9DFF),
    63: ("Mưa vừa", "🌧️", 0x8B9DFF),
    65: ("Mưa lớn", "⛈️", 0x6E7FE8),
    66: ("Mưa băng nhẹ", "🌧️", 0x8B9DFF),
    67: ("Mưa băng mạnh", "⛈️", 0x6E7FE8),
    71: ("Tuyết nhẹ", "🌨️", 0x79C9FF),
    73: ("Tuyết vừa", "❄️", 0x79C9FF),
    75: ("Tuyết lớn", "❄️", 0x79C9FF),
    77: ("Hạt tuyết", "❄️", 0x79C9FF),
    80: ("Mưa rào nhẹ", "🌦️", 0x8B9DFF),
    81: ("Mưa rào", "🌧️", 0x8B9DFF),
    82: ("Mưa rào mạnh", "⛈️", 0x6E7FE8),
    85: ("Mưa tuyết nhẹ", "🌨️", 0x79C9FF),
    86: ("Mưa tuyết mạnh", "❄️", 0x79C9FF),
    95: ("Dông", "⛈️", 0x6E7FE8),
    96: ("Dông có mưa đá", "⛈️", 0x6E7FE8),
    99: ("Dông mưa đá mạnh", "⛈️", 0x6E7FE8),
}

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

panel_lock = asyncio.Lock()
music_lock = asyncio.Lock()
music_timer_task = None
music_deadline = 0
music_queue = []
music_query = AUTO_MUSIC_QUERY
last_morning_date = None
view_registered = False


def weather_info(code):
    return WEATHER.get(
        int(code or 0),
        ("Chưa rõ", "🌈", 0x9BE3D3),
    )


async def fetch_weather(city_key):
    city = CITIES[city_key]

    params = {
        "latitude": city["lat"],
        "longitude": city["lon"],
        "timezone": city["timezone"],
        "forecast_days": 7,
        "current": (
            "temperature_2m,relative_humidity_2m,"
            "apparent_temperature,precipitation,weather_code,"
            "wind_speed_10m,wind_gusts_10m"
        ),
        "hourly": (
            "temperature_2m,precipitation_probability,"
            "precipitation,weather_code,wind_speed_10m"
        ),
        "daily": (
            "weather_code,temperature_2m_max,temperature_2m_min,"
            "precipitation_probability_max,precipitation_sum,"
            "wind_speed_10m_max"
        ),
    }

    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(WEATHER_URL, params=params) as response:
            response.raise_for_status()
            data = await response.json()

    return city, data


def weather_advice(current, daily):
    temp = current.get("temperature_2m")
    feels = current.get("apparent_temperature")
    rain = (daily.get("precipitation_probability_max") or [0])[0] or 0
    wind = current.get("wind_speed_10m") or 0
    gust = current.get("wind_gusts_10m") or 0
    code = int(current.get("weather_code") or 0)

    messages = []

    if rain >= 60 or code in (61, 63, 65, 80, 81, 82, 95, 96, 99):
        messages.append("☂️ Khả năng mưa cao — nhớ mang ô.")

    if temp is not None and temp <= 5:
        messages.append("🧣 Trời rất lạnh — mặc nhiều lớp để giữ ấm.")
    elif temp is not None and temp <= 12:
        messages.append("🧥 Nên mang áo khoác.")

    if feels is not None and feels >= 32:
        messages.append("🧢 Cảm giác nóng — uống nước, nghỉ trong bóng râm.")
    elif temp is not None and temp >= 30:
        messages.append("💧 Trời nóng — nhớ uống đủ nước.")

    if wind >= 35 or gust >= 50:
        messages.append("💨 Gió mạnh — cẩn thận khi đi ngoài trời.")

    if not messages:
        messages.append("🌿 Thời tiết khá ổn — chúc m một ngày tốt lành!")

    return "\n".join(messages)


def make_today_embed(city, data):
    current = data["current"]
    daily = data["daily"]
    status, emoji, color = weather_info(current.get("weather_code"))

    high = (daily.get("temperature_2m_max") or ["—"])[0]
    low = (daily.get("temperature_2m_min") or ["—"])[0]
    rain = (daily.get("precipitation_probability_max") or [0])[0]
    rain = rain if rain is not None else 0

    embed = discord.Embed(
        title=f"{city['flag']} {city['label']} • {emoji} {status}",
        description=(
            f"# {current.get('temperature_2m', '—')}°C\n"
            f"Cảm giác như **{current.get('apparent_temperature', '—')}°C**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🌡️ **Cao / thấp:** {high}° / {low}°C\n"
            f"💧 **Độ ẩm:** {current.get('relative_humidity_2m', '—')}%\n"
            f"☔ **Khả năng mưa:** {rain}%\n"
            f"🌧️ **Lượng mưa hiện tại:** {current.get('precipitation', '—')} mm\n"
            f"💨 **Gió:** {current.get('wind_speed_10m', '—')} km/h "
            f"· giật {current.get('wind_gusts_10m', '—')} km/h\n\n"
            f"**✦ Lời nhắn hôm nay**\n"
            f"{weather_advice(current, daily)}"
        ),
        color=color,
    )

    gif_url = os.getenv(city["gif"], "").strip()
    if gif_url.startswith(("https://", "http://")):
        embed.set_image(url=gif_url)

    embed.set_footer(
        text=f"◈ ANIME WEATHER • Open-Meteo • {current.get('time', '—')}"
    )
    return embed


def make_hourly_embed(city, data):
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    now = data.get("current", {}).get("time", "")
    start = times.index(now) if now in times else 0

    lines = []

    for i in range(start, min(start + 8, len(times))):
        status, icon, _ = weather_info(
            (hourly.get("weather_code") or [0])[i]
        )
        temp = (hourly.get("temperature_2m") or ["—"])[i]
        rain = (hourly.get("precipitation_probability") or [0])[i]
        wind = (hourly.get("wind_speed_10m") or ["—"])[i]

        lines.append(
            f"`{times[i][-5:]}` {icon} **{temp}°C** · "
            f"mưa {rain or 0}% · gió {wind} km/h · {status}"
        )

    _, _, color = weather_info(data["current"].get("weather_code"))

    embed = discord.Embed(
        title=f"⏳ {city['flag']} {city['name']} • 8 giờ tới",
        description="\n".join(lines) or "Chưa có dữ liệu theo giờ.",
        color=color,
    )
    embed.set_footer(text="Dự báo theo giờ • Open-Meteo")
    return embed


def make_week_embed(city, data):
    daily = data.get("daily", {})
    lines = []

    for i, date in enumerate((daily.get("time") or [])[:7]):
        status, icon, _ = weather_info(
            (daily.get("weather_code") or [0])[i]
        )
        high = (daily.get("temperature_2m_max") or ["—"])[i]
        low = (daily.get("temperature_2m_min") or ["—"])[i]
        rain = (daily.get("precipitation_probability_max") or [0])[i]
        amount = (daily.get("precipitation_sum") or ["—"])[i]

        lines.append(
            f"**{date}** · {icon} **{high}° / {low}°C** · "
            f"mưa {rain or 0}% · {amount} mm\n└ {status}"
        )

    _, _, color = weather_info(data["current"].get("weather_code"))

    embed = discord.Embed(
        title=f"📅 {city['flag']} {city['name']} • Dự báo 7 ngày",
        description="\n".join(lines) or "Chưa có dữ liệu tuần.",
        color=color,
    )
    embed.set_footer(text="Dự báo có thể thay đổi • Open-Meteo")
    return embed


def make_panel_embed():
    embed = discord.Embed(
        title="◈ 𝐀𝐍𝐈𝐌𝐄 𝐖𝐄𝐀𝐓𝐇𝐄𝐑",
        description=(
            "```ansi\n"
            "\u001b[1;36m✦ DAILY FORECAST • ANIME ATMOSPHERE ✦\u001b[0m\n"
            "```\n"
            "Bấm nút bên dưới — **không cần gõ lệnh**.\n\n"
            "🌤️ Hôm nay　·　⏳ Theo giờ　·　📅 7 ngày\n"
            "🇰🇷 Daejeon　·　🇻🇳 Đà Nẵng　·　🔄 Làm mới\n"
            "🎵 Test nhạc　·　⏹ Dừng nhạc *(admin)*\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🕖 Bản tin tự động: **{MORNING_HOUR:02d}:"
            f"{MORNING_MINUTE:02d} KST**\n"
            f"🎧 Nhạc tự phát: **{MUSIC_MINUTES} phút** mỗi sáng\n"
            "♾️ Panel được khôi phục sau khi bot khởi động lại."
        ),
        color=0x9BE3D3,
    )
    embed.set_footer(text=PANEL_MARKER)
    return embed


async def get_text_channel(channel_id):
    if not channel_id:
        return None

    channel = bot.get_channel(channel_id)

    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except Exception:
            log.exception("Không lấy được text channel %s", channel_id)
            return None

    if isinstance(channel, (discord.TextChannel, discord.Thread)):
        return channel

    return None


async def ensure_panel():
    channel = await get_text_channel(PANEL_CHANNEL_ID or WEATHER_CHANNEL_ID)

    if channel is None:
        log.error("Thiếu PANEL_CHANNEL_ID hoặc WEATHER_CHANNEL_ID hợp lệ.")
        return

    async with panel_lock:
        try:
            async for message in channel.history(limit=100):
                if (
                    message.author == bot.user
                    and message.embeds
                    and PANEL_MARKER in (message.embeds[0].footer.text or "")
                ):
                    await message.edit(
                        embed=make_panel_embed(),
                        view=WeatherPanel(),
                    )
                    log.info("Panel đã khôi phục: %s", message.id)
                    return

            message = await channel.send(
                embed=make_panel_embed(),
                view=WeatherPanel(),
            )
            log.info("Panel đã tạo: %s", message.id)

        except Exception:
            log.exception(
                "Không tạo được panel. Kiểm tra quyền View Channel, "
                "Send Messages, Embed Links, Read Message History."
            )


async def send_morning_weather():
    channel = await get_text_channel(WEATHER_CHANNEL_ID)

    if channel is None:
        log.error("WEATHER_CHANNEL_ID không hợp lệ.")
        return

    for key in ("kr", "vn"):
        try:
            city, data = await fetch_weather(key)
            await channel.send(embed=make_today_embed(city, data))
            log.info("Đã gửi thời tiết sáng: %s", city["name"])
        except Exception:
            log.exception("Gửi bản tin thời tiết thất bại: %s", key)


# ==================== YOUTUBE MUSIC ====================

YTDLP_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "socket_timeout": 20,
    "retries": 2,
    "extractor_retries": 2,
    "default_search": "ytsearch5",
}


def search_youtube(query):
    with yt_dlp.YoutubeDL(YTDLP_OPTIONS) as ydl:
        info = ydl.extract_info(f"ytsearch5:{query}", download=False)

    if info and info.get("entries"):
        return [
            item for item in info["entries"]
            if item and item.get("webpage_url")
        ]

    return []


def resolve_youtube(url):
    options = {
        **YTDLP_OPTIONS,
        "default_search": "auto",
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)

    if info and info.get("entries"):
        info = next((item for item in info["entries"] if item), None)

    if not info or not info.get("url"):
        raise RuntimeError("YouTube không trả về audio stream.")

    return info


async def get_voice():
    if not MUSIC_VOICE_CHANNEL_ID:
        raise RuntimeError("Chưa nhập MUSIC_VOICE_CHANNEL_ID.")

    channel = (
        bot.get_channel(MUSIC_VOICE_CHANNEL_ID)
        or await bot.fetch_channel(MUSIC_VOICE_CHANNEL_ID)
    )

    if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
        raise RuntimeError("MUSIC_VOICE_CHANNEL_ID không phải voice channel.")

    voice = discord.utils.get(bot.voice_clients, guild=channel.guild)

    if voice and voice.is_connected():
        if voice.channel != channel:
            await voice.move_to(channel)
    else:
        voice = await channel.connect()

    return voice


async def play_next():
    global music_queue

    async with music_lock:
        if time.time() >= music_deadline:
            return

        voice = next(
            (item for item in bot.voice_clients if item.is_connected()),
            None,
        )

        if voice is None:
            log.warning("Không có voice connection để phát nhạc.")
            return

        if not music_queue:
            try:
                music_queue = await asyncio.to_thread(
                    search_youtube, music_query
                )
            except Exception:
                log.exception("Tìm nhạc trên YouTube thất bại.")
                return

        if not music_queue:
            log.warning("Không tìm thấy bài nhạc.")
            return

        item = music_queue.pop(0)

        try:
            audio = await asyncio.to_thread(
                resolve_youtube, item["webpage_url"]
            )

            source = discord.FFmpegPCMAudio(
                audio["url"],
                before_options=(
                    "-reconnect 1 -reconnect_streamed 1 "
                    "-reconnect_delay_max 5"
                ),
                options="-vn",
            )

            log.info(
                "Đang phát nhạc: %s",
                audio.get("title", item.get("title", "YouTube")),
            )

            def after_play(error):
                if error:
                    log.warning("Lỗi phát audio: %s", error)

                if time.time() < music_deadline:
                    asyncio.run_coroutine_threadsafe(
                        play_next(), bot.loop
                    )

            voice.play(source, after=after_play)

        except Exception:
            log.exception("Không phát được bài: %s", item.get("title"))

            if time.time() < music_deadline:
                asyncio.get_running_loop().call_later(
                    2,
                    lambda: asyncio.create_task(play_next()),
                )


async def start_music():
    global music_timer_task, music_deadline, music_query, music_queue

    voice = await get_voice()
    voice.stop()

    music_query = AUTO_MUSIC_QUERY
    music_queue = []
    music_deadline = time.time() + MUSIC_MINUTES * 60

    try:
        music_queue = await asyncio.to_thread(
            search_youtube, music_query
        )
    except Exception:
        music_deadline = 0
        raise

    if not music_queue:
        music_deadline = 0
        raise RuntimeError("YouTube không tìm thấy bài nhạc.")

    await play_next()

    if music_timer_task and not music_timer_task.done():
        music_timer_task.cancel()

    music_timer_task = asyncio.create_task(stop_music_after_limit())
    log.info("Nhạc bắt đầu; giới hạn %s phút.", MUSIC_MINUTES)


async def stop_music_after_limit():
    try:
        await asyncio.sleep(MUSIC_MINUTES * 60)
        await stop_music()
        log.info("Đã kết thúc phiên nhạc.")
    except asyncio.CancelledError:
        pass


async def stop_music():
    global music_deadline, music_queue, music_timer_task

    music_deadline = 0
    music_queue = []

    current_task = asyncio.current_task()

    if (
        music_timer_task
        and music_timer_task is not current_task
        and not music_timer_task.done()
    ):
        music_timer_task.cancel()

    for voice in list(bot.voice_clients):
        try:
            if voice.is_connected():
                voice.stop()
                await voice.disconnect(force=True)
        except Exception:
            log.exception("Dừng nhạc thất bại.")


async def run_morning_tasks():
    await send_morning_weather()

    try:
        await start_music()
    except Exception:
        log.exception("Không bật được nhạc tự động buổi sáng.")


# ==================== PERSISTENT BUTTON PANEL ====================

async def user_is_admin(interaction):
    if ADMIN_USER_ID and interaction.user.id == ADMIN_USER_ID:
        return True

    return (
        isinstance(interaction.user, discord.Member)
        and interaction.user.guild_permissions.administrator
    )


class WeatherPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def show_weather(self, interaction, city_key, mode):
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            city, data = await fetch_weather(city_key)

            if mode == "today":
                embed = make_today_embed(city, data)
            elif mode == "hourly":
                embed = make_hourly_embed(city, data)
            else:
                embed = make_week_embed(city, data)

            await interaction.followup.send(
                embed=embed,
                ephemeral=True,
            )

        except Exception:
            log.exception("Nút thời tiết gặp lỗi.")
            await interaction.followup.send(
                "⚠️ Chưa lấy được dữ liệu thời tiết. Thử lại sau nhé.",
                ephemeral=True,
            )

    @discord.ui.button(
        label="Hôm nay",
        emoji="🌤️",
        style=discord.ButtonStyle.primary,
        custom_id="animeweather:today",
        row=0,
    )
    async def today(self, interaction, button):
        await self.show_weather(interaction, "kr", "today")

    @discord.ui.button(
        label="Theo giờ",
        emoji="⏳",
        style=discord.ButtonStyle.primary,
        custom_id="animeweather:hourly",
        row=0,
    )
    async def hourly(self, interaction, button):
        await self.show_weather(interaction, "kr", "hourly")

    @discord.ui.button(
        label="7 ngày",
        emoji="📅",
        style=discord.ButtonStyle.primary,
        custom_id="animeweather:week",
        row=0,
    )
    async def week(self, interaction, button):
        await self.show_weather(interaction, "kr", "week")

    @discord.ui.button(
        label="Daejeon",
        emoji="🇰🇷",
        style=discord.ButtonStyle.secondary,
        custom_id="animeweather:kr",
        row=1,
    )
    async def korea(self, interaction, button):
        await self.show_weather(interaction, "kr", "today")

    @discord.ui.button(
        label="Đà Nẵng",
        emoji="🇻🇳",
        style=discord.ButtonStyle.secondary,
        custom_id="animeweather:vn",
        row=1,
    )
    async def vietnam(self, interaction, button):
        await self.show_weather(interaction, "vn", "today")

    @discord.ui.button(
        label="Làm mới panel",
        emoji="🔄",
        style=discord.ButtonStyle.secondary,
        custom_id="animeweather:refresh",
        row=1,
    )
    async def refresh(self, interaction, button):
        if not await user_is_admin(interaction):
            await interaction.response.send_message(
                "Chỉ admin mới dùng được nút này.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        await ensure_panel()
        await interaction.followup.send(
            "✅ Đã kiểm tra/cập nhật bảng nút.",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Test nhạc",
        emoji="🎵",
        style=discord.ButtonStyle.success,
        custom_id="animeweather:testmusic",
        row=2,
    )
    async def test_music(self, interaction, button):
        if not await user_is_admin(interaction):
            await interaction.response.send_message(
                "Chỉ admin mới dùng được nút này.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            await start_music()
            await interaction.followup.send(
                "🎵 Đã yêu cầu bật nhạc trong voice channel.",
                ephemeral=True,
            )
        except Exception as exc:
            log.exception("Test nhạc thất bại.")
            await interaction.followup.send(
                f"⚠️ Không bật được nhạc: {str(exc)[:250]}",
                ephemeral=True,
            )

    @discord.ui.button(
        label="Dừng nhạc",
        emoji="⏹️",
        style=discord.ButtonStyle.danger,
        custom_id="animeweather:stopmusic",
        row=2,
    )
    async def stop_button(self, interaction, button):
        if not await user_is_admin(interaction):
            await interaction.response.send_message(
                "Chỉ admin mới dùng được nút này.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        await stop_music()
        await interaction.followup.send(
            "⏹️ Đã dừng nhạc và rời voice channel.",
            ephemeral=True,
        )


# ==================== DAILY SCHEDULER ====================

async def check_morning_schedule():
    global last_morning_date

    now = discord.utils.utcnow().astimezone(KST)

    if now.hour == MORNING_HOUR and now.minute == MORNING_MINUTE:
        date_key = now.date().isoformat()

        if last_morning_date != date_key:
            last_morning_date = date_key
            log.info("Chạy tác vụ sáng lúc %s KST", now.isoformat())
            await run_morning_tasks()


@tasks.loop(seconds=20)
async def morning_scheduler():
    await check_morning_schedule()


@morning_scheduler.before_loop
async def before_morning_scheduler():
    await bot.wait_until_ready()


@bot.event
async def on_ready():
    global view_registered

    log.info("Bot online: %s", bot.user)

    if not view_registered:
        bot.add_view(WeatherPanel())
        view_registered = True

    await ensure_panel()

    if not morning_scheduler.is_running():
        morning_scheduler.start()


if not TOKEN:
    raise RuntimeError("Thiếu DISCORD_TOKEN trong Railway Variables.")

bot.run(TOKEN)
