import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)

FILE_DATABASE = {
    "tool_capcut_vip": {
        "link": "https://mega.nz/file/example_capcut_vip",
        "required_invites": 3,
        "description": "File mod mở khóa toàn bộ tính năng Pro"
    },
    "script_tiktok_auto": {
        "link": "https://drive.google.com/file/example_script",
        "required_invites": 5,
        "description": "Source code Python auto tương tác TikTok"
    }
}

user_invites_cache = {}

@bot.event
async def on_ready():
    print(f'=== BOT STORE ONLINE: {bot.user} ===')

@bot.slash_command(name="layfile", description="Nhận file VIP bằng cách hoàn thành số lượt mời bạn bè")
async def lay_file(ctx, ten_file: str):
    if ten_file not in FILE_DATABASE:
        await ctx.respond(f"❌ Không tìm thấy file `{ten_file}` trong kho!", ephemeral=True)
        return

    file_info = FILE_DATABASE[ten_file]
    required = file_info["required_invites"]
    current_invites = user_invites_cache.get(ctx.author.id, 0)

    if current_invites < required:
        embed = discord.Embed(
            title="🔒 Chưa Đủ Điều Kiện Nhận File!",
            description=f"Bạn muốn tải: **{ten_file}**\n\n- Yêu cầu: **{required} lượt mời**\n- Hiện có: **{current_invites}/{required} lượt**\n\n👉 Hãy copy Link mời riêng của bạn gửi cho bạn bè để mở khóa!",
            color=discord.Color.red()
        )
        await ctx.respond(embed=embed, ephemeral=True)
        return

    try:
        dm_channel = await ctx.author.create_dm()
        await dm_channel.send(f"🎉 **Đã mở khóa!**\n📂 **File:** {ten_file}\n🔗 **Link tải:** {file_info['link']}")
        await ctx.respond(f"✅ Đã gửi thông tin file vào Tin nhắn riêng (DM) của bạn!", ephemeral=True)
    except Exception:
        await ctx.respond("❌ Không thể gửi DM. Hãy mở tính năng nhận tin nhắn từ thành viên trong server!", ephemeral=True)

@bot.slash_command(name="kiemtra_invite", description="Xem bạn đã kéo được bao nhiêu người")
async def kiem_tra_invite(ctx):
    current_invites = user_invites_cache.get(ctx.author.id, 0)
    await ctx.respond(f"📊 Bạn đã mời thành công: **{current_invites} người** vào server.", ephemeral=True)

bot.run("TOKEN_BOT_4_CỦA_BẠN")
