
import os
import re
import json
import asyncio
import aiohttp
import discord

from urllib.parse import urlparse
from discord.ext import commands
from TikTokLive import TikTokLiveClient

# =========================
# DISCORD BOT
# =========================

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
}

TIMEOUT = aiohttp.ClientTimeout(total=20)


# =========================
# TIỆN ÍCH
# =========================

def clean_username(value):
    value = value.strip()

    if "://" not in value and "tiktok.com" in value.lower():
        value = "https://" + value

    if value.startswith(("http://", "https://")):
        parsed = urlparse(value)
        match = re.search(r"/@([^/?#]+)", parsed.path)

        if not match:
            return ""

        value = match.group(1)

    value = value.strip().lstrip("@")

    if not re.fullmatch(r"[A-Za-z0-9._]+", value):
        return ""

    return value


def fmt_number(value):
    if value is None:
        return "Không có dữ liệu"

    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return "Không có dữ liệu"


def add_requester(embed, ctx):
    embed.set_footer(
        text=f"Người kiểm tra: {ctx.author.display_name}",
        icon_url=ctx.author.display_avatar.url,
    )


# =========================
# ĐỌC DỮ LIỆU HỒ SƠ TIKTOK
# =========================

def extract_profile(html):
    # TikTok đôi khi đổi cấu trúc dữ liệu.
    # Thử cả định dạng mới và định dạng cũ.
    script_patterns = [
        r'<script[^>]*id=["\']__UNIVERSAL_DATA_FOR_REHYDRATION__["\'][^>]*>(.*?)</script>',
        r'<script[^>]*id=["\']SIGI_STATE["\'][^>]*>(.*?)</script>',
    ]

    for pattern in script_patterns:
        match = re.search(pattern, html, re.S | re.I)

        if not match:
            continue

        try:
            root = json.loads(match.group(1))
        except (ValueError, TypeError):
            continue

        # Cấu trúc dữ liệu TikTok mới
        scope = root.get("__DEFAULT_SCOPE__", root)
        detail = scope.get("webapp.user-detail", {})
        user_info = detail.get("userInfo", {})

        user = user_info.get("user")
        stats = user_info.get("stats") or user_info.get("statsV2") or {}

        # Cấu trúc dữ liệu TikTok cũ
        if not isinstance(user, dict):
            module = root.get("UserModule", {})
            users = module.get("users", {})
            all_stats = module.get("stats", {})

            if users:
                uid = next(iter(users))
                user = users[uid]
                stats = all_stats.get(uid, {})

        if not isinstance(user, dict):
            continue

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

        if not isinstance(stats, dict):
            stats = {}

        # Chỉ coi là tài khoản tìm thấy nếu dữ liệu nhận dạng hợp lệ.
        unique_id = user.get("uniqueId", "")

        if not unique_id and not avatar:
            continue

        return {
            "username": unique_id,
            "nickname": user.get("nickname") or unique_id or "TikTok user",
            "avatar": avatar,
            "followers": stats.get("followerCount"),
            "likes": stats.get("heartCount", stats.get("heart")),
            "verified": user.get("verified", False),
        }

    return None


async def fetch_profile(username):
    url = f"https://www.tiktok.com/@{username}"

    try:
        async with aiohttp.ClientSession(
            headers=HEADERS,
            timeout=TIMEOUT,
        ) as session:
            async with session.get(
                url,
                allow_redirects=True,
            ) as response:
                html = await response.text(errors="ignore")

                if response.status in (403, 429, 500, 502, 503):
                    return "unknown", None

                # Chỉ báo DIE khi có dấu hiệu rõ ràng.
                lower_html = html.lower()

                not_found_markers = [
                    "couldn't find this account",
                    "could not find this account",
                    "this account was banned",
                    "account doesn't exist",
                    "account does not exist",
                ]

                if any(marker in lower_html for marker in not_found_markers):
                    return "dead", None

                data = extract_profile(html)

                if data:
                    return "alive", data

                # Trang trả về nhưng không có dữ liệu:
                # không được kết luận tài khoản DIE.
                return "unknown", None

    except (aiohttp.ClientError, asyncio.TimeoutError):
        return "unknown", None


# =========================
# KIỂM TRA TRẠNG THÁI LIVE
# =========================

async def check_tiktok_live(username):
    client = TikTokLiveClient(unique_id=username)

    try:
        result = await asyncio.wait_for(
            client.is_live(),
            timeout=15,
        )

        if isinstance(result, bool):
            return result

        return None

    except Exception as exc:
        print(f"TikTok LIVE check error: {type(exc).__name__}: {exc}")
        return None


