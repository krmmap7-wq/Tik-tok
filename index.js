const { 
    Client, GatewayIntentBits, REST, Routes, 
    SlashCommandBuilder, EmbedBuilder, ModalBuilder, 
    TextInputBuilder, TextInputStyle, ActionRowBuilder 
} = require('discord.js');

// Sử dụng puppeteer-extra kết hợp Stealth Plugin né anti-bot
const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
puppeteer.use(StealthPlugin());

const client = new Client({
    intents: [GatewayIntentBits.Guilds, GatewayIntentBits.DirectMessages]
});

// Map quản lý phiên chạy của từng User
const activeSessions = new Map();

// Đăng ký các lệnh Slash
const commands = [
    new SlashCommandBuilder()
        .setName('live')
        .setDescription('🚀 Khởi động công cụ Seeding TikTok Live Pro 24/24'),
    new SlashCommandBuilder()
        .setName('stop')
        .setDescription('🛑 Dừng tiến trình seeding và dọn dẹp hệ thống')
].map(cmd => cmd.toJSON());

client.once('ready', async () => {
    console.log(`🤖 Bot PRO đã sẵn sàng hoạt động 24/24: ${client.user.tag}`);
    const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);
    try {
        await rest.put(Routes.applicationCommands(process.env.CLIENT_ID), { body: commands });
        console.log('✅ Đã cập nhật thành công các lệnh Slash!');
    } catch (error) {
        console.error('Lỗi đăng ký lệnh:', error);
    }
});

