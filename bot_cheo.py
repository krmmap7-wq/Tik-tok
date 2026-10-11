import discord
from discord.ext import commands

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

user_points = {}

@bot.event
async def on_ready():
    print(f'=== BOT CHÉO ONLINE: {bot.user} ===')

@bot.slash_command(name="diem", description="Check số dư điểm tương tác chéo")
async def check_diem(ctx):
    points = user_points.get(ctx.author.id, 100)
    await ctx.respond(f"💎 **Số dư hiện tại của bạn:** `{points}` Điểm", ephemeral=True)

@bot.slash_command(name="buffcheo", description="Đổi điểm lấy lượt tương tác chéo")
async def buff_cheo(ctx, loai: str, link: str):
    current_points = user_points.get(ctx.author.id, 100)
    cost = 20
    
    if current_points < cost:
        await ctx.respond("❌ Bạn không đủ điểm! Hãy treo acc làm nhiệm vụ để tích thêm.", ephemeral=True)
        return

    user_points[ctx.author.id] = current_points - cost
    await ctx.respond(f"✅ **Đã tạo đơn {loai}!**\n🔗 **Target:** {link}\n📉 **Đã trừ:** {cost} Điểm (Còn lại: {user_points[ctx.author.id]})")

bot.run("TOKEN_BOT_3_CỦA_BẠN")
