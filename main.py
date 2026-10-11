import asyncio
import os
import pyotp
import aiohttp
import discord
from discord.ext import commands

# ==================== CẤU HÌNH BIẾN MÔI TRƯỜNG ====================
GUILD_ID = int(os.getenv("GUILD_ID", 0))
CHANNEL_CHECK = int(os.getenv("CHANNEL_CHECK_ID", 0))
CHANNEL_LIVE = int(os.getenv("CHANNEL_LIVE_ID", 0))
CHANNEL_CHEO = int(os.getenv("CHANNEL_CHEO_ID", 0))
CHANNEL_STORE = int(os.getenv("CHANNEL_STORE_ID", 0))

intents = discord.Intents.default()
intents.members = True

# ==================== EMBED NỘI QUY CỐ ĐỊNH 24/7 ====================
embed_check = discord.Embed(
    title="🔍 BOURBON INVESTIGATION - NỘI QUY KÊNH CHECK & 2FA",
    description="Hệ thống kiểm tra thông tin Facebook & Lấy mã 2FA siêu tốc.",
    color=discord.Color.gold()
)
embed_check.add_field(name="📌 CÚ PHÁP LỆNH", value="• `/2fa <secret_key>`: Lấy mã 2FA tức thì.\n• `/checkuid <uid>`: Check trạng thái Facebook UID.", inline=False)
embed_check.add_field(name="⚠️ QUY ĐỊNH 24/7", value="1. Chỉ dùng lệnh tại kênh này, cấm spam.\n2. Lệnh trả kết quả ẩn, chống trôi kênh 100%.", inline=False)
embed_check.set_footer(text="Mật danh Bourbon • Giám sát 24/7")

embed_live = discord.Embed(
    title="🎩 KAITOU KID SHOW - NỘI QUY AUTO LIVE BOOSTER",
    description="Hệ thống hỗ trợ tương tác Livestream rực rỡ trước ánh đèn sân khấu.",
    color=discord.Color.blue()
)
embed_live.add_field(name="📌 CÚ PHÁP LỆNH", value="• `/autolive <link> <noi_dung> <so_luong>`: Buff comment livestream.", inline=False)
embed_live.add_field(name="⚠️ QUY ĐỊNH 24/7", value="1. Tối đa 20 comment mỗi đơn.\n2. Cấm link đồi trụy / vi phạm pháp luật.", inline=False)
embed_live.set_footer(text="Kaitou Kid • Sân khấu ảo thuật 24/7")

embed_cheo = discord.Embed(
    title="⚽ EDOGAWA CONAN - NỘI QUY TƯƠNG TÁC CHÉO",
    description="Hệ thống tích điểm và hỗ trợ tương tác chéo giữa các thành viên.",
    color=discord.Color.red()
)
embed_cheo.add_field(name="📌 CÚ PHÁP LỆNH", value="• `/diem`: Kiểm tra số dư điểm cá nhân.", inline=False)
embed_cheo.add_field(name="⚠️ QUY ĐỊNH 24/7", value="1. Nghiêm cấm gian lận điểm dưới mọi hình thức.\n2. Tương tác văn minh, hỗ trợ lẫn nhau.", inline=False)
embed_cheo.set_footer(text="Edogawa Conan • Sự thật chỉ có một 24/7")

embed_store = discord.Embed(
    title="🧪 HAIBARA AI - NỘI QUY KHO TÀI NGUYÊN VIP",
    description="Nơi lưu trữ dữ liệu mã hóa và phần mềm VIP độc quyền.",
    color=discord.Color.purple()
)
embed_store.add_field(name="📌 CÚ PHÁP LỆNH", value="• `/layfile <ten_file>`: Mở khóa nhận file VIP.", inline=False)
embed_store.add_field(name="⚠️ QUY ĐỊNH 24/7 (Invite to Unlock)", value="1. Cần đủ lượt mời (Invite) để mở khóa file.\n2. Nghiêm cấm phát tán link ra bên ngoài.", inline=False)
embed_store.set_footer(text="Haibara Ai • Dữ liệu mã hóa APTX-4869 24/7")


# ==================== BOT 1: BOURBON (CHECK & 2FA) ====================
bot_1 = commands.Bot(command_prefix="/", intents=intents)

@bot_1.event
async def on_ready():
    print(f"🟢 Bot Bourbon ({bot_1.user}) đã Trực tuyến!")
    await bot_1.change_presence(activity=discord.Game(name="🔍 Soi mã 2FA & Check UID"))

@bot_1.slash_command(name="setup_luat", description="Gửi và ghim bảng nội quy cố định kênh Check")
@commands.has_permissions(administrator=True)
async def setup_luat_1(ctx):
    msg = await ctx.send(embed=embed_check)
    await msg.pin()
    await ctx.respond("✅ Đã ghim bảng nội quy Bourbon 24/7 thành công!", ephemeral=True)

@bot_1.slash_command(name="2fa", description="Lấy mã 2FA siêu tốc")
async def get_2fa(ctx, secret_key: str):
    if ctx.guild.id != GUILD_ID or ctx.channel.id != CHANNEL_CHECK:
        await ctx.respond("❌ Lệnh này chỉ được dùng tại kênh Check quy định!", ephemeral=True)
        return
    try:
        totp = pyotp.TOTP(secret_key.replace(" ", ""))
        await ctx.respond(f"🔑 **Mã 2FA của bạn:** `{totp.now()}`", ephemeral=True)
    except Exception:
        await ctx.respond("❌ Secret Key 2FA không hợp lệ!", ephemeral=True)

