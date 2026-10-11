import discord
from discord.ext import commands
import aiohttp
import re

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

# Dùng User-Agent giả lập trình duyệt Safari trên iPhone để TikTok trả về bản web mobile dễ đọc hơn
HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
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
# LỆNH /checkacc: Check Acc Sống/Die chính xác kèm Avatar & Người check
# -------------------------------------------------------------------------
@bot.slash_command(name="checkacc", description="Check trạng thái tài khoản TikTok (Sống/Die) kèm Avatar & Người check")
async def check_acc(
    ctx: discord.ApplicationContext,
    username: discord.Option(str, description="Nhập @username hoặc link profile TikTok")
):
    await ctx.defer(ephemeral=False)

    clean_user = username.replace("https://www.tiktok.com/@", "").replace("@", "").strip().split("/")[0]
    profile_url = f"https://www.tiktok.com/@{clean_user}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(profile_url, headers=HEADERS, timeout=10) as resp:
                html = await resp.text()

                # Nếu TikTok trả về lỗi 404 hoặc thông báo không tìm thấy user
                if resp.status == 404 or "Couldn't find this account" in html or "This account was banned" in html:
                    embed = discord.Embed(
                        title="❌ TÀI KHOẢN ĐÃ DIE / BỊ BAN",
                        description=f"Tài khoản `@{clean_user}` không tồn tại hoặc đã bị khóa vĩnh viễn.",
                        color=discord.Color.red()
                    )
                else:
                    # Lấy Avatar chuẩn từ thẻ OpenGraph của TikTok
                    avatar_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                    avatar_url = avatar_match.group(1) if avatar_match else ""

                    embed = discord.Embed(
                        title="✅ TÀI KHOẢN HOẠT ĐỘNG (SỐNG)",
                        description=f"Tài khoản `@{clean_user}` hoàn toàn bình thường và đang hoạt động!",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="🔗 Profile", value=f"[Trang cá nhân TikTok]({profile_url})", inline=False)
                    
                    if avatar_url:
                        embed.set_thumbnail(url=avatar_url) # Hiển thị Avatar tài khoản TikTok

                # Hiển thị Avatar & Tên của người gõ lệnh ở Footer
                user_avatar = ctx.author.display_avatar.url if ctx.author.display_avatar else ctx.author.default_avatar.url
                embed.set_footer(text=f"Yêu cầu bởi {ctx.author.name}", icon_url=user_avatar)

                await ctx.followup.send(embed=embed)
    except Exception as e:
        await ctx.followup.send(f"⚠️ Lỗi kết nối tới TikTok: `{e}`", ephemeral=True)

# -------------------------------------------------------------------------
# LỆNH /checklive: Check Live Sống/Die + Ảnh Live + Người check
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
