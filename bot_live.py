
import os
import re
import json
import asyncio
import aiohttp
import discord

from urllib.parse import urlparse
from discord.ext import commands
from TikTokLive import TikTokLiveClient


# ================= CONFIG =================

TOKEN_NAME = "TOKEN_BOT_1"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
}

TIMEOUT = aiohttp.ClientTimeout(total=20)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)


# ================= HELPERS =================

def clean_username(value):
    value = value.strip()

    if "://" not in value and "tiktok.com" in value.lower():
        value = "https://" + value

    if value.startswith(("https://", "http://")):
        parsed = urlparse(value)

        if not parsed.hostname or not (
            parsed.hostname.lower() == "tiktok.com"
            or parsed.hostname.lower().endswith(".tiktok.com")
        ):
            return ""

        match = re.search(r"/@([^/?#]+)", parsed.path)
        if not match:
            return ""

        value = match.group(1)

    value = value.lstrip("@").strip()

    if not re.fullmatch(r"[A-Za-z0-9._]+", value):
        return ""

    return value


def fmt_number(value):
    if value is None:
        return "Chưa lấy được"

    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return "Chưa lấy được"


def add_requester(embed, ctx):
    embed.set_footer(
        text=f"Người kiểm tra: {ctx.author.display_name}",
        icon_url=ctx.author.display_avatar.url,
    )


# ================= PROFILE PARSER =================

def extract_profile(html):
    patterns = [
        r'<script[^>]*id=["\']__UNIVERSAL_DATA_FOR_REHYDRATION__["\'][^>]*>(.*?)</script>',
        r'<script[^>]*id=["\']SIGI_STATE["\'][^>]*>(.*?)</script>',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.S | re.I)

        if not match:
            continue

        try:
            root = json.loads(match.group(1))
        except (ValueError, TypeError):
            continue

        candidates = []

        def walk(obj):
            if isinstance(obj, dict):
                info = obj.get("userInfo")

                if isinstance(info, dict):
                    user = info.get("user")
                    stats = info.get("stats") or info.get("statsV2") or {}

                    if isinstance(user, dict):
                        candidates.append((user, stats))

                for value in obj.values():
                    walk(value)

            elif isinstance(obj, list):
                for value in obj:
                    walk(value)

        walk(root)

        module = root.get("UserModule", {})
        users = module.get("users", {})
        all_stats = module.get("stats", {})

        if isinstance(users, dict):
            for uid, user in users.items():
                if isinstance(user, dict):
                    candidates.append((user, all_stats.get(uid, {})))

        for user, stats in candidates:
            if not isinstance(user, dict):
                continue

            if not isinstance(stats, dict):
                stats = {}

            username = user.get("uniqueId", "")

            avatar = (
                user.get("avatarLarger")
                or user.get("avatarMedium")
                or user.get("avatarThumb")
                or ""
            )

            if isinstance(avatar, list):
                avatar = avatar[0] if avatar else ""

            if not isinstance(avatar, str):
                avatar = ""

            if not username and not avatar:
                continue

            return {
                "username": username,
                "nickname": user.get("nickname") or username or "TikTok user",
                "avatar": avatar,
                "followers": stats.get("followerCount"),
                "likes": stats.get(
                    "heartCount",
                    stats.get("heart", stats.get("likesCount")),
                ),
                "verified": user.get("verified", False),
            }

    return None


# ================= FETCH PROFILE =================

async def fetch_profile(session, username):
    profile_url = f"https://www.tiktok.com/@{username}"

    result = {
        "username": username,
        "nickname": username,
        "avatar": "",
        "followers": None,
        "likes": None,
        "verified": False,
    }

    try:
        async with session.get(
            profile_url,
            allow_redirects=True,
        ) as response:
            if response.status == 200:
                html = await response.text(errors="ignore")
                data = extract_profile(html)

                if data:
                    result.update(data)
                    return "alive", result

            elif response.status in (403, 429, 500, 502, 503):
                return "unknown", None

    except (aiohttp.ClientError, asyncio.TimeoutError):
        return "unknown", None

    try:
        async with session.get(
            "https://www.tiktok.com/oembed",
            params={"url": profile_url},
            allow_redirects=True,
        ) as response:
            if response.status == 200:
                data = await response.json(content_type=None)

                result["nickname"] = (
                    data.get("author_name") or result["nickname"]
                )
                result["avatar"] = (
                    data.get("thumbnail_url") or result["avatar"]
                )

                if result["avatar"] or result["nickname"] != username:
                    return "alive", result

    except (
        aiohttp.ClientError,
        asyncio.TimeoutError,
        ValueError,
    ):
        pass

    return "unknown", None


# ================= RESOLVE LIVE LINK =================

async def resolve_live_link(session, link):
    link = link.strip()

    if not link.startswith(("https://", "http://")):
        link = "https://" + link

    parsed = urlparse(link)
    host = (parsed.hostname or "").lower()

    if not (
        host == "tiktok.com"
        or host.endswith(".tiktok.com")
    ):
        return None, link

    final_url = link

    try:
        async with session.get(
            link,
            allow_redirects=True,
        ) as response:
            final_url = str(response.url)
    except (aiohttp.ClientError, asyncio.TimeoutError):
        pass

    match = re.search(
        r"tiktok\.com/@([^/?#]+)",
        final_url,
        re.I,
    )

    if not match:
        match = re.search(
            r"tiktok\.com/@([^/?#]+)",
            link,
            re.I,
        )

    if not match:
        return None, final_url

    return clean_username(match.group(1)) or None, final_url


