import discord
from discord.ext import commands
import aiohttp
import re

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

# Headers giả lập trình duyệt thật để không bị TikTok chặn 403 / Forbidden
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://www.tiktok.com/",
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
# 1. LỆNH /checkacc: Check Acc + Avatar + Follow + Tim + Avatar người check
# -------------------------------------------------------------------------
@bot.slash_command(name="checkacc", description="Check trạng thái tài khoản TikTok (Sống/Die) kèm thông số chi tiết")
async def check_acc(
    ctx: discord.ApplicationContext,
    username: discord.Option(str, description="Nhập @username hoặc link profile TikTok")
):
    await ctx.defer(ephemeral=False)

    # Làm sạch định dạng username
    clean_user = username.replace("https://www.tiktok.com/@", "").replace("@", "").strip().split("/")[0]
    profile_url = f"https://www.tiktok.com/@{clean_user}"
    web_url = f"https://www.tiktok.com/@{clean_user}"

    try:
        async with aiohttp.ClientSession() as session:
            # Cào trực tiếp trang profile web của TikTok
            async with session.get(web_url, headers=HEADERS, timeout=10) as resp:
                html = await resp.text()

                # Kiểm tra xem tài khoản có tồn tại hay bị ban không
                if resp.status == 404 or "Couldn't find this account" in html or "This account was banned" in html:
                    embed = discord.Embed(
                        title="❌ TÀI KHOẢN ĐÃ DIE / BỊ BAN",
                        description=f"Tài khoản `@{clean_user}` không tồn tại hoặc đã bị TikTok khóa vĩnh viễn.",
                        color=discord.Color.red()
                    )
                else:
                    # Trích xuất dữ liệu từ OpenGraph tags và JSON nhúng trong HTML của TikTok
                    avatar_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                    nickname_match = re.search(r'<meta property="og:title" content="([^"]+)"', html)
                    
                    # Cào số liệu Follower và Heart (Tim) từ dữ liệu json-ld hoặc kho dữ liệu trang
                    follower_match = re.search(r'"followerCount":(\d+)', html)
                    heart_match = re.search(r'"heartCount":(\d+)', html)
                    video_match = re.search(r'"videoCount":(\d+)', html)

                    avatar_url = avatar_match.group(1) if avatar_match else ""
                    nickname = nickname_match.group(1).split("(@")[0].strip() if nickname_match else clean_user
                    
                    followers = int(follower_match.group(1)) if follower_match else 0
                    likes = int(heart_match.group(1)) if heart_match else 0
                    videos = int(video_match.group(1)) if video_match else 0

                    embed = discord.Embed(
                        title=f"✅ TÀI KHOẢN HOẠT ĐỘNG (SỐNG)",
                        description=f"**Tên kênh:** {nickname}\n**ID:** `@{clean_user}`",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="👥 Follower", value=f"`{followers:,}`", inline=True)
                    embed.add_field(name="❤️ Tổng Tim", value=f"`{likes:,}`", inline=True)
                    embed.add_field(name="🎬 Video", value=f"`{videos:,}`", inline=True)
                    embed.add_field(name="🔗 Profile", value=f"[Trang cá nhân TikTok]({profile_url})", inline=False)
                    
                    if avatar_url:
                        embed.set_thumbnail(url=avatar_url) # Ảnh đại diện tài khoản TikTok

                # Hiển thị Avatar & Tên của người gõ lệnh (User Check) ở Footer
                user_avatar = ctx.author.display_avatar.url if ctx.author.display_avatar else ctx.author.default_avatar.url
                embed.set_footer(text=f"Yêu cầu bởi {ctx.author.name}", icon_url=user_avatar)

                await ctx.followup.send(embed=embed)
    except Exception as e:
        await ctx.followup.send(f"⚠️ Lỗi kết nối tới TikTok: `{e}`", ephemeral=True)

# -------------------------------------------------------------------------
# 2. LỆNH /checklive: Check Live + Mắt xem + Tim Live + Ảnh Live + Avatar người check
# -------------------------------------------------------------------------
@bot.slash_command(name="checklive", description="Check trạng thái Livestream (Sống/Die), mắt xem, thả tim và ảnh live")
async def check_live(
    ctx: discord.ApplicationContext,
    link_live: discord.Option(str, description="Dán LINK LIVERSTREAM TikTok vào đây (Không phải tên acc)")
):
    await ctx.defer(ephemeral=False)

    real_link = link_live
    # Giải mã link rút gọn vt.tiktok.com
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

                # Kiểm tra phòng live còn hoạt động hay không
                if "Live Room Ended" in html or "room_id" not in html or resp.status != 200:
                    embed = discord.Embed(
                        title="🔴 TRẠNG THÁI: LIVE ĐÃ TẮT (DIE)",
                        description="Phòng Livestream này đã kết thúc hoặc không tồn tại.",
                        color=discord.Color.red()
                    )
                    embed.add_field(name="📌 Link kiểm tra", value=f"[Truy cập phòng Live]({real_link})", inline=False)
                else:
                    # Trích xuất số mắt xem, số tim live và ảnh thumbnail phiên live
                    views_match = re.search(r'"user_count":(\d+)', html)
                    likes_match = re.search(r'"like_count":(\d+)', html)
                    img_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                    
                    views = int(views_match.group(1)) if views_match else 0
                    likes = int(likes_match.group(1)) if likes_match else 0
                    thumb_url = img_match.group(1) if img_match else ""

                    embed = discord.Embed(
                        title="🟢 TRẠNG THÁI: LIVE Đang PHÁT (SỐNG)",
                        description="Phòng Livestream đang phát trực tiếp!",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="👁️ Mắt xem hiện tại", value=f"`{views:,}` người", inline=True)
                    embed.add_field(name="💖 Tổng tim phiên live", value=f"`{likes:,}` tim", inline=True)
                    embed.add_field(name="📌 Link Live", value=f"[Xem Livestream Ngay]({real_link})", inline=False)
                    
                    if thumb_url:
                        embed.set_image(url=thumb_url) # Hiển thị ảnh đang live to đùng

                # Hiển thị Avatar & Tên của người gõ lệnh (User Check) ở Footer
                user_avatar = ctx.author.display_avatar.url if ctx.author.display_avatar else ctx.author.default_avatar.url
                embed.set_footer(text=f"Yêu cầu bởi {ctx.author.name}", icon_url=user_avatar)

                await ctx.followup.send(embed=embed)
    except Exception as e:
        await ctx.followup.send(f"⚠️ Lỗi kết nối tới TikTok: `{e}`", ephemeral=True)

bot.run("TOKEN_BOT_CỦA_BẠN")
