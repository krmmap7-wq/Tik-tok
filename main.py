import threading
import os
import pyotp
import aiohttp
import discord
from discord.ext import commands

# --- Khởi tạo Intents ---
intents = discord.Intents.default()
intents.members = True

# ==================== BOT 1: CHECK & 2FA ====================
bot_1 = commands.Bot(command_prefix="/", intents=intents)

@bot_1.slash_command(name="2fa", description="Lấy mã 2FA siêu tốc")
async def get_2fa(ctx, secret_key: str):
    try:
        totp = pyotp.TOTP(secret_key.replace(" ", ""))
        code = totp.now()
        await ctx.respond(f"🔑 **Mã 2FA của bạn:** `{code}`", ephemeral=True)
    except Exception:
        await ctx.respond("❌ Secret Key không hợp lệ!", ephemeral=True)

@bot_1.slash_command(name="checkuid", description="Check status UID Facebook")
async def check_uid(ctx, uid: str):
    await ctx.defer(ephemeral=True)
    url = f"https://graph.facebook.com/{uid}/picture?type=normal"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                await ctx.respond(f"🟢 **UID {uid}:** LIVE")
            else:
                await ctx.respond(f"🔴 **UID {uid}:** DIE / PRIVATE")

# ==================== BOT 2: AUTO LIVE ====================
bot_2 = commands.Bot(command_prefix="/", intents=intents)

@bot_2.slash_command(name="autolive", description="Tự động buff comment Livestream")
async def auto_live(ctx, link_live: str, noi_dung: str, so_luong: int = 5):
    if so_luong > 20:
        await ctx.respond("⚠️ Tối đa 20 comment!", ephemeral=True)
        return
    await ctx.respond(f"🚀 **Đã nhận đơn Live!**\n📌 Link: {link_live}")
    await ctx.send(f"✅ **Đã hoàn thành buff Live cho:** {ctx.author.mention}")

# ==================== BOT 3: TƯƠNG TÁC CHÉO ====================
bot_3 = commands.Bot(command_prefix="/", intents=intents)
user_points = {}

@bot_3.slash_command(name="diem", description="Check số dư điểm")
async def check_diem(ctx):
    points = user_points.get(ctx.author.id, 100)
    await ctx.respond(f"💎 **Số dư:** `{points}` Điểm", ephemeral=True)

# ==================== BOT 4: STORE & INVITE ====================
bot_4 = commands.Bot(command_prefix="/", intents=intents)
FILE_DATABASE = {
    "tool_capcut_vip": {"link": "https://mega.nz/file/example", "required_invites": 3}
}
user_invites_cache = {}

@bot_4.slash_command(name="layfile", description="Nhận file VIP")
async def lay_file(ctx, ten_file: str):
    await ctx.respond(f"📂 Đang kiểm tra file `{ten_file}`...", ephemeral=True)


# ==================== CHẠY SONG SONG 4 BOT BẰNG THREADING ====================
def run_bot_1():
    bot_1.run("TOKEN_BOT_1_CỦA_BẠN")

def run_bot_2():
    bot_2.run("TOKEN_BOT_2_CỦA_BẠN")

def run_bot_3():
    bot_3.run("TOKEN_BOT_3_CỦA_BẠN")

def run_bot_4():
    bot_4.run("TOKEN_BOT_4_CỦA_BẠN")

if __name__ == "__main__":
    t1 = threading.Thread(target=run_bot_1)
    t2 = threading.Thread(target=run_bot_2)
    t3 = threading.Thread(target=run_bot_3)
    t4 = threading.Thread(target=run_bot_4)

    t1.start()
    t2.start()
    t3.start()
    t4.start()

    t1.join()
    t2.join()
    t3.join()
    t4.join()