@bot_1.slash_command(name="checkuid", description="Check status UID Facebook")
async def check_uid(ctx, uid: str):
    if ctx.guild.id != GUILD_ID or ctx.channel.id != CHANNEL_CHECK:
        await ctx.respond("❌ Lệnh này chỉ được dùng tại kênh Check quy định!", ephemeral=True)
        return
    await ctx.defer(ephemeral=True)
    url = f"https://graph.facebook.com/{uid}/picture?type=normal"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                await ctx.respond(f"🟢 **UID {uid}:** LIVE", ephemeral=True)
            else:
                await ctx.respond(f"🔴 **UID {uid}:** DIE / PRIVATE", ephemeral=True)


# ==================== BOT 2: KAITOU KID (AUTO LIVE) ====================
bot_2 = commands.Bot(command_prefix="/", intents=intents)

@bot_2.event
async def on_ready():
    print(f"🟢 Bot Kaitou Kid ({bot_2.user}) đã Trực tuyến!")
    await bot_2.change_presence(activity=discord.Game(name="🎩 Ảo thuật Livestream"))

@bot_2.slash_command(name="setup_luat", description="Gửi và ghim bảng nội quy cố định kênh Live")
@commands.has_permissions(administrator=True)
async def setup_luat_2(ctx):
    msg = await ctx.send(embed=embed_live)
    await msg.pin()
    await ctx.respond("✅ Đã ghim bảng nội quy Kaitou Kid 24/7 thành công!", ephemeral=True)

@bot_2.slash_command(name="autolive", description="Buff comment Livestream")
async def auto_live(ctx, link_live: str, noi_dung: str, so_luong: int = 5):
    if ctx.guild.id != GUILD_ID or ctx.channel.id != CHANNEL_LIVE:
        await ctx.respond("❌ Lệnh này chỉ được dùng tại kênh Live quy định!", ephemeral=True)
        return
    if so_luong > 20:
        await ctx.respond("⚠️ Tối đa 20 comment cho 1 đơn!", ephemeral=True)
        return
    await ctx.respond(f"🚀 **Đã nhận đơn Live!**\n📌 Link: {link_live}\n📝 Nội dung: `{noi_dung}`", ephemeral=True)


# ==================== BOT 3: EDOGAWA CONAN (TƯƠNG TÁC CHÉO) ====================
bot_3 = commands.Bot(command_prefix="/", intents=intents)
user_points = {}

@bot_3.event
async def on_ready():
    print(f"🟢 Bot Conan ({bot_3.user}) đã Trực tuyến!")
    await bot_3.change_presence(activity=discord.Game(name="⚽ Tương Tác Chéo & Điểm"))

@bot_3.slash_command(name="setup_luat", description="Gửi và ghim bảng nội quy cố định kênh Chéo")
@commands.has_permissions(administrator=True)
async def setup_luat_3(ctx):
    msg = await ctx.send(embed=embed_cheo)
    await msg.pin()
    await ctx.respond("✅ Đã ghim bảng nội quy Conan 24/7 thành công!", ephemeral=True)

@bot_3.slash_command(name="diem", description="Check số dư điểm")
async def check_diem(ctx):
    if ctx.guild.id != GUILD_ID or ctx.channel.id != CHANNEL_CHEO:
        await ctx.respond("❌ Lệnh này chỉ được dùng tại kênh Tương tác chéo!", ephemeral=True)
        return
    points = user_points.get(ctx.author.id, 100)
    await ctx.respond(f"💎 **Số dư hiện tại của bạn:** `{points}` Điểm", ephemeral=True)


# ==================== BOT 4: HAIBARA AI (KHO FILE & INVITE) ====================
bot_4 = commands.Bot(command_prefix="/", intents=intents)

@bot_4.event
async def on_ready():
    print(f"🟢 Bot Haibara ({bot_4.user}) đã Trực tuyến!")
    await bot_4.change_presence(activity=discord.Game(name="🧪 Quản lý Kho File VIP"))

@bot_4.slash_command(name="setup_luat", description="Gửi và ghim bảng nội quy cố định kênh Kho File")
@commands.has_permissions(administrator=True)
async def setup_luat_4(ctx):
    msg = await ctx.send(embed=embed_store)
    await msg.pin()
    await ctx.respond("✅ Đã ghim bảng nội quy Haibara 24/7 thành công!", ephemeral=True)

@bot_4.slash_command(name="layfile", description="Mở khóa nhận file VIP")
async def lay_file(ctx, ten_file: str):
    if ctx.guild.id != GUILD_ID or ctx.channel.id != CHANNEL_STORE:
        await ctx.respond("❌ Lệnh này chỉ được dùng tại kênh Kho File!", ephemeral=True)
        return
    await ctx.respond(f"📂 **Haibara đang truy xuất dữ liệu file `{ten_file}`...**", ephemeral=True)


# ==================== CHẠY BẤT ĐỒNG BỘ 4 BOT BẰNG ASYNCIO ====================
async def main():
    token_1 = os.getenv("TOKEN_BOT_1")
    token_2 = os.getenv("TOKEN_BOT_2")
    token_3 = os.getenv("TOKEN_BOT_3")
    token_4 = os.getenv("TOKEN_BOT_4")

    await asyncio.gather(
        bot_1.start(token_1),
        bot_2.start(token_2),
        bot_3.start(token_3),
        bot_4.start(token_4)
    )

if __name__ == "__main__":
    asyncio.run(main())
