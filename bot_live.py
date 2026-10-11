
import os
import re
import json
import aiohttp
import discord
from discord.ext import commands
from urllib.parse import urlparse

# ==========================================
# CẤU HÌNH BOT - PYCORD 2.6+
# ==========================================

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

TIMEOUT = aiohttp.ClientTimeout(total=15)


# ==========================================
# TIỆN ÍCH
# ==========================================

def clean_username(value: str) -> str:
    value = value.strip()

    if "tiktok.com/" in value.lower():
        parsed = urlparse(
            value if "://" in value else "https://" + value
        )
        match = re.match(r"/@([^/?#]+)", parsed.path)

        if match:
            value = match.group(1)
        else:
            return ""

    value = value.lstrip("@").strip()

    if not re.fullmatch(r"[A-Za-z0-9._]+", value):
        return ""

    return value


def valid_tiktok_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())

        host = (parsed.hostname or "").lower()

        return (
            parsed.scheme in ("https", "http")
            and (
                host == "tiktok.com"
                or host.endswith(".tiktok.com")
            )
        )
    except ValueError:
        return False


def format_number(value):
    if isinstance(value, (int, float)):
        return f"{int(value):,}"
    return "Không lấy được"


def add_checker(embed, ctx):
    embed.set_footer(
        text=f"Người check: {ctx.author.display_name}",
        icon_url=ctx.author.display_avatar.url,
    )


# ==========================================
# LẤY THÔNG TIN HỒ SƠ TIKTOK
# ==========================================

def extract_profile(html):
    script_patterns = [
        r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"'
        r'[^>]*>(.*?)</script>',
        r'<script[^>]*id="SIGI_STATE"'
        r'[^>]*>(.*?)</script>',
    ]

    for pattern in script_patterns:
        match = re.search(pattern, html, re.S)

        if not match:
            continue

        try:
            root = json.loads(match.group(1))
        except (ValueError, TypeError):
            continue

        candidates = []

        def walk(obj):
            if isinstance(obj, dict):
                user = obj.get("user")
                stats = obj.get("stats")

                if isinstance(user, dict) and isinstance(stats, dict):
                    candidates.append((user, stats))

                for value in obj.values():
                    walk(value)

            elif isinstance(obj, list):
                for value in obj:
                    walk(value)

        walk(root)

        for user, stats in candidates:
            avatar = (
                user.get("avatarLarger")
                or user.get("avatarMedium")
                or user.get("avatarThumb")
                or ""
            )

            return {
                "nickname": user.get("nickname") or "",
                "avatar": avatar,
                "followers": stats.get("followerCount"),
                "likes": stats.get("heartCount"),
                "verified": user.get("verified", False),
            }

    return None


async def fetch_profile(session, username):
    url = f"https://www.tiktok.com/@{username}"

    try:
        async with session.get(
            url,
            allow_redirects=True,
        ) as response:

            if response.status != 200:
                return None, (
                    f"TikTok trả về HTTP {response.status}"
                )

            html = await response.text()
            data = extract_profile(html)

            if data is None:
                return None, (
                    "Không đọc được dữ liệu hồ sơ. "
                    "TikTok có thể đã thay đổi trang hoặc "
                    "chặn yêu cầu từ Railway."
                )

            return data, None

    except (aiohttp.ClientError, TimeoutError) as error:
        return None, f"Lỗi kết nối: {type(error).__name__}"


# ==========================================
# BOT ONLINE
# ==========================================

@bot.event
async def on_ready():
    print(f"Bot TikTok online: {bot.user}")

    try:
        await bot.sync_commands()
        print("Đã đồng bộ slash commands.")
    except Exception as error:
        print(f"Lỗi đồng bộ lệnh: {error}")


# ==========================================
# /checkacc
# ==========================================

