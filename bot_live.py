import discord
from discord.ext import commands
import asyncio
import aiohttp

intents = discord.Intents.default()
# Khởi tạo Bot Discord
bot = commands.Bot(command_prefix="/", intents=intents)

# Hàm tự giải mã link vt.tiktok.com sang link Live thật
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

@bot.event
async def on_ready():
    print(f'=== BOT DISCORD LIVE ONLINE: {bot.user} ===')

@bot.slash_command(name="autolive", description="Tự động buff comment/thả tym Livestream")
async def auto_live(ctx, link_live: str, noi_dung: str, so_luong: int = 5):
    # 1. FIX LỖI "ỨNG DỤNG KHÔNG PHẢN HỒI": Defer ngay lập tức trong 3s đầu!
    await ctx.defer()

    if so_luong > 20:
        await ctx.followup.send("⚠️ Tối đa 20 comment cho 1 lần chạy để tránh spam!", ephemeral=True)
        return

    # 2. Xử lý link rút gọn vt.tiktok.com -> link live chuẩn
    real_link = await expand_url(link_live)

    # 3. Trả lời lại trên Discord bằng followup
    embed = discord.Embed(
        title="🚀 Đã nhận đơn Live!",
        color=discord.Color.blue()
    )
    embed.add_field(name="📌 Link", value=f"[{real_link}]({real_link})", inline=False)
    embed.add_field(name="💬 Nội dung", value=f"`{noi_dung}`", inline=True)
    embed.add_field(name="🔄 Số lượng", value=f"`{so_luong}` lượt", inline=True)
    
    await ctx.followup.send(embed=embed)

    # 4. Vòng lặp chạy đơn cho Bot Discord
    for i in range(1, so_luong + 1):
        await asyncio.sleep(2) # Delay 2s mỗi cmt
        print(f"[Discord Bot Worker] Lượt {i}/{so_luong} -> Comment '{noi_dung}' vào {real_link}")

    # Thông báo hoàn thành lên kênh Discord
    await ctx.send(f"✅ **Đã hoàn thành buff Live cho:** {ctx.author.mention}")

bot.run("TOKEN_BOT_DISCORD_CUẢ_BẠN")
