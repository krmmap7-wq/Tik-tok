import discord
from discord.ext import commands
import aiohttp

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

# 1. Hàm đồng bộ lệnh tự động khi bot online
@bot.event
async def on_ready():
    print(f'=== BOT CHECK LIVE/ACC ONLINE: {bot.user} ===')
    try:
        await bot.sync_commands()
        print("✅ Đã sync lệnh thành công lên Discord!")
    except Exception as e:
        print(f"❌ Lỗi sync: {e}")

# -------------------------------------------------------------------------
# LỆNH 1: CHECK LIVE TIKTOK (Sống hay Die)
# -------------------------------------------------------------------------
@bot.slash_command(name="checklive", description="Kiểm tra trạng thái Livestream TikTok còn sống hay đã tắt")
async def check_live(
    ctx: discord.ApplicationContext,
    link_live: discord.Option(str, description="Nhập link hoặc ID phòng live TikTok")
):
    await ctx.defer(ephemeral=False)

    # Xử lý lấy link rút gọn nếu có
    real_link = link_live
    if "vt.tiktok.com" in link_live or "vm.tiktok.com" in link_live:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(link_live, allow_redirects=True, timeout=5) as resp:
                    real_link = str(resp.url)
        except:
            pass

    # Giả lập check trạng thái phòng live qua Web API TikTok hoặc trích xuất thông tin
    # Thông thường TikTok trả về dữ liệu phòng live qua web endpoint
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        async with aiohttp.ClientSession() as session:
            # Thêm request vào trang web live của tiktok để check xem còn tồn tại phòng hay không
            async with session.get(real_link, headers=headers, timeout=10) as resp:
                html = await resp.text()
                
                # Kiểm tra các dấu hiệu phòng live đã kết thúc hoặc không tìm thấy
                if "Live Room Ended" in html or "room_id" not in html or resp.status != 200:
                    embed = discord.Embed(
                        title="🔴 TRẠNG THÁI: LIVE ĐÃ TẮT (DIE)",
                        description=f"Phòng Livestream này đã kết thúc hoặc không tồn tại.",
                        color=discord.Color.red()
                    )
                else:
                    embed = discord.Embed(
                        title="🟢 TRẠNG THÁI: LIVE ĐANG HOẠT ĐỘNG (SỐNG)",
                        description=f"Phòng Livestream vẫn đang phát bình thường!",
                        color=discord.Color.green()
                    )
                embed.add_field(name="📌 Link kiểm tra", value=f"[Bấm vào đây để xem]({real_link})", inline=False)
                await ctx.followup.send(embed=embed)
    except Exception as e:
        await ctx.followup.send(f"⚠️ Không thể kết nối tới TikTok để kiểm tra. Lỗi: `{e}`", ephemeral=True)

# -------------------------------------------------------------------------
# LỆNH 2: CHECK ACC TIKTOK (Sống hay Bị Khóa/Die)
# -------------------------------------------------------------------------
@bot.slash_command(name="checkacc", description="Kiểm tra tài khoản TikTok còn hoạt động hay đã bị khóa (Die)")
async def check_acc(
    ctx: discord.ApplicationContext,
    username: discord.Option(str, description="Nhập ID tài khoản TikTok (Ví dụ: @channehoặc link profile)")
):
    await ctx.defer(ephemeral=False)

    # Làm sạch username (bỏ dấu @ hoặc link nếu người dùng dán cả link vào)
    clean_user = username.replace("https://www.tiktok.com/@", "").replace("@", "").strip().split("/")[0]
    profile_url = f"https://www.tiktok.com/@{clean_user}"

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(profile_url, headers=headers, timeout=10) as resp:
                # Nếu tài khoản bị ban/xóa, TikTok thường trả về mã lỗi 404 hoặc thông báo user not found
                if resp.status == 404:
                    embed = discord.Embed(
                        title="❌ TÀI KHOẢN ĐÃ DIE / BỊ KHÓA",
                        description=f"Tài khoản `@{clean_user}` không tồn tại hoặc đã bị TikTok khóa vĩnh viễn.",
                        color=discord.Color.red()
                    )
                else:
                    html = await resp.text()
                    # Kiểm tra thêm một số từ khóa báo tài khoản bị cấm trên web
                    if "Couldn't find this account" in html or "This account was banned" in html:
                        embed = discord.Embed(
                            title="❌ TÀI KHOẢN ĐÃ DIE / BỊ BAN",
                            description=f"Tài khoản `@{clean_user}` đã bị phát hiện vi phạm và bị khóa.",
                            color=discord.Color.red()
                        )
                    else:
                        embed = discord.Embed(
                            title="✅ TÀI KHOẢN HOẠT ĐỘNG BÌNH THƯỜNG (SỐNG)",
                            description=f"Tài khoản `@{clean_user}` hoàn toàn bình thường.",
                            color=discord.Color.green()
                        )
                
                embed.add_field(name="🔗 Profile", value=f"[Truy cập trang cá nhân]({profile_url})", inline=False)
                await ctx.followup.send(embed=embed)
    except Exception as e:
        await ctx.followup.send(f"⚠️ Lỗi khi check tài khoản: `{e}`", ephemeral=True)

bot.run("TOKEN_BOT_CỦA_BẠN")
