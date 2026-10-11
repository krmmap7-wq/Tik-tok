import discord
from discord.ext import commands
import asyncio
import aiohttp

# Khai báo Intents cho Bot Discord
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

# -------------------------------------------------------------------------
# 1. HÀM GIẢI MÃ LINK RÚT GỌN (vt.tiktok.com -> Link Live chuẩn)
# -------------------------------------------------------------------------
async def expand_url(url: str) -> str:
    if "vt.tiktok.com" in url or "vm.tiktok.com" in url:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, allow_redirects=True, timeout=5) as response:
                    return str(response.url)
        except Exception as e:
            print(f"[Warning] Không thể mở rộng URL: {e}")
            return url
    return url

# -------------------------------------------------------------------------
# 2. HÀM GỬI COMMENT VÀO TIKTOK LIVE BẰNG COOKIE TỰ DO
# -------------------------------------------------------------------------
async def send_tiktok_comment(room_id: str, text: str, user_cookie: str) -> bool:
    url = "https://www.tiktok.com/api/live/web/room/send_msg/"
    
    # Định dạng chuỗi Cookie nếu người dùng chỉ truyền sessionid
    cookie_header = user_cookie if "sessionid=" in user_cookie else f"sessionid={user_cookie};"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": cookie_header,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    params = {
        "room_id": room_id,
        "content": text,
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=params, timeout=10) as resp:
                data = await resp.json()
                if data.get("status_code") == 0:
                    return True
                else:
                    print(f"[TikTok API Error] {data}")
                    return False
    except Exception as e:
        print(f"[Request Error] {e}")
        return False

# -------------------------------------------------------------------------
# 3. SỰ KIỆN TỰ ĐỘNG SYNC CÁC THAM SỐ LỆNH MỚI
# -------------------------------------------------------------------------
@bot.event
async def on_ready():
    print(f'=== BOT DISCORD LIVE ONLINE: {bot.user} ===')
    try:
        # Tự động cập nhật các ô nhập mới (bao gồm cookie) lên server Discord
        await bot.sync_commands()
        print("✅ Đã sync toàn bộ Slash Command lên Discord thành công!")
    except Exception as e:
        print(f"❌ Lỗi sync command: {e}")

# -------------------------------------------------------------------------
# 4. SLASH COMMAND /autolive
# -------------------------------------------------------------------------
@bot.slash_command(name="autolive", description="Tự động buff comment TikTok Live bằng Cookie cá nhân")
async def auto_live(
    ctx, 
    link_live: str, 
    noi_dung: str, 
    cookie: str,  # Ô nhập Cookie tự do cho người dùng
    so_luong: int = 5
):
    # 4.1. Hoãn phản hồi ngay lập tức để TRÁNH LỖI "Ứng dụng không phản hồi" (3 giây)
    # ephemeral=True để BẢO MẬT Cookie, chỉ người bấm lệnh mới thấy tin nhắn này
    await ctx.defer(ephemeral=True)

    # Kiểm tra số lượng
    if so_luong > 20:
        await ctx.followup.send("⚠️ Tối đa 20 comment cho 1 lần chạy!", ephemeral=True)
        return
    if so_luong < 1:
        so_luong = 1

    # 4.2. Mở rộng link rút gọn
    real_link = await expand_url(link_live)

    # 4.3. Phản hồi xác nhận đơn (Bảo mật riêng cho người dùng)
    embed = discord.Embed(
        title="🚀 Đã nhận đơn Live!",
        color=discord.Color.green()
    )
    embed.add_field(name="📌 Link", value=f"[Truy cập Live]({real_link})", inline=False)
    embed.add_field(name="💬 Nội dung", value=f"`{noi_dung}`", inline=True)
    embed.add_field(name="🔄 Số lượng", value=f"`{so_luong}` lượt", inline=True)
    embed.set_footer(text="🔒 Cookie của bạn được bảo mật an toàn.")
    
    await ctx.followup.send(embed=embed, ephemeral=True)

    # 4.4. Vòng lặp gửi comment thực tế
    success_count = 0
    for i in range(1, so_luong + 1):
        # Delay 3 giây giữa các lần comment để tránh TikTok quét spam/shadowban
        await asyncio.sleep(3) 
        
        # Gửi request bằng cookie người dùng nhập
        is_sent = await send_tiktok_comment(room_id="123456789", text=noi_dung, user_cookie=cookie)
        
        if is_sent:
            success_count += 1
            print(f"[{ctx.author}] [{i}/{so_luong}] Comment thành công: {noi_dung}")
        else:
            print(f"[{ctx.author}] [{i}/{so_luong}] Thất bại lượt {i}")

    # 4.5. Thông báo kết quả công khai lên kênh Discord
    await ctx.send(f"✅ **{ctx.author.mention}** đã hoàn thành buff `{success_count}/{so_luong}` comment vào Livestream!")

# -------------------------------------------------------------------------
# 5. CHẠY BOT
# -------------------------------------------------------------------------
bot.run("TOKEN_BOT_DISCORD_CỦA_BẠN")