# ================= CHECK LIVE =================

async def check_tiktok_live(username):
    client = TikTokLiveClient(unique_id=username)

    try:
        result = await asyncio.wait_for(
            client.is_live(),
            timeout=20,
        )

        if result is True:
            return True

        if result is False:
            return False

        return None

    except Exception as exc:
        print(
            f"LIVE CHECK ERROR: {type(exc).__name__}: {exc}",
            flush=True,
        )
        return None


# ================= BOT READY =================

@bot.event
async def on_ready():
    print(f"Bot online: {bot.user}", flush=True)

    try:
        await bot.sync_commands()
        print("Slash commands synced.", flush=True)
    except Exception as exc:
        print(f"COMMAND SYNC ERROR: {exc}", flush=True)


# ================= /checkacc =================

@bot.slash_command(
    name="checkacc",
    description="Kiểm tra tài khoản TikTok",
)
async def checkacc(
    ctx: discord.ApplicationContext,
    username: discord.Option(
        str,
        description="Nhập username hoặc link hồ sơ TikTok",
    ),
):
    await ctx.defer()

    name = clean_username(username)

    if not name:
        await ctx.followup.send(
            "❌ Username không hợp lệ. Hãy nhập @username "
            "hoặc link hồ sơ TikTok.",
            ephemeral=True,
        )
        return

    async with aiohttp.ClientSession(
        headers=HEADERS,
        timeout=TIMEOUT,
    ) as session:
        status, data = await fetch_profile(session, name)

    profile_url = f"https://www.tiktok.com/@{name}"

    if status == "alive" and data:
        embed = discord.Embed(
            title="🟢 TÀI KHOẢN TÌM THẤY",
            description=f"**@{name}**",
            url=profile_url,
            color=discord.Color.green(),
        )

        embed.add_field(
            name="👤 Tên hiển thị",
            value=data["nickname"],
            inline=False,
        )
        embed.add_field(
            name="👥 Followers",
            value=fmt_number(data["followers"]),
            inline=True,
        )
        embed.add_field(
            name="❤️ Tổng tim",
            value=fmt_number(data["likes"]),
            inline=True,
        )
        embed.add_field(
            name="☑️ Xác minh",
            value="Có" if data["verified"] else "Không rõ / không",
            inline=True,
        )

        if data["avatar"]:
            embed.set_thumbnail(url=data["avatar"])

    else:
        embed = discord.Embed(
            title="⚠️ KHÔNG XÁC MINH ĐƯỢC",
            description=(
                f"Không lấy được dữ liệu đáng tin cậy của **@{name}**.\n"
                "Không thể kết luận tài khoản DIE chỉ từ kết quả này."
            ),
            url=profile_url,
            color=discord.Color.orange(),
        )

    embed.add_field(
        name="🔗 Hồ sơ",
        value=f"[Mở TikTok]({profile_url})",
        inline=False,
    )

    add_requester(embed, ctx)
    await ctx.followup.send(embed=embed)


# ================= /checklive =================

@bot.slash_command(
    name="checklive",
    description="Kiểm tra livestream TikTok",
)
async def checklive(
    ctx: discord.ApplicationContext,
    link_live: discord.Option(
        str,
        description="Dán link livestream TikTok",
    ),
):
    await ctx.defer()

    async with aiohttp.ClientSession(
        headers=HEADERS,
        timeout=TIMEOUT,
    ) as session:
        username, final_url = await resolve_live_link(
            session,
            link_live,
        )

        if not username:
            embed = discord.Embed(
                title="⚠️ KHÔNG ĐỌC ĐƯỢC LINK",
                description=(
                    "Không tìm được username từ link. "
                    "Thử link dạng "
                    "`https://www.tiktok.com/@username/live`."
                ),
                color=discord.Color.orange(),
            )

            add_requester(embed, ctx)
            await ctx.followup.send(embed=embed)
            return

        _, profile = await fetch_profile(session, username)

    live_status = await check_tiktok_live(username)

    if live_status is True:
        embed = discord.Embed(
            title="🟢 ĐANG LIVE",
            description=f"Đã phát hiện **@{username}** đang live.",
            url=final_url,
            color=discord.Color.green(),
        )

    elif live_status is False:
        embed = discord.Embed(
            title="⚪ KHÔNG PHÁT HIỆN LIVE",
            description=(
                f"Thư viện không phát hiện phiên live của **@{username}**. "
                "Kết quả vẫn có thể sai nếu TikTok chặn dữ liệu."
            ),
            url=final_url,
            color=discord.Color.light_grey(),
        )

    else:
        embed = discord.Embed(
            title="⚠️ KHÔNG XÁC MINH ĐƯỢC LIVE",
            description=(
                f"Không lấy được trạng thái live của **@{username}**. "
                "Không thể kết luận người đó đã tắt live."
            ),
            url=final_url,
            color=discord.Color.orange(),
        )

    if profile and profile.get("avatar"):
        embed.set_thumbnail(url=profile["avatar"])

    embed.add_field(
        name="👤 Tài khoản",
        value=f"@{username}",
        inline=False,
    )
    embed.add_field(
        name="🔗 Link livestream",
        value=f"[Mở TikTok]({final_url})",
        inline=False,
    )

    add_requester(embed, ctx)
    await ctx.followup.send(embed=embed)


# ================= START BOT 1 =================

token = os.getenv("TOKEN_BOT_1")

if not token:
    raise RuntimeError(
        "Railway Variables đang thiếu TOKEN_BOT_1."
    )

bot.run(token)
