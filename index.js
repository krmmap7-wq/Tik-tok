const { 
    Client, GatewayIntentBits, REST, Routes, 
    SlashCommandBuilder, EmbedBuilder, ModalBuilder, 
    TextInputBuilder, TextInputStyle, ActionRowBuilder 
} = require('discord.js');

const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
puppeteer.use(StealthPlugin());

const client = new Client({
    intents: [GatewayIntentBits.Guilds, GatewayIntentBits.DirectMessages]
});

const activeSessions = new Map();

const commands = [
    new SlashCommandBuilder()
        .setName('live')
        .setDescription('🚀 Khởi động bảng điều khiển TikTok Live Seeding PRO'),
    new SlashCommandBuilder()
        .setName('stop')
        .setDescription('🛑 Dừng tiến trình seeding và dọn dẹp hệ thống')
].map(cmd => cmd.toJSON());

client.once('ready', async () => {
    console.log(`🤖 BOT ONLINE: ${client.user.tag}`);
    const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);
    try {
        await rest.put(Routes.applicationCommands(process.env.CLIENT_ID), { body: commands });
        console.log('✅ Đã đăng ký thành công danh mục lệnh!');
    } catch (error) {
        console.error('❌ Lỗi đăng ký lệnh Slash:', error);
    }
});

