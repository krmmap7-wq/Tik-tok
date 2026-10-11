const { 
    Client, GatewayIntentBits, REST, Routes, 
    SlashCommandBuilder, EmbedBuilder, ModalBuilder, 
    TextInputBuilder, TextInputStyle, ActionRowBuilder 
} = require('discord.js');
const puppeteer = require('puppeteer');

const client = new Client({
    intents: [GatewayIntentBits.Guilds, GatewayIntentBits.DirectMessages]
});

// Lưu trữ các tiến trình spam đang chạy theo userId
const activeSessions = new Map();

// Đăng ký lệnh Slash
const commands = [
    new SlashCommandBuilder()
        .setName('live')
        .setDescription('🚀 Khởi động công cụ Seeding TikTok Live 24/24'),
    new SlashCommandBuilder()
        .setName('stop')
        .setDescription('🛑 Dừng ngay tiến trình seeding đang chạy')
].map(cmd => cmd.toJSON());

client.once('ready', async () => {
    console.log(`🤖 Bot đã sẵn sàng hoạt động 24/24: ${client.user.tag}`);
    const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);
    try {
        await rest.put(Routes.applicationCommands(process.env.CLIENT_ID), { body: commands });
        console.log('✅ Đã đăng ký lệnh thành công!');
    } catch (error) {
        console.error(error);
    }
});

