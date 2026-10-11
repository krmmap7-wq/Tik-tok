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

# Cập nhật Embed Nội Quy mới cho kênh Check Live/Acc TikTok
embed_live = discord.Embed(
    title="🎩 KAITOU KID SHOW - KÊNH CHECK LIVE & ACC TIKTOK",
    description="Hệ thống kiểm tra trạng thái Livestream và Tài khoản TikTok siêu tốc.",
    color=discord.Color.blue()
)
embed_live.add_field(
    name="📌 CÚ PHÁP LỆNH", 
    value="• `/checklive <link>`: Check trạng thái Livestream (Live/Die).\n• `/checkacc <username>`: Check trạng thái tài khoản TikTok (Sống/Ban).", 
    inline=False
)
embed_live.add_field(name="⚠️ QUY ĐỊNH 24/7", value="1. Chỉ dùng lệnh đúng kênh quy định.\n2. Nghiêm cấm spam lệnh liên tục.", inline=False)
embed_live.set_footer(text="Kaitou Kid • Giám sát TikTok 24/7")

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


# ==================== BOT 2: KAITOU KID (CHECK LIVE & ACC TIKTOK) ====================
bot_2 = commands.Bot(command_prefix="/", intents=intents)

@bot_2.event
async def on_ready():
    print(f"🟢 Bot Kaitou Kid ({bot_2.user}) đã Trực tuyến!")
    await bot_2.change_presence(activity=discord.Game(name="🎩 Check Live & Acc TikTok"))

@bot_2.slash_command(name="setup_luat", description="Gửi và ghim bảng nội quy cố định kênh Live")
@commands.has_permissions(administrator=True)
async def setup_luat_2(ctx):
    msg = await ctx.send(embed=embed_live)
    await msg.pin()
    await ctx.respond("✅ Đã ghim bảng nội quy Kaitou Kid 24/7 thành công!", ephemeral=True)

# LỆNH 1: CHECK LIVE TIKTOK (LIVE / DIE)
@bot_2.slash_command(name="checklive", description="Kiểm tra trạng thái Livestream TikTok (Sống hay Die)")
async def check_live(ctx, link_live: str):
    if ctx.guild.id != GUILD_ID or ctx.channel.id != CHANNEL_LIVE:
        await ctx.respond("❌ Lệnh này chỉ được dùng tại kênh Live quy định!", ephemeral=True)
        return

    await ctx.defer(ephemeral=True)
    
    # Xử lý lấy link gốc nếu là link vt.tiktok.com
    real_link = link_live
    if "vt.tiktok.com" in link_live or "vm.tiktok.com" in link_live:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(link_live, allow_redirects=True, timeout=5) as resp:
                    real_link = str(resp.url)
        except Exception:
            pass

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(real_link, headers=headers, timeout=10) as resp:
                html = await resp.text()
                
                # Kiểm tra trạng thái Live trong mã HTML
                if "Live Room Ended" in html or "room_id" not in html or resp.status != 200:
                    embed = discord.Embed(
                        title="🔴 TRẠNG THÁI: LIVE ĐÃ TẮT (DIE)",
                        description=f"Phòng Livestream này đã kết thúc hoặc không tồn tại.",
                        color=discord.Color.red()
                    )
                else:
                    embed = discord.Embed(
                        title="🟢 TRẠNG THÁI: LIVE ĐANG PHÁT (SỐNG)",
                        description=f"Phòng Livestream vẫn đang phát trực tiếp bình thường!",
                        color=discord.Color.green()
                    )
                embed.add_field(name="📌 Link kiểm tra", value=f"[Truy cập phòng Live]({real_link})", inline=False)
                await ctx.respond(embed=embed, ephemeral=True)
    except Exception as e:
        await ctx.respond(f"⚠️ Lỗi kết nối tới TikTok: `{e}`", ephemeral=True)

# LỆNH 2: CHECK ACC TIKTOK (SỐNG / BAN)
@bot_2.slash_command(name="checkacc", description="Kiểm tra tài khoản TikTok (Sống hay đã bị Ban/Die)")
async def check_acc(ctx, username: str):
    if ctx.guild.id != GUILD_ID or ctx.channel.id != CHANNEL_LIVE:
        await ctx.respond("❌ Lệnh này chỉ được dùng tại kênh Live quy định!", ephemeral=True)
        return

    await ctx.defer(ephemeral=True)

    # Làm sạch username
    clean_user = username.replace("https://www.tiktok.com/@", "").replace("@", "").strip().split("/")[0]
    profile_url = f"https://www.tiktok.com/@{clean_user}"

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(profile_url, headers=headers, timeout=10) as resp:
                if resp.status == 404:
                    embed = discord.Embed(
                        title="❌ TÀI KHOẢN ĐÃ DIE / BỊ KHÓA",
                        description=f"Tài khoản `@{clean_user}` không tồn tại hoặc đã bị khóa.",
                        color=discord.Color.red()
                    )
                else:
                    html = await resp.text()
                    if "Couldn't find this account" in html or "This account was banned" in html:
                        embed = discord.Embed(
                            title="❌ TÀI KHOẢN ĐÃ DIE / BỊ BAN",
                            description=f"Tài khoản `@{clean_user}` đã bị TikTok cấm hoạt động.",
                            color=discord.Color.red()
                        )
                    else:
                        embed = discord.Embed(
                            title="✅ TÀI KHOẢN HOẠT ĐỘNG (SỐNG)",
                            description=f"Tài khoản `@{clean_user}` hoàn toàn bình thường.",
                            color=discord.Color.green()
                        )
                embed.add_field(name="🔗 Profile", value=f"[Trang cá nhân]({profile_url})", inline=False)
                await ctx.respond(embed=embed, ephemeral=True)
    except Exception as e:
        await ctx.respond(f"⚠️ Lỗi khi check tài khoản: `{e}`", ephemeral=True)


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
