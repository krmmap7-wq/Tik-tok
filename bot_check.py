import discord
from discord.ext import commands
import pyotp
import aiohttp

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f'=== BOT CHECK ONLINE: {bot.user} ===')

@bot.slash_command(name="2fa", description="Lấy mã 2FA siêu tốc")
async def get_2fa(ctx, secret_key: str):
    try:
        totp = pyotp.TOTP(secret_key.replace(" ", ""))
        code = totp.now()
        await ctx.respond(f"🔑 **Mã 2FA của bạn:** `{code}`", ephemeral=True)
    except Exception:
        await ctx.respond("❌ Secret Key không hợp lệ!", ephemeral=True)

@bot.slash_command(name="checkuid", description="Check status UID Facebook")
async def check_uid(ctx, uid: str):
    await ctx.defer(ephemeral=True)
    url = f"https://graph.facebook.com/{uid}/picture?type=normal"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                await ctx.respond(f"🟢 **UID {uid}:** LIVE (Tài khoản hoạt động)")
            else:
                await ctx.respond(f"🔴 **UID {uid}:** DIE / PRIVATE (Không tồn tại hoặc bị khóa)")

bot.run("TOKEN_BOT_1_CỦA_BẠN")
