import discord
from discord.ext import commands
import aiohttp
import re

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f'=== BOT CHECK TIKTOK ONLINE: {bot.user} ===')
    try:
        await bot.sync_commands()
        print("✅ Đã sync lệnh thành công!")
    except Exception as e:
        print(f"Lỗi sync: {e}")

# -------------------------------------------------------------------------
# 1. LỆNH /checklive: Kiểm tra Live Sống/Die kèm ảnh phiên Live
# -------------------------------------------------------------------------
@bot.slash_command(name="checklive", description="Kiểm tra Livestream TikTok Sống hay Die kèm ảnh phiên live")
async def check_live(
    ctx: discord.ApplicationContext,
    link_live: discord.Option(str, description="Dán link live TikTok vào đây")
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

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(real_link, headers=headers, timeout=10) as resp:
                html = await resp.text()
                
                # Trích xuất ảnh bìa (thumbnail) của phòng live nếu có trong metadata trang web
                img_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                thumb_url = img_match.group(1) if img_match else "https://ibb.co/1M2R65v" # Ảnh mặc định nếu không lấy được

                if "Live Room Ended" in html or "room_id" not in html or resp.status != 200:
                    embed = discord.Embed(
                        title="🔴 TRẠNG THÁI: LIVE ĐÃ TẮT (DIE)",
                        description=f"Phòng Livestream này đã kết thúc hoặc không tồn tại.",
                        color=discord.Color.red()
                    )
                else:
                    embed = discord.Embed(
                        title="🟢 TRẠNG THÁI: LIVE ĐANG PHÁT (SỐNG)",
                        description=f"Phòng Livestream vẫn đang hoạt động bình thường!",
                        color=discord.Color.green()
                    )
                
                embed.add_field(name="📌 Link Live", value=f"[Truy cập ngay]({real_link})", inline=False)
                embed.set_image(url=thumb_url) # Hiển thị ảnh phiên live to đùng
                embed.set_footer(text=f"Yêu cầu bởi {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
                
                await ctx.followup.send(embed=embed)
    except Exception as e:
        await ctx.followup.send(f"⚠️ Lỗi khi check live: `{e}`", ephemeral=True)

# -------------------------------------------------------------------------
# 2. LỆNH /checkacc: Kiểm tra Acc TikTok Sống/Die kèm Avatar
# -------------------------------------------------------------------------
@bot.slash_command(name="checkacc", description="Kiểm tra tài khoản TikTok Sống hay Die kèm Avatar")
async def check_acc(
    ctx: discord.ApplicationContext,
    username: discord.Option(str, description="Nhập @username hoặc link profile TikTok")
):
    await ctx.defer(ephemeral=False)

    # Làm sạch username
    clean_user = username.replace("https://www.tiktok.com/@", "").replace("@", "").strip().split("/")[0]
    profile_url = f"https://www.tiktok.com/@{clean_user}"

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(profile_url, headers=headers, timeout=10) as resp:
                html = await resp.text()
                
                # Trích xuất ảnh Avatar của tài khoản TikTok từ trang profile
                avatar_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                avatar_url = avatar_match.group(1) if avatar_match else "https://ibb.co/1M2R65v"

                if resp.status == 404 or "Couldn't find this account" in html or "This account was banned" in html:
                    embed = discord.Embed(
                        title="❌ TÀI KHOẢN ĐÃ DIE / BỊ BAN",
                        description=f"Tài khoản `@{clean_user}` không tồn tại hoặc đã bị TikTok khóa vĩnh viễn.",
                        color=discord.Color.red()
                    )
                else:
                    embed = discord.Embed(
                        title="✅ TÀI KHOẢN HOẠT ĐỘNG (SỐNG)",
                        description=f"Tài khoản `@{clean_user}` hoàn toàn bình thường, không bị khóa.",
                        color=discord.Color.green()
                    )
                
                embed.add_field(name="🔗 Link Profile", value=f"[Truy cập trang cá nhân]({profile_url})", inline=False)
                embed.set_thumbnail(url=avatar_url) # Hiển thị avatar góc phải embed
                embed.set_footer(text=f"Yêu cầu bởi {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
                
                await ctx.followup.send(embed=embed)
    except Exception as e:
        await ctx.followup.send(f"⚠️ Lỗi khi check tài khoản: `{e}`", ephemeral=True)

bot.run("TOKEN_BOT_CỦA_BẠN")
