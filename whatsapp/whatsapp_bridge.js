// ============================================================
//  ALTROS WhatsApp Bridge
//  Talks to real WhatsApp via whatsapp-web.js, exposes a small
//  REST API on :8001 for modules/whatsapp.py.
//
//  npm install whatsapp-web.js qrcode-terminal express
//  node whatsapp_bridge.js
//  Scan the QR code once -- session persists in ./wa_session
//  (LocalAuth), no re-scan needed on restart.
//
//  SECURITY: bound to 127.0.0.1 only, not 0.0.0.0. Without this,
//  anyone else on your Wi-Fi could hit /send and message people
//  as you, or pull your contacts/chats -- there's no auth on
//  these routes, so "not reachable from outside this PC" is the
//  only thing protecting them. Don't change the host below.
// ============================================================

const express = require('express');
const qrcode = require('qrcode-terminal');
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');

const PORT = 8001;
const HOST = '127.0.0.1';

const app = express();
app.use(express.json());

const client = new Client({
    authStrategy: new LocalAuth({ dataPath: './wa_session' }),
    puppeteer: { headless: true, args: ['--no-sandbox', '--disable-setuid-sandbox'] }
});

let isReady = false;

client.on('qr', qr => {
    console.log('Scan this with WhatsApp -> Settings -> Linked Devices:');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    isReady = true;
    console.log('\u2705 WhatsApp bridge ready.');
});

client.on('auth_failure', msg => console.error('Auth failure:', msg));
client.on('disconnected', reason => {
    isReady = false;
    console.error('WhatsApp disconnected:', reason);
});

client.initialize();

function requireReady(req, res, next) {
    if (!isReady) return res.status(503).json({ error: 'client not ready yet -- scan the QR code or wait for startup' });
    next();
}

// ---- status -------------------------------------------------------
app.get('/status', (req, res) => {
    res.json({ status: isReady ? 'ready' : 'starting' });
});

// ---- send a text message -------------------------------------------
app.post('/send', requireReady, async (req, res) => {
    try {
        const { number, message } = req.body;
        if (!number || !message) return res.status(400).json({ error: 'number and message required' });
        await client.sendMessage(number, message);
        res.json({ ok: true });
    } catch (e) {
        res.status(500).json({ error: String(e) });
    }
});

// ---- send a file/photo with optional caption --------------------------
app.post('/send-file', requireReady, async (req, res) => {
    try {
        const { number, filepath, caption } = req.body;
        if (!number || !filepath) return res.status(400).json({ error: 'number and filepath required' });
        const media = MessageMedia.fromFilePath(filepath);
        await client.sendMessage(number, media, { caption: caption || '' });
        res.json({ ok: true });
    } catch (e) {
        res.status(500).json({ error: String(e) });
    }
});

// ---- contacts (named, non-group only) ------------------------------
app.get('/contacts', requireReady, async (req, res) => {
    try {
        const contacts = await client.getContacts();
        const named = contacts
            .filter(c => c.isMyContact && (c.name || c.pushname) && !c.isGroup)
            .map(c => ({ name: c.name || c.pushname, number: (c.number || '').replace(/\D/g, '') }))
            .filter(c => c.number)
            .slice(0, 300);
        res.json({ contacts: named });
    } catch (e) {
        res.status(500).json({ error: String(e) });
    }
});

// ---- NEW: recent messages from one chat -----------------------------
app.get('/messages', requireReady, async (req, res) => {
    try {
        const number = req.query.number;
        const limit = parseInt(req.query.limit || '10', 10);
        if (!number) return res.status(400).json({ error: 'number required, e.g. 919876543210@c.us' });
        const chat = await client.getChatById(number);
        const msgs = await chat.fetchMessages({ limit });
        res.json({
            messages: msgs.map(m => ({
                body: m.body,
                fromMe: m.fromMe,
                timestamp: m.timestamp
            }))
        });
    } catch (e) {
        res.status(500).json({ error: String(e) });
    }
});

// ---- NEW: chats with unread messages, for the "summary" feature --------
app.get('/unread', requireReady, async (req, res) => {
    try {
        const chats = await client.getChats();
        const unread = chats
            .filter(c => c.unreadCount > 0 && !c.isGroup)
            .map(c => ({
                name: c.name || c.id.user,
                number: c.id.user,
                unreadCount: c.unreadCount,
                lastMessage: c.lastMessage ? c.lastMessage.body : ''
            }))
            .slice(0, 20);
        res.json({ chats: unread });
    } catch (e) {
        res.status(500).json({ error: String(e) });
    }
});

app.listen(PORT, HOST, () => console.log(`WhatsApp bridge listening on http://${HOST}:${PORT}`));