client.on('interactionCreate', async interaction => {
    if (interaction.isChatInputCommand()) {
        if (interaction.commandName === 'live') {
            const modal = new ModalBuilder()
                .setCustomId('live_modal')
                .setTitle('⚙️ Cấu Hình TikTok Live Seeding PRO');

            const cookieInput = new TextInputBuilder()
                .setCustomId('cookie_input')
                .setLabel('Dán chuỗi Cookie TikTok')
                .setStyle(TextInputStyle.Paragraph)
                .setPlaceholder('session_id=...; ttwid=...;')
                .setRequired(true);

            const urlInput = new TextInputBuilder()
                .setCustomId('url_input')
                .setLabel('Link phòng Livestream TikTok')
                .setStyle(TextInputStyle.Short)
                .setPlaceholder('https://www.tiktok.com/@username/live')
                .setRequired(true);

            const messageInput = new TextInputBuilder()
                .setCustomId('message_input')
                .setLabel('Nội dung tin nhắn spam')
                .setStyle(TextInputStyle.Short)
                .setRequired(true);

            const delayInput = new TextInputBuilder()
                .setCustomId('delay_input')
                .setLabel('Thời gian chờ giữa các tin (giây)')
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
                await interaction.reply({ content: '🛑 Đã gửi tín hiệu dừng! Đang đóng trình duyệt và xóa dữ liệu...', ephemeral: true });
            } else {
                await interaction.reply({ content: '⚠️ Bạn không có tiến trình seeding nào đang chạy.', ephemeral: true });
            }
        }
    } 
    else if (interaction.isModalSubmit()) {
        if (interaction.customId === 'live_modal') {
            const userId = interaction.user.id;
            
            if (activeSessions.has(userId)) {
                return interaction.reply({ content: '⚠️ Bạn đang có một phiên seeding chạy rồi! Hãy dùng lệnh `/stop` trước.', ephemeral: true });
            }

            const cookieString = interaction.fields.getTextInputValue('cookie_input');
            const liveUrl = interaction.fields.getTextInputValue('url_input');
            const messageText = interaction.fields.getTextInputValue('message_input');
            const delaySec = Math.max(2, parseInt(interaction.fields.getTextInputValue('delay_input')) || 5);

            await interaction.reply({ content: '🔍 Đang kết nối trình duyệt ẩn danh (Stealth Mode) và truy cập phòng Live...', ephemeral: true });

            let browser;
            try {
                // Khởi tạo Puppeteer với chế độ Stealth chống phát hiện 100%
                browser = await puppeteer.launch({
                    headless: 'new',
                    args: [
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--no-first-run',
                        '--no-zygote',
                        '--disable-gpu',
                        '--window-size=1440,900'
                    ]
                });

                const page = await browser.newPage();
                await page.setViewport({ width: 1440, height: 900 });

                // Chuẩn hóa và parse danh sách Cookie
                const cookies = cookieString.split(';').map(pair => {
                    const idx = pair.indexOf('=');
                    if (idx === -1) return null;
                    const name = pair.substring(0, idx).trim();
                    const value = pair.substring(idx + 1).trim();
                    if (!name || !value) return null;
                    return {
                        name: name,
                        value: value,
                        domain: '.tiktok.com',
                        path: '/',
                        httpOnly: false,
                        secure: true,
                        sameSite: 'Lax'
                    };
                }).filter(Boolean);

                if (cookies.length === 0) {
                    await browser.close();
                    return interaction.user.send('❌ **LỖI:** Định dạng Cookie không hợp lệ! Vui lòng sao chép lại toàn bộ Cookie từ Stay.').catch(() => {});
                }

                await page.setCookie(...cookies);

                // Mở link phòng Live
                console.log(`[PRO] Đang truy cập: ${liveUrl}`);
                await page.goto(liveUrl, { waitUntil: 'networkidle2', timeout: 60000 });

                // Giả lập thao tác cuộn nhẹ trang để kích hoạt giao diện
                await new Promise(r => setTimeout(r, 4000));
                await page.evaluate(() => window.scrollBy(0, 150));

                // Danh sách Selector khung chat đa dạng của TikTok
                const chatSelectors = [
                    'div[contenteditable="true"]',
                    'textarea[data-e2e="chat-input"]',
                    'div[placeholder*="Say something"]',
                    'div[placeholder*="Nói gì đó"]',
                    'textarea'
                ];

                let targetSelector = null;
                for (const selector of chatSelectors) {
                    try {
                        await page.waitForSelector(selector, { timeout: 5000 });
                        targetSelector = selector;
                        break;
                    } catch (e) {
                        continue;
                    }
                }

                if (!targetSelector) {
                    await browser.close();
                    return interaction.user.send('❌ **LỖI ĐĂNG NHẬP:** Không tìm thấy khung chat! Cookie có thể đã hết hạn, tài khoản bị hạn chế hoặc phòng Live này chặn comment.').catch(() => {});
                }

                // Gửi Embed xác nhận kết nối thành công về DM
                const successEmbed = new EmbedBuilder()
                    .setColor(0x28A745)
                    .setTitle('🚀 KẾT NỐI & SEEDING THÀNH CÔNG (PRO)')
                    .setDescription('Trình duyệt Stealth đã vượt qua lớp kiểm tra bảo mật và bắt đầu gửi tin nhắn.')
                    .addFields(
                        { name: '🔗 Link Live', value: liveUrl },
                        { name: '💬 Nội dung', value: messageText },
                        { name: '⏱️ Độ trễ', value: `${delaySec} giây/tin` }
                    )
                    .setFooter({ text: 'Dùng lệnh /stop tại kênh chat để dừng tiến trình.' })
                    .setTimestamp();

                await interaction.user.send({ embeds: [successEmbed] }).catch(() => {});

                // Khởi tạo phiên chạy
                const session = { isStopped: false, messageCount: 0, startTime: Date.now() };
                activeSessions.set(userId, session);

                // Vòng lặp gửi tin nhắn
                (async () => {
                    try {
                        while (!session.isStopped) {
                            try {
                                await page.click(targetSelector);
                                // Gõ từ từ giống người thật
                                await page.type(targetSelector, messageText, { delay: 70 });
                                await page.keyboard.press('Enter');
                                session.messageCount++;
                            } catch (err) {
                                console.log('[PRO] Thử lại thao tác gõ chat...', err.message);
                            }
                            await new Promise(r => setTimeout(r, delaySec * 1000));
                        }
                    } finally {
                        // Tự động đóng trình duyệt & giải phóng bộ nhớ
                        if (browser) await browser.close();

                        const durationMinutes = Math.max(1, Math.round((Date.now() - session.startTime) / 60000));

                        const stopEmbed = new EmbedBuilder()
                            .setColor(0xDC3545)
                            .setTitle('🛑 BÁO CÁO TỔNG KẾT TIẾN TRÌNH')
                            .setDescription('Tiến trình đã kết thúc an toàn. Toàn bộ thông tin phiên làm việc và Cookie đã được xóa hoàn toàn khỏi bộ nhớ tạm.')
                            .addFields(
                                { name: '✉️ Tổng tin nhắn đã gửi', value: `${session.messageCount} tin`, inline: true },
                                { name: '⏱️ Thời gian hoạt động', value: `${durationMinutes} phút`, inline: true }
                            )
                            .setTimestamp();

                        await interaction.user.send({ embeds: [stopEmbed] }).catch(() => {});
                        activeSessions.delete(userId);
                    }
                })();

            } catch (error) {
                if (browser) await browser.close();
                console.error('[PRO ERROR]:', error);
                await interaction.user.send(`❌ **LỖI HỆ THỐNG:** ${error.message}`).catch(() => {});
            }
        }
    }
});

client.login(process.env.DISCORD_TOKEN);
