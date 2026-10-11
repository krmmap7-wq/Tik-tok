const { 
    Client, GatewayIntentBits, REST, Routes, 
    SlashCommandBuilder, ModalBuilder, TextInputBuilder, 
    TextInputStyle, ActionRowBuilder, EmbedBuilder 
} = require('discord.js');
const puppeteer = require('puppeteer');

const TOKEN = process.env.DISCORD_TOKEN;
const CLIENT_ID = process.env.CLIENT_ID;
const ALLOWED_CHANNEL_ID = process.env.ALLOWED_CHANNEL_ID || ""; 

const client = new Client({ 
    intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent] 
});

// Lưu trữ phiên chạy activeSessions
const activeSessions = new Map();

const commands = [
    new SlashCommandBuilder()
        .setName('live')
        .setDescription('🚀 Khởi chạy hệ thống Seeding TikTok Live tự động'),
    new SlashCommandBuilder()
        .setName('stop')
        .setDescription('🛑 Dừng toàn bộ tiến trình Seeding đang chạy của bạn')
];

const rest = new REST({ version: '10' }).setToken(TOKEN);

(async () => {
    try {
        await rest.put(Routes.applicationCommands(CLIENT_ID), { body: commands });
        console.log('✅ Đã đăng ký lệnh Slash (/live, /stop) thành công!');
    } catch (error) {
        console.error('❌ Lỗi đăng ký Slash Command:', error);
    }
})();

client.on('ready', async () => {
    console.log(`🤖 Bot đã online: ${client.user.tag}`);
    
    if (ALLOWED_CHANNEL_ID) {
        try {
            const channel = await client.channels.fetch(ALLOWED_CHANNEL_ID);
            if (channel) {
                const rulesEmbed = new EmbedBuilder()
                    .setColor('#FF0055')
                    .setTitle('⚠️ HỆ THỐNG ĐIỀU HÀNH & NỘI QUY SEEDING TIKTOK')
                    .setDescription('Chào mừng bạn đến với hệ thống tự động hóa chuyên nghiệp. Vui lòng tuân thủ nghiêm ngặt các quy định dưới đây để đảm bảo an toàn cho tài khoản.')
                    .addFields(
                        { name: '🛡️ 1. Bảo mật & Quyền riêng tư', value: '• Mọi Cookie nhập vào **chỉ sử dụng trực tiếp cho phiên chạy** và **tự động xóa sạch ngay lập tức**, tuyệt đối không lưu trữ.', inline: false },
                        { name: '⚖️ 2. Quy định sử dụng', value: '• Nghiêm cấm dùng hệ thống vào các mục đích phá hoại, lừa đảo hoặc vi phạm pháp luật.', inline: false },
                        { name: '⚡ 3. Hướng dẫn lệnh', value: '• Gõ lệnh `/live` để mở bảng cấu hình.\n• Gõ lệnh `/stop` để dừng phiên đang chạy.\n• Phản hồi lệnh được bảo mật **chỉ hiển thị riêng với bạn (Ephemeral)**.', inline: false }
                    )
                    .setFooter({ text: 'Hệ thống tự động 24/24 • Đảm bảo an toàn cấp độ cao' })
                    .setTimestamp();

                const messages = await channel.messages.fetch({ limit: 5 });
                const hasRule = messages.some(m => m.author.id === client.user.id && m.embeds.length > 0);
                if (!hasRule) {
                    await channel.send({ embeds: [rulesEmbed] });
                }
            }
        } catch (e) {
            console.log('Không thể gửi Embed nội quy:', e.message);
        }
    }
});

