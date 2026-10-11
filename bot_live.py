import discord
from discord.ext import commands
import aiohttp
import re
import json

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
}

@bot.event
async def on_ready():
    print(f'=== BOT CHECK TIKTOK ONLINE: {bot.user} ===')
    try:
        await bot.sync_commands()
        print("✅ Đã sync toàn bộ lệnh mới thành công!")
    except Exception as e:
        print(f"Lỗi Sync: {e}")

# -------------------------------------------------------------------------
# 1. LỆNH /checkacc: Check Acc Sống/Die + Avatar + Follower + Tim + Người check
# -------------------------------------------------------------------------
@bot.slash_command(name="checkacc", description="Check trạng thái Acc TikTok (Sống/Die), số Follow, Tim & Avatar")
async def check_acc(
    ctx: discord.ApplicationContext,
    username: discord.Option(str, description="Nhập @username hoặc link profile TikTok")
):
    await ctx.defer(ephemeral=False)

    clean_user = username.replace("https://www.tiktok.com/@", "").replace("@", "").strip().split("/")[0]
    api_url = f"https://www.tiktok.com/api/user/detail/?uniqueId={clean_user}"
    profile_url = f"https://www.tiktok.com/@{clean_user}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers, timeout=10) as resp:
                data = await resp.json()
                
                # Kiểm tra nếu lấy được dữ liệu User
                user_info = data.get("userInfo", {})
                user_data = user_info.get("user", {})
                stats_data = user_info.get("stats", {})

                if not user_data:
                    # Trường hợp tài khoản Die/Ban
                    embed = discord.Embed(
                        title="❌ TÀI KHOẢN ĐÃ DIE / BỊ BAN",
                        description=f"Tài khoản `@{clean_user}` không tồn tại hoặc đã bị TikTok khóa.",
                        color=discord.Color.red()
                    )
                    embed.add_field(name="🔗 Profile", value=f"[Truy cập]({profile_url})", inline=False)
                else:
                    # Trường hợp tài khoản SỐNG
                    nickname = user_data.get("nickname", clean_user)
                    avatar = user_data.get("avatarLarger", "") or user_data.get("avatarMedium", "")
                    
                    followers = stats_data.get("followerCount", 0)
                    likes = stats_data.get("heartCount", 0)
                    videos = stats_data.get("videoCount", 0)

                    embed = discord.Embed(
                        title=f"✅ TÀI KHOẢN HOẠT ĐỘNG (SỐNG)",
                        description=f"**Tên kênh:** {nickname}\n**ID:** `@{clean_user}`",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="👥 Follower", value=f"`{followers:,}`", inline=True)
                    embed.add_field(name="❤️ Tổng Tim", value=f"`{likes:,}`", inline=True)
                    embed.add_field(name="🎬 Video", value=f"`{videos:,}`", inline=True)
                    embed.add_field(name="🔗 Profile", value=f"[Trang cá nhân TikTok]({profile_url})", inline=False)
                    
                    if avatar:
                        embed.set_thumbnail(url=avatar) # Avatar nick TikTok

                # Hiển thị Avatar & Tên người bấm lệnh ở Footer
                user_avatar = ctx.author.display_avatar.url if ctx.author.display_avatar else ctx.author.default_avatar.url
                embed.set_footer(text=f"Yêu cầu bởi {ctx.author.name}", icon_url=user_avatar)
                
                await ctx.followup.send(embed=embed)
    except Exception as e:
        await ctx.followup.send(f"⚠️ Lỗi hệ thống khi check acc: `{e}`", ephemeral=True)

# -------------------------------------------------------------------------
# 2. LỆNH /checklive: Check Live Sống/Die + Mắt xem + Tim Live + Ảnh Live + Người check
# -------------------------------------------------------------------------
@bot.slash_command(name="checklive", description="Check trạng thái Live (Mắt xem, Tim, Ảnh phiên Live)")
async def check_live(
    ctx: discord.ApplicationContext,
    link_live: discord.Option(str, description="Dán link live TikTok vào đây")
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
            async with session.get(real_link, headers=headers, timeout=10) as resp:
                html = await resp.text()

                # Kiểm tra phòng live có tồn tại và đang phát hay không
                if "Live Room Ended" in html or "room_id" not in html or resp.status != 200:
                    embed = discord.Embed(
                        title="🔴 TRẠNG THÁI: LIVE ĐÃ TẮT (DIE)",
                        description="Phòng Livestream này đã kết thúc hoặc không tồn tại.",
                        color=discord.Color.red()
                    )
                    embed.add_field(name="📌 Link kiểm tra", value=f"[Truy cập phòng Live]({real_link})", inline=False)
                else:
                    # Lấy thông số Mắt xem (User Count) và Ảnh bìa Live từ HTML Data
                    views_match = re.search(r'"user_count":(\d+)', html)
                    likes_match = re.search(r'"like_count":(\d+)', html)
                    img_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                    
                    views = int(views_match.group(1)) if views_match else 0
                    likes = int(likes_match.group(1)) if likes_match else 0
                    thumb_url = img_match.group(1) if img_match else ""

                    embed = discord.Embed(
                        title="🟢 TRẠNG THÁI: LIVE ĐANG PHÁT (SỐNG)",
                        description="Phòng Livestream vẫn đang hoạt động trực tiếp!",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="👁️ Mắt xem hiện tại", value=f"`{views:,}` người", inline=True)
                    embed.add_field(name="💖 Lượt thả tim", value=f"`{likes:,}` tim", inline=True)
                    embed.add_field(name="📌 Link Live", value=f"[Xem Livestream Ngay]({real_link})", inline=False)
                    
                    if thumb_url:
                        embed.set_image(url=thumb_url) # Ảnh thumbnail phiên live

                # Hiển thị Avatar & Tên người bấm lệnh ở Footer
                user_avatar = ctx.author.display_avatar.url if ctx.author.display_avatar else ctx.author.default_avatar.url
                embed.set_footer(text=f"Yêu cầu bởi {ctx.author.name}", icon_url=user_avatar)

                await ctx.followup.send(embed=embed)
    except Exception as e:
        await ctx.followup.send(f"⚠️ Lỗi hệ thống khi check live: `{e}`", ephemeral=True)

bot.run("TOKEN_BOT_CỦA_BẠN")