async def resolve_live_link(link):
    if not link.startswith(("https://", "http://")):
        link = "https://" + link

    parsed = urlparse(link)
    host = (parsed.hostname or "").lower()

    if not (host == "tiktok.com" or host.endswith(".tiktok.com")):
        return None, None

    try:
        async with aiohttp.ClientSession(
            headers=HEADERS,
            timeout=TIMEOUT,
        ) as session:
            async with session.get(
                link,
                allow_redirects=True,
            ) as response:
                final_url = str(response.url)

        match = re.search(
            r"tiktok\.com/@([^/?#]+)",
            final_url,
            re.I,
        )

        if match:
            username = clean_username(match.group(1))
            return username or None, final_url

        # Link live có thể chưa chuyển hướng tới URL có @username.
        match = re.search(
            r"tiktok\.com/@([^/?#]+)",
            link,
            re.I,
        )

        if match:
            username = clean_username(match.group(1))
            return username or None, link

        return None, final_url

    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        return None, link


# =========================
# BOT READY
# =========================

@bot.event
async def on_ready():
    print(f"Bot online: {bot.user}", flush=True)

    try:
        await bot.sync_commands()
        print("Slash commands synced.", flush=True)
    except Exception as exc:
        print(f"Command sync error: {exc}", flush=True)


# =========================
# /checkacc
# =========================

@bot.slash_command(
    name="checkacc",
    description="Kiểm tra tài khoản TikTok",
)
async def checkacc(
    ctx: discord.ApplicationContext,
    username: discord.Option(
        str,
        description="Nhập @username hoặc link hồ sơ TikTok",
    ),
):
    await ctx.defer()

    name = clean_username(username)

    if not name:
        await ctx.followup.send(
            "❌ Link hoặc username không hợp lệ. Hãy nhập @username hoặc link hồ sơ.",
            ephemeral=True,
        )
        return

    status, data = await fetch_profile(name)
    profile_url = f"https://www.tiktok.com/@{name}"

    if status == "dead":
        embed = discord.Embed(
            title="🔴 TÀI KHOẢN DIE / KHÔNG TÌM THẤY",
            description=f"**@{name}**",
            url=profile_url,
            color=discord.Color.red(),
        )

    elif status == "unknown":
        embed = discord.Embed(
            title="⚠️ KHÔNG XÁC MINH ĐƯỢC",
            description=(
                f"Không lấy được dữ liệu của **@{name}**.\n"
                "TikTok có thể chặn máy chủ hoặc thay đổi dữ liệu. "
                "Kết quả này không có nghĩa là tài khoản DIE."
            ),
            url=profile_url,
            color=discord.Color.orange(),
        )

    else:
        embed = discord.Embed(
            title="🟢 TÀI KHOẢN TÌM THẤY",
            description=f"**@{data['username'] or name}**",
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
            value="Có" if data["verified"] else "Không",
            inline=True,
        )

        if data["avatar"]:
            embed.set_thumbnail(url=data["avatar"])

    embed.add_field(
        name="🔗 Hồ sơ",
        value=f"[Mở TikTok]({profile_url})",
        inline=False,
    )

    add_requester(embed, ctx)
    await ctx.followup.send(embed=embed)


# =========================
# /checklive
# =========================

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

    username, final_url = await resolve_live_link(link_live.strip())

    if not username:
        embed = discord.Embed(
            title="⚠️ KHÔNG ĐỌC ĐƯỢC LINK LIVE",
            description=(
                "Không tìm được username từ link. "
                "Hãy dùng link dạng `https://www.tiktok.com/@username/live`."
            ),
            color=discord.Color.orange(),
        )
        add_requester(embed, ctx)
        await ctx.followup.send(embed=embed)
        return

    # Lấy avatar hồ sơ riêng; không tự nhận đó là ảnh phòng live.
    profile_status, data = await fetch_profile(username)

    live_status = await check_tiktok_live(username)

    if live_status is True:
        embed = discord.Embed(
            title="🟢 ĐANG LIVE",
            description=f"**@{username}** đang phát trực tiếp.",
            url=final_url,
            color=discord.Color.green(),
        )

    elif live_status is False:
        embed = discord.Embed(
            title="🔴 HIỆN KHÔNG LIVE",
            description=f"Không phát hiện phiên live của **@{username}**.",
            url=f"https://www.tiktok.com/@{username}/live",
            color=discord.Color.red(),
        )

    else:
        embed = discord.Embed(
            title="⚠️ KHÔNG XÁC MINH ĐƯỢC LIVE",
            description=(
                f"Không xác định được trạng thái live của **@{username}**. "
                "Có thể TikTok chặn yêu cầu hoặc dịch vụ kiểm tra gặp lỗi."
            ),
            url=final_url,
            color=discord.Color.orange(),
        )

    if data and data.get("avatar"):
        embed.set_thumbnail(url=data["avatar"])

    if data:
        embed.add_field(
            name="👤 Tài khoản",
            value=data["nickname"] + f" (`@{username}`)",
            inline=False,
        )

    embed.add_field(
        name="🔗 Link",
        value=f"[Mở TikTok]({final_url})",
        inline=False,
    )

    add_requester(embed, ctx)
    await ctx.followup.send(embed=embed)


# =========================
# START
# =========================

token = os.getenv("DISCORD_TOKEN")

if not token:
    raise RuntimeError(
        "Thiếu DISCORD_TOKEN trong Railway Variables."
    )

bot.run(token)