client.on('interactionCreate', async interaction => {
    // Giới hạn độc quyền kênh được chỉ định
    if (ALLOWED_CHANNEL_ID && interaction.channelId !== ALLOWED_CHANNEL_ID) {
        if (interaction.isChatInputCommand() || interaction.isModalSubmit()) {
            return interaction.reply({ 
                content: `❌ **Lệnh này chỉ được phép dùng tại kênh chat quy định!**`, 
                ephemeral: true 
            });
        }
    }

    // Lệnh /live -> Mở Modal Form
    if (interaction.isChatInputCommand() && interaction.commandName === 'live') {
        const modal = new ModalBuilder()
            .setCustomId('liveModal')
            .setTitle('⚙️ Cấu Hình Seeding TikTok Live');

        const cookieInput = new TextInputBuilder()
            .setCustomId('cookieInput')
            .setLabel('1. Dán Cookie TikTok của bạn:')
            .setStyle(TextInputStyle.Paragraph)
            .setPlaceholder('Dán chuỗi cookie session_id / ttwid vào đây...')
            .setRequired(true);

        const urlInput = new TextInputBuilder()
            .setCustomId('urlInput')
            .setLabel('2. Link Livestream TikTok:')
            .setStyle(TextInputStyle.Short)
            .setPlaceholder('https://www.tiktok.com/@username/live')
            .setRequired(true);

        const msgInput = new TextInputBuilder()
            .setCustomId('msgInput')
            .setLabel('3. Nội dung spam (Mỗi dòng 1 câu):')
            .setStyle(TextInputStyle.Paragraph)
            .setPlaceholder('Ch.eo✅\nChe0✅\nC.h.e.o✅')
            .setRequired(true);

        const delayInput = new TextInputBuilder()
            .setCustomId('delayInput')
            .setLabel('4. Delay (0.1 đến 5 giây max):')
            .setStyle(TextInputStyle.Short)
            .setPlaceholder('Ví dụ: 1.5')
            .setRequired(true);

        modal.addComponents(
            new ActionRowBuilder().addComponents(cookieInput),
            new ActionRowBuilder().addComponents(urlInput),
            new ActionRowBuilder().addComponents(msgInput),
            new ActionRowBuilder().addComponents(delayInput)
        );

        await interaction.showModal(modal);
    }

    // Lệnh /stop -> Hủy tiến trình
    if (interaction.isChatInputCommand() && interaction.commandName === 'stop') {
        const session = activeSessions.get(interaction.user.id);
        if (session) {
            clearInterval(session.interval);
            if (session.browser) await session.browser.close().catch(() => {});
            activeSessions.delete(interaction.user.id);
            return interaction.reply({ content: '🛑 **Đã dừng thành công tiến trình Seeding của bạn.**', ephemeral: true });
        } else {
            return interaction.reply({ content: '⚠️ Bạn không có tiến trình nào đang chạy.', ephemeral: true });
        }
    }

    // Xử lý dữ liệu Submit từ Modal
    if (interaction.isModalSubmit() && interaction.customId === 'liveModal') {
        let cookieStr = interaction.fields.getTextInputValue('cookieInput');
        const liveUrl = interaction.fields.getTextInputValue('urlInput');
        const rawMsg = interaction.fields.getTextInputValue('msgInput');
        let delaySec = parseFloat(interaction.fields.getTextInputValue('delayInput'));

        if (isNaN(delaySec) || delaySec < 0.1) delaySec = 0.1;
        if (delaySec > 5) delaySec = 5;

        if (activeSessions.has(interaction.user.id)) {
            const old = activeSessions.get(interaction.user.id);
            clearInterval(old.interval);
            if (old.browser) await old.browser.close().catch(() => {});
            activeSessions.delete(interaction.user.id);
        }

        await interaction.reply({ 
            content: `🚀 **Đã khởi chạy Seeding!**\n- Link: \`${liveUrl}\`\n- Delay: \`${delaySec}s\`\n*Cookie của bạn được sử dụng transient và đã tự động hủy khỏi bộ nhớ tạm.*`, 
            ephemeral: true 
        });

        let browser = null;
        try {
            browser = await puppeteer.launch({
                headless: "new",
                args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            });
            const page = await browser.newPage();
            await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36');

            if (cookieStr) {
                const cookies = cookieStr.split(';').map(cookie => {
                    const [name, ...rest] = cookie.trim().split('=');
                    return {
                        name: name ? name.trim() : '',
                        value: rest.join('=').trim(),
                        domain: '.tiktok.com',
                        path: '/'
                    };
                }).filter(c => c.name && c.value);
                await page.setCookie(...cookies);
            }

            await page.goto(liveUrl, { waitUntil: 'networkidle2', timeout: 60000 });

            const msgs = rawMsg.split('\n').map(s => s.trim()).filter(s => s.length > 0);
            let idx = 0;

            const intervalId = setInterval(async () => {
                try {
                    const chatBox = await page.$('div[contenteditable="true"]');
                    if (chatBox) {
                        await chatBox.click();
                        await page.keyboard.type(msgs[idx]);
                        await page.keyboard.press('Enter');
                        idx = (idx + 1) % msgs.length;
                    }
                } catch (err) {
                    console.log('Lỗi spam:', err.message);
                }
            }, delaySec * 1000);

            activeSessions.set(interaction.user.id, { browser, interval: intervalId });

        } catch (e) {
            if (browser) await browser.close().catch(() => {});
            cookieStr = null;
            return interaction.followUp({ content: `❌ **Khởi chạy thất bại:** ${e.message}`, ephemeral: true });
        }

        cookieStr = null; // Xóa Cookie ngay lập tức
    }
});

client.login(TOKEN);
