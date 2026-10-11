import discord
from discord.ext import commands
import aiohttp
import re

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

# Headers giả lập trình duyệt thật để bypass tường lửa TikTok
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://www.tiktok.com/",
    "Accept": "application/json, text/plain, */*"
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
# LỆNH /checkacc: Check Acc Sống/Die chính xác 100% + Đầy đủ thông số & Avatar
# -------------------------------------------------------------------------
@bot.slash_command(name="checkacc", description="Check trạng thái tài khoản TikTok (Sống/Die) kèm Follow, Tim, Video")
async def check_acc(
    ctx: discord.ApplicationContext,
    username: discord.Option(str, description="Nhập @username hoặc link profile TikTok")
):
    await ctx.defer(ephemeral=False)

    # Làm sạch username
    clean_user = username.replace("https://www.tiktok.com/@", "").replace("@", "").strip().split("/")[0]
    profile_url = f"https://www.tiktok.com/@{clean_user}"
    
    # Sử dụng API ngầm của TikTok để lấy JSON chính xác tuyệt đối
    api_url = f"https://www.tiktok.com/node/share/user/@{clean_user}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=HEADERS, timeout=10) as resp:
                if resp.status != 200:
                    # Nếu lỗi mạng hoặc không gọi được API
                    await ctx.followup.send(f"⚠️ Không thể kết nối tới TikTok để check tài khoản `@{clean_user}`.", ephemeral=True)
                    return

                data = await resp.json()
                user_info = data.get("body", {}).get("userInfo", {})
                user_data = user_info.get("user", {})
                stats_data = user_info.get("stats", {})

                # Nếu không tìm thấy user_data nghĩa là acc không tồn tại hoặc bị khóa
                if not user_data:
                    embed = discord.Embed(
                        title="❌ TÀI KHOẢN ĐÃ DIE / BỊ BAN",
                        description=f"Tài khoản `@{clean_user}` không tồn tại hoặc đã bị TikTok khóa vĩnh viễn.",
                        color=discord.Color.red()
                    )
                    embed.add_field(name="🔗 Profile", value=f"[Trang cá nhân]({profile_url})", inline=False)
                else:
                    # Lấy thông tin tài khoản SỐNG chuẩn xác
                    nickname = user_data.get("nickname", clean_user)
                    avatar = user_data.get("avatarLarger", "") or user_data.get("avatarMedium", "")
                    
                    followers = stats_data.get("followerCount", 0)
                    likes = stats_data.get("heartCount", 0)
                    videos = stats_data.get("videoCount", 0)

                    embed = discord.Embed(
                        title="✅ TÀI KHOẢN HOẠT ĐỘNG (SỐNG)",
                        description=f"**Tên kênh:** {nickname}\n**ID:** `@{clean_user}`",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="👥 Follower", value=f"`{followers:,}`", inline=True)
                    embed.add_field(name="❤️ Tổng Tim", value=f"`{likes:,}`", inline=True)
                    embed.add_field(name="🎬 Video", value=f"`{videos:,}`", inline=True)
                    embed.add_field(name="🔗 Profile", value=f"[Trang cá nhân TikTok]({profile_url})", inline=False)
                    
                    if avatar:
                        embed.set_thumbnail(url=avatar) # Ảnh Avatar của kênh TikTok

                # Hiển thị Avatar & Tên của người check ở Footer
                user_avatar = ctx.author.display_avatar.url if ctx.author.display_avatar else ctx.author.default_avatar.url
                embed.set_footer(text=f"Yêu cầu bởi {ctx.author.name}", icon_url=user_avatar)

                await ctx.followup.send(embed=embed)
    except Exception as e:
        await ctx.followup.send(f"⚠️ Lỗi hệ thống: `{e}`", ephemeral=True)

# -------------------------------------------------------------------------
# LỆNH /checklive: Check Live + Mắt xem + Tim Live + Ảnh Live
# -------------------------------------------------------------------------
@bot.slash_command(name="checklive", description="Check trạng thái Livestream (Sống/Die), mắt xem, thả tim và ảnh live")
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
                    views_match = re.search(r'"user_count":(\d+)', html)
                    likes_match = re.search(r'"like_count":(\d+)', html)
                    img_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                    
                    views = int(views_match.group(1)) if views_match else 0
                    likes = int(likes_match.group(1)) if likes_match else 0
                    thumb_url = img_match.group(1) if img_match else ""

                    embed = discord.Embed(
                        title="🟢 TRẠNG THÁI: LIVE ĐANG PHÁT (SỐNG)",
                        description="Phòng Livestream đang phát trực tiếp!",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="👁️ Mắt xem hiện tại", value=f"`{views:,}` người", inline=True)
                    embed.add_field(name="💖 Tổng tim phiên live", value=f"`{likes:,}` tim", inline=True)
                    embed.add_field(name="📌 Link Live", value=f"[Xem Livestream Ngay]({real_link})", inline=False)
                    
                    if thumb_url:
                        embed.set_image(url=thumb_url)

                user_avatar = ctx.author.display_avatar.url if ctx.author.display_avatar else ctx.author.default_avatar.url
                embed.set_footer(text=f"Yêu cầu bởi {ctx.author.name}", icon_url=user_avatar)

                await ctx.followup.send(embed=embed)
    except Exception as e:
        await ctx.followup.send(f"⚠️ Lỗi kết nối tới TikTok: `{e}`", ephemeral=True)

bot.run("TOKEN_BOT_CỦA_BẠN")
