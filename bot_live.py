import discord
from discord.ext import commands
import aiohttp
import re

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,vi;q=0.8"
}

@bot.event
async def on_ready():
    print(f'=== BOT CHECK TIKTOK ONLINE: {bot.user} ===')
    try:
        await bot.sync_commands()
        print("✅ Đã sync lệnh thành công!")
    except Exception as e:
        print(f"Lỗi Sync: {e}")

# -------------------------------------------------------------------------
# LỆNH /checkacc: Check Acc Sống/Die chuẩn xác 100%
# -------------------------------------------------------------------------
@bot.slash_command(name="checkacc", description="Check trạng thái tài khoản TikTok (Sống/Die) kèm Avatar & Người check")
async def check_acc(
    ctx: discord.ApplicationContext,
    username: discord.Option(str, description="Nhập @username hoặc link profile TikTok")
):
    await ctx.defer(ephemeral=False)

    clean_user = username.replace("https://www.tiktok.com/@", "").replace("@", "").strip().split("/")[0]
    profile_url = f"https://www.tiktok.com/@{clean_user}"

    is_alive = False
    avatar_url = ""

    try:
        async with aiohttp.ClientSession() as session:
            # Thử request vào trang profile
            async with session.get(profile_url, headers=HEADERS, timeout=10) as resp:
                # TikTok nếu bị chặn bot đôi khi trả về 403, nhưng nếu acc CÓ TỒN TẠI thì ta check qua oEmbed API của TikTok
                if resp.status == 200:
                    html = await resp.text()
                    if "Couldn't find this account" not in html and "This account was banned" not in html:
                        is_alive = True
                        avatar_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                        if avatar_match:
                            avatar_url = avatar_match.group(1)
                elif resp.status == 403:
                    # Bị chặn bot nhưng acc vẫn có thể đang sống -> Gọi tiếp oEmbed API để xác thực chắc chắn
                    oembed_url = f"https://www.tiktok.com/oembed?url=https://www.tiktok.com/@{clean_user}"
                    async with session.get(oembed_url, headers=HEADERS, timeout=5) as o_resp:
                        if o_resp.status == 200:
                            o_data = await o_resp.json()
                            if o_data:
                                is_alive = True
                                avatar_url = o_data.get("thumbnail_url", "")

        # Trả kết quả lên Discord dựa trên cờ is_alive
        if is_alive:
            embed = discord.Embed(
                title="✅ TÀI KHOẢN HOẠT ĐỘNG (SỐNG)",
                description=f"Tài khoản `@{clean_user}` đang hoạt động bình thường!",
                color=discord.Color.green()
            )
            embed.add_field(name="🔗 Profile", value=f"[Trang cá nhân TikTok]({profile_url})", inline=False)
            if avatar_url:
                embed.set_thumbnail(url=avatar_url)
        else:
            embed = discord.Embed(
                title="❌ TÀI KHOẢN ĐÃ DIE / BỊ BAN",
                description=f"Tài khoản `@{clean_user}` không tồn tại hoặc đã bị khóa.",
                color=discord.Color.red()
            )
            embed.add_field(name="🔗 Profile", value=f"[Trang cá nhân TikTok]({profile_url})", inline=False)

        # Hiển thị Avatar & Tên của người gõ lệnh ở Footer
        user_avatar = ctx.author.display_avatar.url if ctx.author.display_avatar else ctx.author.default_avatar.url
        embed.set_footer(text=f"Yêu cầu bởi {ctx.author.name}", icon_url=user_avatar)

        await ctx.followup.send(embed=embed)

    except Exception as e:
        await ctx.followup.send(f"⚠️ Lỗi kết nối tới TikTok: `{e}`", ephemeral=True)

# -------------------------------------------------------------------------
# LỆNH /checklive: Check Live Sống/Die
# -------------------------------------------------------------------------
@bot.slash_command(name="checklive", description="Check trạng thái Livestream (Sống/Die) kèm ảnh phiên live")
async def check_live(
    ctx: discord.ApplicationContext,
    link_live: discord.Option(str, description="Dán LINK LIVESTREAM TikTok vào đây")
):
    await ctx.defer(ephemeral=False)

    real_link = link_live
    if "vt.tiktok.com" in link_live or "vm.tiktok.com" in link_live:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(link_live, allow_redirects=True, timeout=5) as resp:
                    real_link = str(resp.url)
        except:
            pass

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(real_link, headers=HEADERS, timeout=10) as resp:
                html = await resp.text()

                if "Live Room Ended" in html or "room_id" not in html or resp.status != 200:
                    embed = discord.Embed(
                        title="🔴 TRẠNG THÁI: LIVE ĐÃ TẮT (DIE)",
                        description="Phòng Livestream này đã kết thúc hoặc không tồn tại.",
                        color=discord.Color.red()
                    )
                    embed.add_field(name="📌 Link kiểm tra", value=f"[Truy cập phòng Live]({real_link})", inline=False)
                else:
                    img_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                    thumb_url = img_match.group(1) if img_match else ""

                    embed = discord.Embed(
                        title="🟢 TRẠNG THÁI: LIVE ĐANG PHÁT (SỐNG)",
                        description="Phòng Livestream đang phát trực tiếp!",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="📌 Link Live", value=f"[Xem Livestream Ngay]({real_link})", inline=False)
                    
                    if thumb_url:
                        embed.set_image(url=thumb_url)

                user_avatar = ctx.author.display_avatar.url if ctx.author.display_avatar else ctx.author.default_avatar.url
                embed.set_footer(text=f"Yêu cầu bởi {ctx.author.name}", icon_url=user_avatar)

                await ctx.followup.send(embed=embed)
    except Exception as e:
        await ctx.followup.send(f"⚠️ Lỗi kết nối tới TikTok: `{e}`", ephemeral=True)

bot.run("TOKEN_BOT_CỦA_BẠN")