client.on('interactionCreate', async interaction => {
    if (interaction.isChatInputCommand()) {
        if (interaction.commandName === 'live') {
            const modal = new ModalBuilder()
                .setCustomId('live_modal')
                .setTitle('⚡ TIKTOK LIVE SEEDING CONTROL PANEL');

            const cookieInput = new TextInputBuilder()
                .setCustomId('cookie_input')
                .setLabel('🍪 CHUỖI COOKIE TIKTOK')
                .setStyle(TextInputStyle.Paragraph)
                .setPlaceholder('Dán toàn bộ Cookie tại đây...')
                .setRequired(true);

            const urlInput = new TextInputBuilder()
                .setCustomId('url_input')
                .setLabel('🔗 LINK PHÒNG LIVESTREAM')
                .setStyle(TextInputStyle.Short)
                .setPlaceholder('https://www.tiktok.com/@username/live')
                .setRequired(true);

            const messageInput = new TextInputBuilder()
                .setCustomId('message_input')
                .setLabel('💬 NỘI DUNG TIN NHẮN SPAM')
                .setStyle(TextInputStyle.Short)
                .setPlaceholder('Nhập nội dung muốn gửi...')
                .setRequired(true);

            const delayInput = new TextInputBuilder()
                .setCustomId('delay_input')
                .setLabel('⏱️ THỜI GIAN DELAY NGHỈ (GIÂY)')
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

                const stopEmbed = new EmbedBuilder()
                    .setColor(0xFFA500)
                    .setTitle('⏳ ĐANG XỬ LÝ LỆNH DỪNG...')
                    .setDescription('```fix\nHệ thống đang ngắt trình duyệt và dọn dẹp bộ nhớ tạm...\n```')
                    .setTimestamp();

                await interaction.reply({ embeds: [stopEmbed], ephemeral: true });
            } else {
                const noSessionEmbed = new EmbedBuilder()
                    .setColor(0xFF4500)
                    .setTitle('⚠️ KHÔNG TÌM THẤY TIẾN TRÌNH')
                    .setDescription('Hiện tại bạn không có phiên seeding nào đang chạy.')
                    .setTimestamp();

                await interaction.reply({ embeds: [noSessionEmbed], ephemeral: true });
            }
        }
    } 
    else if (interaction.isModalSubmit()) {
        if (interaction.customId === 'live_modal') {
            const userId = interaction.user.id;
            
            if (activeSessions.has(userId)) {
                const existEmbed = new EmbedBuilder()
                    .setColor(0xFFCC00)
                    .setTitle('⚠️ TIẾN TRÌNH ĐANG CHẠY')
                    .setDescription('Bạn đang có một phiên seeding hoạt động! Hãy dùng `/stop` trước khi tạo phiên mới.')
                    .setTimestamp();

                return interaction.reply({ embeds: [existEmbed], ephemeral: true });
            }

            const cookieString = interaction.fields.getTextInputValue('cookie_input');
            const liveUrl = interaction.fields.getTextInputValue('url_input');
            const messageText = interaction.fields.getTextInputValue('message_input');
            const delaySec = Math.max(2, parseInt(interaction.fields.getTextInputValue('delay_input')) || 5);

            const initEmbed = new EmbedBuilder()
                .setColor(0x00BFFF)
                .setTitle('⚙️ KHỞI ĐỘNG HỆ THỐNG STEALTH PRO')
                .setDescription('```yaml\nĐang vượt tường lửa TikTok & nạp Cookie bảo mật...\n```')
                .setTimestamp();

            await interaction.reply({ embeds: [initEmbed], ephemeral: true });

            let browser;
            try {
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
                    const errCookieEmbed = new EmbedBuilder()
                        .setColor(0xFF0055)
                        .setTitle('❌ ĐỊNH DẠNG COOKIE SAI')
                        .setDescription('Mã Cookie bạn dán không hợp lệ. Vui lòng copy lại chính xác từ Stay.')
                        .setTimestamp();

                    return interaction.user.send({ embeds: [errCookieEmbed] }).catch(() => {});
                }

                await page.setCookie(...cookies);
                await page.setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Mobile/15E148 Safari/604.1');

                console.log(`[PRO SETUP] Mở link: ${liveUrl}`);
                await page.goto(liveUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
                await new Promise(r => setTimeout(r, 5000));

                const chatSelectors = [
                    'div[contenteditable="true"]',
                    'textarea[data-e2e="chat-input"]',
                    'input[placeholder*="Say something"]',
                    'input[placeholder*="Nói gì đó"]',
                    'textarea',
                    'input'
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
                    const errLoginEmbed = new EmbedBuilder()
                        .setColor(0xFF0055)
                        .setTitle('❌ LỖI KẾT NỐI PHÒNG LIVE')
                        .setDescription('Không mở được khung chat! Rất có thể:\n• Cookie đã bị hết hạn hoặc sai phiên.\n• TikTok yêu cầu xác minh Captcha hình ảnh.\n• Phòng Live bị khóa tính năng bình luận.')
                        .setTimestamp();

                    return interaction.user.send({ embeds: [errLoginEmbed] }).catch(() => {});
                }

                const dashboardEmbed = new EmbedBuilder()
                    .setColor(0x00FF66)
                    .setTitle('🚀 TIKTOK SEEDING DASHBOARD [ONLINE]')
                    .setDescription('```ansi\n\u001b[1;32m[STATUS] Đã kết nối thành công & đang chạy ngầm 24/24\u001b[0m\n```')
                    .addFields(
                        { name: '📌 Link Phòng Live', value: `[Bấm để mở phòng Live](${liveUrl})`, inline: false },
                        { name: '💬 Nội Dung Spam', value: `\`\`\`${messageText}\`\`\``, inline: false },
                        { name: '⏱️ Độ Trễ Gửi', value: `\`${delaySec} Giây / Tin\``, inline: true },
                        { name: '🛡️ Bảo Mật', value: '`Stealth Mode Active`', inline: true }
                    )
                    .setFooter({ text: 'Dùng lệnh /stop tại Discord để ngắt tiến trình.' })
                    .setTimestamp();

                await interaction.user.send({ embeds: [dashboardEmbed] }).catch(() => {});

                const session = { isStopped: false, messageCount: 0, startTime: Date.now() };
                activeSessions.set(userId, session);

                (async () => {
                    try {
                        while (!session.isStopped) {
                            try {
                                await page.click(targetSelector);
                                await page.type(targetSelector, messageText, { delay: 60 });
                                await page.keyboard.press('Enter');
                                session.messageCount++;
                            } catch (err) {
                                console.log('[RETRY] Thử lại ô chat...');
                            }
                            await new Promise(r => setTimeout(r, delaySec * 1000));
                        }
                    } finally {
                        if (browser) await browser.close();

                        const durationMinutes = Math.max(1, Math.round((Date.now() - session.startTime) / 60000));

                        const reportEmbed = new EmbedBuilder()
                            .setColor(0xFF0055)
                            .setTitle('🛑 BÁO CÁO TỔNG KẾT TIẾN TRÌNH')
                            .setDescription('```ansi\n\u001b[1;31m[STOPPED] Phiên làm việc đã ngắt & Cookie đã được xóa sạch.\u001b[0m\n```')
                            .addFields(
                                { name: '✉️ Tổng Số Tin Nhắn', value: `\`\`\`yaml\n${session.messageCount} Tin nhắn\n\`\`\``, inline: true },
                                { name: '⏱️ Thời Gian Chạy', value: `\`\`\`yaml\n${durationMinutes} Phút\n\`\`\``, inline: true }
                            )
                            .setFooter({ text: 'Dữ liệu cá nhân đã được dọn dẹp khỏi bộ nhớ tạm.' })
                            .setTimestamp();

                        await interaction.user.send({ embeds: [reportEmbed] }).catch(() => {});
                        activeSessions.delete(userId);
                    }
                })();

            } catch (error) {
                if (browser) await browser.close();
                console.error('[ERROR CRASH]:', error);

                const crashEmbed = new EmbedBuilder()
                    .setColor(0xFF0000)
                    .setTitle('💥 LỖI HỆ THỐNG UNHANDLED')
                    .setDescription(`\`\`\`js\n${error.message}\n\`\`\``)
                    .setTimestamp();

                await interaction.user.send({ embeds: [crashEmbed] }).catch(() => {});
            }
        }
    }
});

client.login(process.env.DISCORD_TOKEN);
