
import os
import re
import json
import aiohttp
import discord
from discord.ext import commands
from urllib.parse import urlparse

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en-US,en;q=0.8",
}

TIMEOUT = aiohttp.ClientTimeout(total=15)


def clean_username(value):
    value = value.strip()

    if "tiktok.com/" in value.lower():
        parsed = urlparse(
            value if "://" in value else "https://" + value
        )
        match = re.search(r"/@([^/?#]+)", parsed.path)
        if match:
            value = match.group(1)
        else:
            return ""

    value = value.lstrip("@").strip()

    if not re.fullmatch(r"[A-Za-z0-9._]+", value):
        return ""

    return value


def number_text(value):
    if isinstance(value, (int, float)):
        return f"{int(value):,}"
    return "Không lấy được"


def checker(embed, ctx):
    embed.set_footer(
        text=f"Người check: {ctx.author.display_name}",
        icon_url=ctx.author.display_avatar.url,
    )


def extract_profile(html):
    patterns = [
        r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"'
        r'[^>]*>(.*?)</script>',
        r'<script[^>]*id="SIGI_STATE"[^>]*>(.*?)</script>',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.S)
        if not match:
            continue

        try:
            root = json.loads(match.group(1))
        except (ValueError, TypeError):
            continue

        users = []

        def walk(obj):
            if isinstance(obj, dict):
                user = obj.get("user")
                stats = obj.get("stats")

                if isinstance(user, dict) and isinstance(stats, dict):
                    users.append((user, stats))

                for value in obj.values():
                    walk(value)

            elif isinstance(obj, list):
                for value in obj:
                    walk(value)

        walk(root)

        if users:
            user, stats = users[0]
            return {
                "nickname": user.get("nickname", ""),
                "avatar": (
                    user.get("avatarLarger")
                    or user.get("avatarMedium")
                    or user.get("avatarThumb")
                    or ""
                ),
                "followers": stats.get("followerCount"),
                "likes": stats.get("heartCount"),
            }

    return None


async def get_profile(session, username):
    url = f"https://www.tiktok.com/@{username}"

    try:
        async with session.get(url, allow_redirects=True) as response:
            if response.status != 200:
                return None

            html = await response.text()
            return extract_profile(html)

    except (aiohttp.ClientError, TimeoutError):
        return None


@bot.event
async def on_ready():
    print(f"Bot online: {bot.user}", flush=True)

    try:
        await bot.sync_commands()
        print("Slash commands synced.", flush=True)
    except Exception as exc:
        print(f"Sync error: {exc}", flush=True)


# ==========================================
# /checkacc
# ==========================================

@bot.slash_command(
    name="checkacc",
    description="Kiểm tra tài khoản TikTok",
)
async def checkacc(
    ctx: discord.ApplicationContext,
    username: discord.Option(
        str,
        description="Username hoặc link hồ sơ TikTok",
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

    async with aiohttp.ClientSession(
        headers=HEADERS,
        timeout=TIMEOUT,
    ) as session:
        data = await get_profile(session, name)

    if not data:
        embed = discord.Embed(
            title="⚠️ CHƯA XÁC MINH ĐƯỢC",
            description=(
                f"Không lấy được dữ liệu @{name}.\n"
                "Không thể kết luận tài khoản DIE vì TikTok "
                "có thể chặn Railway hoặc thay đổi trang."
            ),
            color=discord.Color.orange(),
        )
        embed.add_field(
            name="Hồ sơ",
            value=f"[Mở TikTok]({profile_url})",
            inline=False,
        )
        checker(embed, ctx)
        await ctx.followup.send(embed=embed)
        return

    embed = discord.Embed(
        title="🟢 TÀI KHOẢN TÌM THẤY",
        description=f"**@{name}**",
        url=profile_url,
        color=discord.Color.green(),
    )

    embed.add_field(
        name="Tên hiển thị",
        value=data["nickname"] or "Không có dữ liệu",
        inline=False,
    )
    embed.add_field(
        name="👥 Follower",
        value=number_text(data["followers"]),
        inline=True,
    )
    embed.add_field(
        name="❤️ Tổng tim",
        value=number_text(data["likes"]),
        inline=True,
    )

    if data["avatar"]:
        embed.set_thumbnail(url=data["avatar"])

    checker(embed, ctx)
    await ctx.followup.send(embed=embed)


# ==========================================
# /checklive
# ==========================================

@bot.slash_command(
    name="checklive",
    description="Kiểm tra link livestream TikTok",
)
async def checklive(
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

    try:
        parsed = urlparse(link)
        host = (parsed.hostname or "").lower()

        if not (
            host == "tiktok.com"
            or host.endswith(".tiktok.com")
        ):
            await ctx.followup.send(
                "❌ Link không thuộc TikTok.",
                ephemeral=True,
            )
            return

        async with aiohttp.ClientSession(
            headers=HEADERS,
            timeout=TIMEOUT,
        ) as session:
            async with session.get(
                link,
                allow_redirects=True,
            ) as response:
                real_link = str(response.url)
                http_status = response.status

            match = re.search(
                r"tiktok\.com/@([^/?#]+)",
                real_link,
                re.I,
            )

            name = clean_username(match.group(1)) if match else ""
            data = await get_profile(session, name) if name else None

        embed = discord.Embed(
            title="🔎 KẾT QUẢ KIỂM TRA LIVE",
            description=(
                "Chưa xác minh được trạng thái phát trực tiếp. "
                "HTTP thành công không đồng nghĩa live đang chạy."
            ),
            url=real_link,
            color=discord.Color.orange(),
        )

        embed.add_field(
            name="Trạng thái",
            value="⚠️ Chưa xác minh",
            inline=True,
        )
        embed.add_field(
            name="HTTP",
            value=str(http_status),
            inline=True,
        )
        embed.add_field(
            name="Link live",
            value=f"[Mở livestream]({real_link})",
            inline=False,
        )

        if name:
            embed.add_field(
                name="Tài khoản",
                value=f"@{name}",
                inline=True,
            )

        if data and data["avatar"]:
            embed.set_thumbnail(url=data["avatar"])

        checker(embed, ctx)
        await ctx.followup.send(embed=embed)

    except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
        print(f"checklive error: {exc}", flush=True)
        await ctx.followup.send(
            "⚠️ Không truy cập được link TikTok.",
            ephemeral=True,
        )


token = os.getenv("DISCORD_TOKEN")

if not token:
    raise RuntimeError("Railway thiếu biến DISCORD_TOKEN.")

bot.run(token)
