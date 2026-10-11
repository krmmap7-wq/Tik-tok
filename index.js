const { Client, GatewayIntentBits, REST, Routes, SlashCommandBuilder, MessageFlags } = require('discord.js');
const puppeteer = require('puppeteer');

const client = new Client({
    intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent]
});

// Đăng ký lệnh slash /live
const commands = [
    new SlashCommandBuilder()
        .setName('live')
        .setDescription('Seeding chat TikTok Live')
        .addStringOption(option => 
            option.setName('cookie').setDescription('Chuỗi cookie TikTok vừa lấy').setRequired(true))
        .addStringOption(option => 
            option.setName('url').setDescription('Link phòng livestream TikTok').setRequired(true))
        .addStringOption(option => 
            option.setName('message').setDescription('Nội dung tin nhắn muốn gửi').setRequired(true))
].map(command => command.toJSON());

client.once('ready', async () => {
    console.log(`Bot đã online với tên: ${client.user.tag}`);
    const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);
    try {
        await rest.put(
            Routes.applicationCommands(process.env.CLIENT_ID),
            { body: commands },
        );
        console.log('Đã đăng ký thành công lệnh /live');
    } catch (error) {
        console.error(error);
    }
});

client.on('interactionCreate', async interaction => {
    if (!interaction.isChatInputCommand()) return;

    if (interaction.commandName === 'live') {
        const cookieString = interaction.options.getString('cookie');
        const liveUrl = interaction.options.getString('url');
        const messageText = interaction.options.getString('message');

        // Phản hồi an toàn không bị lỗi deprecated ephemeral
        await interaction.reply({ 
            content: '🚀 Bot đang khởi động trình duyệt để vào phòng Live TikTok...', 
            flags: [MessageFlags.Ephemeral] 
        });

        let browser;
        try {
            browser = await puppeteer.launch({
                headless: 'new',
                args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            });

            const page = await browser.newPage();
            await page.setViewport({ width: 1280, height: 800 });

            // Xử lý và nạp Cookie vào trình duyệt
            const cookies = cookieString.split(';').map(pair => {
                const parts = pair.trim().split('=');
                const name = parts[0];
                const value = parts.slice(1).join('=');
                if (!name || !value) return null;
                return {
                    name: name.trim(),
                    value: value.trim(),
                    domain: '.tiktok.com',
                    path: '/',
                    httpOnly: true,
                    secure: true,
                    sameSite: 'Lax'
                };
            }).filter(Boolean);

            await page.setCookie(...cookies);

            // Mở link phòng live
            console.log(`Đang truy cập vào: ${liveUrl}`);
            await page.goto(liveUrl, { waitUntil: 'networkidle2', timeout: 60000 });

            // Chờ khung chat xuất hiện (dùng nhiều selector dự phòng của TikTok)
            const chatSelector = 'textarea[data-e2e="chat-input"], div[contenteditable="true"], textarea';
            await page.waitForSelector(chatSelector, { timeout: 20000 });

            // Click vào ô chat, gõ nội dung và gửi
            await page.click(chatSelector);
            await page.type(chatSelector, messageText, { delay: 100 });
            await page.keyboard.press('Enter');

            await interaction.followUp({ content: `✅ Đã gửi tin nhắn thành công vào phòng live: "${messageText}"` });

        } catch (error) {
            console.error('Lỗi khi chạy Puppeteer:', error);
            await interaction.followUp({ content: `❌ Có lỗi xảy ra: ${error.message}` });
        } finally {
            if (browser) {
                await browser.close();
            }
        }
    }
});

client.login(process.env.DISCORD_TOKEN);
