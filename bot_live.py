import discord
from discord.ext import commands
import asyncio
import aiohttp

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

# Hàm mở rộng link vt.tiktok.com -> Link Live chuẩn
async def expand_url(url: str) -> str:
    if "vt.tiktok.com" in url or "vm.tiktok.com" in url:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, allow_redirects=True, timeout=5) as response:
                    return str(response.url)
        except Exception as e:
            print(f"[Warning] Lỗi giải mã link: {e}")
            return url
    return url

# Hàm gửi comment sử dụng COOKIE DO NGUỜI DÙNG CUNG CẤP
async def send_tiktok_comment(room_id: str, text: str, user_cookie: str) -> bool:
    url = "https://www.tiktok.com/api/live/web/room/send_msg/"
    
    # Xử lý format cookie nếu người dùng chỉ nhập sessionid
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
                    print(f"[TikTok Error] {data}")
                    return False
    except Exception as e:
        print(f"[Request Error] {e}")
        return False

@bot.event
async def on_ready():
    print(f'=== BOT DISCORD LIVE ONLINE: {bot.user} ===')

# THÊM THAM SỐ cookie VÀO LỆNH /autolive
@bot.slash_command(name="autolive", description="Tự động buff comment TikTok Live bằng Cookie cá nhân")
async def auto_live(
    ctx, 
    link_live: str, 
    noi_dung: str, 
    cookie: str, # <--- Người dùng tự điền Cookie / SessionID của họ vào đây
    so_luong: int = 5
):
    # 1. Chống lỗi "Ứng dụng không phản hồi" (Chế độ ẩn ephemeral để bảo mật Cookie)
    await ctx.defer(ephemeral=True)

    if so_luong > 20:
        await ctx.followup.send("⚠️ Tối đa 20 comment cho 1 lần chạy!", ephemeral=True)
        return

    # 2. Xử lý link rút gọn
    real_link = await expand_url(link_live)

    # Thông báo nhận đơn (Để ephemeral=True để người khác không nhìn thấy Cookie của họ)
    embed = discord.Embed(title="🚀 Đã nhận đơn Live!", color=discord.Color.green())
    embed.add_field(name="📌 Link", value=f"[Truy cập Live]({real_link})", inline=False)
    embed.add_field(name="💬 Nội dung", value=f"`{noi_dung}`", inline=True)
    embed.add_field(name="🔄 Số lượng", value=f"`{so_luong}` lượt", inline=True)
    embed.set_footer(text="🔒 Cookie của bạn được bảo mật và xử lý riêng.")
    
    await ctx.followup.send(embed=embed, ephemeral=True)

    # 3. Vòng lặp chạy comment với Cookie người dùng gửi
    success_count = 0
    for i in range(1, so_luong + 1):
        await asyncio.sleep(3) # Delay 3s tránh bị TikTok quét
        
        # Gọi hàm gửi cmt bằng cookie cá nhân
        is_sent = await send_tiktok_comment(room_id="123456789", text=noi_dung, user_cookie=cookie)
        
        if is_sent:
            success_count += 1
            print(f"[{ctx.author}] [{i}/{so_luong}] Comment thành công: {noi_dung}")
        else:
            print(f"[{ctx.author}] [{i}/{so_luong}] Lỗi Cookie hoặc RoomID")

    # Thông báo hoàn thành công khai lên channel
    await ctx.send(f"✅ **{ctx.author.mention}** đã buff xong `{success_count}/{so_luong}` comment vào Live!")

bot.run("TOKEN_BOT_CỦA_BẠN")