// Xử lý sự kiện lệnh Slash và Modal
client.on('interactionCreate', async interaction => {
    if (interaction.isChatInputCommand()) {
        if (interaction.commandName === 'live') {
            // Hiển thị bảng Modal điền thông tin (Bảo mật, không lộ chat chung)
            const modal = new ModalBuilder()
                .setCustomId('live_modal')
                .setTitle('⚙️ Cấu Hình TikTok Seeding Live');

            const cookieInput = new TextInputBuilder()
                .setCustomId('cookie_input')
                .setLabel('Dán chuỗi Cookie TikTok của bạn')
                .setStyle(TextInputStyle.Paragraph)
                .setRequired(true);

            const urlInput = new TextInputBuilder()
                .setCustomId('url_input')
                .setLabel('Link phòng Livestream TikTok')
                .setStyle(TextInputStyle.Short)
                .setRequired(true);

            const messageInput = new TextInputBuilder()
                .setCustomId('message_input')
                .setLabel('Nội dung tin nhắn spam')
                .setStyle(TextInputStyle.Short)
                .setRequired(true);

            const delayInput = new TextInputBuilder()
                .setCustomId('delay_input')
                .setLabel('Thời gian chờ giữa các lần gửi (giây)')
                .setValue('5')
                .setStyle(TextInputStyle.Short)
                .setRequired(true);

            modal.addComponents(
                new ActionRowBuilder().addComponents(cookieInput),
                new ActionRowBuilder().addComponents(urlInput),
                new ActionRowBuilder().addComponents(messageInput),
                new ActionRowBuilder().addComponents(delayInput)
            );

            await interaction.showModal(modal);
        } 
        else if (interaction.commandName === 'stop') {
            const userId = interaction.user.id;
            if (activeSessions.has(userId)) {
                const session = activeSessions.get(userId);
                session.isStopped = true;
                await interaction.reply({ content: '🛑 Đã nhận lệnh dừng! Đang tiến hành dọn dẹp hệ thống...', ephemeral: true });
            } else {
                await interaction.reply({ content: '⚠️ Bạn không có tiến trình seeding nào đang chạy.', ephemeral: true });
            }
        }
    } 
    else if (interaction.isModalSubmit()) {
        if (interaction.customId === 'live_modal') {
            const userId = interaction.user.id;
            
            if (activeSessions.has(userId)) {
                return interaction.reply({ content: '⚠️ Bạn đang có một tiến trình chạy rồi! Hãy dùng lệnh `/stop` trước.', ephemeral: true });
            }

            const cookieString = interaction.fields.getTextInputValue('cookie_input');
            const liveUrl = interaction.fields.getTextInputValue('url_input');
            const messageText = interaction.fields.getTextInputValue('message_input');
            const delaySec = parseInt(interaction.fields.getTextInputValue('delay_input')) || 5;

            // Phản hồi ẩn xác nhận đã nhận lệnh
            await interaction.reply({ content: '🔍 Hệ thống đang kiểm tra Cookie và khởi động trình duyệt...', ephemeral: true });

            let browser;
            try {
                browser = await puppeteer.launch({
                    headless: 'new',
                    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled']
                });

                const page = await browser.newPage();
                await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36');
                await page.setViewport({ width: 1280, height: 800 });

                // Nạp Cookie
                const cookies = cookieString.split(';').map(pair => {
                    const parts = pair.trim().split('=');
                    const name = parts[0];
                    const value = parts.slice(1).join('=');
                    if (!name || !value) return null;
                    return { name: name.trim(), value: value.trim(), domain: '.tiktok.com', path: '/', httpOnly: true, secure: true, sameSite: 'Lax' };
                }).filter(Boolean);

                await page.setCookie(...cookies);

                // Kiểm tra đăng nhập bằng cách truy cập trang cá nhân hoặc TikTok chính
                await page.goto('https://www.tiktok.com', { waitUntil: 'domcontentloaded', timeout: 40000 });
                await new Promise(r => setTimeout(r, 4000));

                // Check xem cookie có hợp lệ không (tìm nút đăng nhập hoặc profile)
                const isLoggedOut = await page.$('button[data-e2e="top-login-button"]');
                if (isLoggedOut) {
                    await browser.close();
                    return interaction.user.send('❌ **LỖI:** Cookie TikTok của bạn không hợp lệ hoặc đã hết hạn! Vui lòng lấy lại cookie mới.').catch(() => {});
                }

                // Truy cập phòng Live
                await page.goto(liveUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
                await new Promise(r => setTimeout(r, 5000));

                const chatSelector = 'div[contenteditable="true"], textarea[data-e2e="chat-input"]';
                await page.waitForSelector(chatSelector, { timeout: 20000 });

                // Gửi thông báo thành công qua DM (Bảo mật tuyệt đối)
                const successEmbed = new EmbedBuilder()
                    .setColor(0x00FF00)
                    .setTitle('🚀 ĐĂNG NHẬP & SEEDING THÀNH CÔNG')
                    .setDescription('Hệ thống đã kết nối thành công vào phòng Livestream và bắt đầu gửi tin nhắn.')
                    .addFields(
                        { name: '🔗 Link Live', value: liveUrl },
                        { name: '💬 Nội dung', value: messageText },
                        { name: '⏱️ Tốc độ', value: `${delaySec} giây/tin nhắn` }
                    )
                    .setTimestamp();
                
                await interaction.user.send({ embeds: [successEmbed] }).catch(() => {});

                // Thiết lập phiên chạy
                const session = { isStopped: false, messageCount: 0, startTime: Date.now() };
                activeSessions.set(userId, session);

                // Vòng lặp spam chạy ngầm
                (async () => {
                    try {
                        while (!session.isStopped) {
                            try {
                                await page.click(chatSelector);
                                await page.type(chatSelector, messageText, { delay: 50 });
                                await page.keyboard.press('Enter');
                                session.messageCount++;
                            } catch (err) {
                                console.log('Lỗi gõ khung chat, đang thử lại...', err);
                            }
                            await new Promise(r => setTimeout(r, delaySec * 1000));
                        }
                    } finally {
                        // Dọn dẹp sạch sẽ
                        if (browser) await browser.close();
                        
                        const durationMinutes = Math.floor((Date.now() - session.startTime) / 60000);
                        
                        const stopEmbed = new EmbedBuilder()
                            .setColor(0xFF0000)
                            .setTitle('🛑 TỔNG KẾT TIẾN TRÌNH SEEDING')
                            .setDescription('Tiến trình đã dừng và toàn bộ dữ liệu/cookie đã được xóa khỏi hệ thống.')
                            .addFields(
                                { name: '✉️ Tổng tin nhắn đã gửi', value: `${session.messageCount} tin`, inline: true },
                                { name: '⏱️ Tổng thời gian chạy', value: `${durationMinutes} phút`, inline: true }
                            )
                            .setTimestamp();

                        await interaction.user.send({ embeds: [stopEmbed] }).catch(() => {});
                        activeSessions.delete(userId);
                    }
                })();

            } catch (error) {
                if (browser) await browser.close();
                await interaction.user.send(`❌ **LỖI HỆ THỐNG:** ${error.message}`).catch(() => {});
            }
        }
    }
});

client.login(process.env.DISCORD_TOKEN);
