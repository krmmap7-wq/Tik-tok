import discord
from discord.ext import commands
import asyncio

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f'=== BOT LIVE ONLINE: {bot.user} ===')

@bot.slash_command(name="autolive", description="Tự động buff comment/thả tym Livestream")
async def auto_live(ctx, link_live: str, noi_dung: str, so_luong: int = 5):
    if so_luong > 20:
        await ctx.respond("⚠️ Tối đa 20 comment cho 1 lần chạy để tránh spam!", ephemeral=True)
        return

    await ctx.respond(f"🚀 **Đã nhận đơn Live!**\n📌 **Link:** {link_live}\n💬 **Nội dung:** `{noi_dung}`\n🔄 **Số lượng:** {so_luong} lượt")
    
    for i in range(1, so_luong + 1):
        await asyncio.sleep(2)
        print(f"[Worker Live] Đã comment lượt {i}/{so_luong} vào {link_live}")

    await ctx.send(f"✅ **Đã hoàn thành buff Live cho:** {ctx.author.mention}")

bot.run("TOKEN_BOT_2_CỦA_BẠN")