@bot.slash_command(
    name="checkacc",
    description="Kiểm tra hồ sơ TikTok, avatar, follower và tổng tim",
)
async def check_acc(
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
            "❌ Username hoặc link TikTok không hợp lệ.",
            ephemeral=True,
        )
        return

    profile_url = f"https://www.tiktok.com/@{name}"

    try:
        async with aiohttp.ClientSession(
            headers=HEADERS,
            timeout=TIMEOUT,
        ) as session:

            data, error = await fetch_profile(session, name)

        if data is None:
            embed = discord.Embed(
                title="⚠️ KHÔNG XÁC ĐỊNH ĐƯỢC TÀI KHOẢN",
                description=(
                    f"Không lấy được dữ liệu của `@{name}`.\n"
                    f"{error}\n\n"
                    "Lỗi truy cập không có nghĩa là tài khoản "
                    "đã bị khóa hoặc không tồn tại."
                ),
                color=discord.Color.orange(),
            )
            embed.add_field(
                name="🔗 Hồ sơ",
                value=f"[Mở TikTok]({profile_url})",
                inline=False,
            )
            add_checker(embed, ctx)
            await ctx.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title="📱 THÔNG TIN TÀI KHOẢN TIKTOK",
            description=f"**@{name}**",
            url=profile_url,
            color=discord.Color.green(),
        )

        embed.add_field(
            name="👤 Tên hiển thị",
            value=data["nickname"] or "Không lấy được",
            inline=False,
        )
        embed.add_field(
            name="👥 Followers",
            value=format_number(data["followers"]),
            inline=True,
        )
        embed.add_field(
            name="❤️ Tổng tim tài khoản",
            value=format_number(data["likes"]),
            inline=True,
        )
        embed.add_field(
            name="☑️ Tài khoản xác minh",
            value="Có" if data["verified"] else "Không",
            inline=True,
        )
        embed.add_field(
            name="🔗 Hồ sơ TikTok",
            value=f"[Nhấn để xem]({profile_url})",
            inline=False,
        )

        if data["avatar"]:
            embed.set_thumbnail(url=data["avatar"])

        add_checker(embed, ctx)
        await ctx.followup.send(embed=embed)

    except Exception as error:
        print(f"Lỗi /checkacc: {error}")
        await ctx.followup.send(
            "⚠️ Có lỗi khi kiểm tra tài khoản. "
            "Hãy thử lại sau.",
            ephemeral=True,
        )


# ==========================================
# /checklive
# ==========================================

@bot.slash_command(
    name="checklive",
    description="Kiểm tra link live và hiển thị avatar TikTok",
)
async def check_live(
    ctx: discord.ApplicationContext,
    link_live: discord.Option(
        str,
        description="Dán link livestream TikTok",
    ),
):
    await ctx.defer()

    link = link_live.strip()

    if not link.startswith(("https://", "http://")):
        link = "https://" + link

    if not valid_tiktok_url(link):
        await ctx.followup.send(
            "❌ Hãy nhập link thuộc tên miền TikTok hợp lệ.",
            ephemeral=True,
        )
        return

    try:
        async with aiohttp.ClientSession(
            headers=HEADERS,
            timeout=TIMEOUT,
        ) as session:

            # Mở link, cho phép chuyển hướng link rút gọn.
            async with session.get(
                link,
                allow_redirects=True,
            ) as response:
                real_link = str(response.url)
                status = response.status
                html = await response.text()

            # Xác định username từ URL sau chuyển hướng.
            match = re.search(
                r"tiktok\.com/@([^/?#]+)",
                real_link,
                re.I,
            )

            name = clean_username(match.group(1)) if match else ""

            data = None
            profile_error = None

            if name:
                data, profile_error = await fetch_profile(
                    session, name
                )

        # HTML có room_id không đủ chứng minh live đang phát.
        # Không tự kết luận live sống/chết khi chưa có API live.
        embed = discord.Embed(
            title="🔎 KIỂM TRA LIVESTREAM TIKTOK",
            description=(
                "Đã truy cập trang TikTok, nhưng chưa có nguồn "
                "dữ liệu live đáng tin cậy để xác nhận phòng "
                "đang phát hay đã kết thúc."
            ),
            url=real_link,
            color=discord.Color.orange(),
        )

        embed.add_field(
            name="🌐 HTTP",
            value=str(status),
            inline=True,
        )

        embed.add_field(
            name="🔴 Trạng thái live",
            value="Chưa xác minh được",
            inline=True,
        )

        embed.add_field(
            name="🔗 Link livestream",
            value=f"[Mở TikTok]({real_link})",
            inline=False,
        )

        if data:
            embed.add_field(
                name="👤 Tài khoản",
                value=f"@{name}",
                inline=False,
            )
            embed.add_field(
                name="👥 Followers",
                value=format_number(data["followers"]),
                inline=True,
            )
            embed.add_field(
                name="❤️ Tổng tim tài khoản",
                value=format_number(data["likes"]),
                inline=True,
            )

            if data["avatar"]:
                embed.set_thumbnail(url=data["avatar"])

        elif name:
            embed.add_field(
                name="ℹ️ Thông tin hồ sơ",
                value=profile_error or "Không lấy được dữ liệu.",
                inline=False,
            )

        add_checker(embed, ctx)
        await ctx.followup.send(embed=embed)

    except Exception as error:
        print(f"Lỗi /checklive: {error}")
        await ctx.followup.send(
            "⚠️ Không truy cập được trang live. "
            "Hãy kiểm tra link hoặc thử lại sau.",
            ephemeral=True,
        )


# ==========================================
# CHẠY BOT TRÊN RAILWAY
# ==========================================

token = os.getenv("DISCORD_TOKEN")

if not token:
    raise RuntimeError(
        "Thiếu biến môi trường DISCORD_TOKEN trong Railway."
    )

bot.run(token)
