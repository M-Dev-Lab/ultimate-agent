const express = require('express');
const { WebSocketServer } = require('ws');
const RealQwenClient = require('./qwen-client');
const WhatsAppBot = require('./whatsapp-bot');
require('dotenv').config();

// Logging utility
const logger = {
  info: (message, data = {}) => {
    console.log(`[INFO] ${new Date().toISOString()} - ${message}`, data);
  },
  error: (message, error = {}) => {
    console.error(`[ERROR] ${new Date().toISOString()} - ${message}`, error);
  },
  warn: (message, data = {}) => {
    console.warn(`[WARN] ${new Date().toISOString()} - ${message}`, data);
  }
};

const app = express();
const port = parseInt(process.env.PORT || '3000');
const host = process.env.HOST || 'localhost';

const qwenClient = new RealQwenClient();
const messageStorage = [];
const whatsappBot = new WhatsAppBot();

// Message persistence utilities
const saveMessagesToFile = () => {
  try {
    const fs = require('fs');
    const path = require('path');
    const dataPath = path.join(__dirname, '..', 'data');
    
    if (!fs.existsSync(dataPath)) {
      fs.mkdirSync(dataPath, { recursive: true });
    }
    
    const filePath = path.join(dataPath, 'messages.json');
    fs.writeFileSync(filePath, JSON.stringify(messageStorage, null, 2));
    logger.info('Messages saved to file', { count: messageStorage.length });
  } catch (error) {
    logger.error('Failed to save messages to file', error);
  }
};

const loadMessagesFromFile = () => {
  try {
    const fs = require('fs');
    const path = require('path');
    const filePath = path.join(__dirname, '..', 'data', 'messages.json');
    
    if (fs.existsSync(filePath)) {
      const data = fs.readFileSync(filePath, 'utf8');
      const messages = JSON.parse(data);
      messageStorage.push(...messages);
      logger.info('Messages loaded from file', { count: messages.length });
    }
  } catch (error) {
    logger.error('Failed to load messages from file', error);
  }
};

// Load existing messages on startup
loadMessagesFromFile();

// WhatsApp admin check - only allow admin number
const isAdmin = (req, res, next) => {
  // Skip admin check for non-sensitive routes
  const publicRoutes = ['/health', '/auth/login', '/'];
  if (publicRoutes.includes(req.path)) {
    return next();
  }

  // Check for admin WhatsApp number in request body/headers
  const adminNumber = process.env.ADMIN_WHATSAPP_NUMBER || '+1234567890';
  const fromNumber = req.body.fromNumber || req.headers['x-whatsapp-number'];
  
  if (fromNumber !== adminNumber) {
    logger.warn('Unauthorized WhatsApp number attempt', { fromNumber, ip: req.ip });
    return res.status(403).json({ error: 'Access denied - admin only' });
  }

  next();
};

// Middleware - Order matters!
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization, X-WhatsApp-Number');
  
  // Set permissive CSP for development - adjust for production
  res.header('Content-Security-Policy', 
    "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob:; " +
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://cdn.tailwindcss.com data: blob:; " +
    "style-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.tailwindcss.com https://cdnjs.cloudflare.com; " +
    "img-src 'self' data: blob: https:; " +
    "font-src 'self' data: https://cdnjs.cloudflare.com; " +
    "connect-src 'self' ws: wss: http: https:;"
  );
  
  next();
});

app.use(express.json());
app.use(express.static('public'));

// Root route - serve main dashboard
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'index.html'));
});

// Health check
app.get('/health', (req, res) => {
  try {
    const healthData = {
      status: 'healthy',
      mode: 'production-qwen-simple',
      version: '2.0.0',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      qwen: qwenClient.getStats(),
      message: 'Ultimate Agent + Qwen Simple Demo Ready'
    };
    logger.info('Health check accessed', { ip: req.ip });
    res.json(healthData);
  } catch (error) {
    logger.error('Health check failed', error);
    res.status(500).json({ status: 'unhealthy', error: error.message });
  }
});

// QR code endpoint - show QR for first use
app.get('/qr', (req, res) => {
  try {
    logger.info('QR endpoint requested', {
      isConnected: whatsappBot.isConnected,
      isReady: whatsappBot.isReady,
      hasQR: !!whatsappBot.currentQR,
      hasError: !!whatsappBot.connectionError
    });

    // Check if WhatsApp is already connected
    if (whatsappBot.isConnected) {
      return res.json({
        connected: true,
        isReady: true,
        message: 'WhatsApp already connected'
      });
    }

    // Get QR code from WhatsApp bot
    const qrData = whatsappBot.getQRCode();

    // Return connection status
    if (qrData.isConnected) {
      return res.json({
        connected: true,
        isReady: true,
        message: 'WhatsApp already connected'
      });
    }

    // Check if there's an error
    if (qrData.error) {
      return res.status(500).json({
        connected: false,
        isReady: false,
        error: qrData.error,
        message: 'WhatsApp connection error: ' + qrData.error
      });
    }

    // Check if QR is ready
    if (qrData.isReady && qrData.qr) {
      res.json({
        connected: false,
        isReady: true,
        qrCode: qrData.qr,
        message: 'Scan this QR code with WhatsApp'
      });
    } else {
      // QR code not ready yet
      res.status(503).json({
        connected: false,
        isReady: false,
        error: 'QR code not available. WhatsApp may be starting...',
        message: 'QR code not ready yet. Please wait a moment...'
      });
    }
  } catch (error) {
    logger.error('QR code endpoint error', error);
    res.status(500).json({
      connected: false,
      isReady: false,
      error: error.message,
      message: 'Failed to get QR code'
    });
  }
});

// Debug endpoint to check WhatsApp bot status
app.get('/debug/whatsapp', (req, res) => {
  try {
    const debugInfo = {
      isConnected: whatsappBot.isConnected,
      isReady: whatsappBot.isReady,
      hasQR: !!whatsappBot.currentQR,
      hasError: !!whatsappBot.connectionError,
      error: whatsappBot.connectionError ? whatsappBot.connectionError.message : null,
      hasSocket: !!whatsappBot.sock,
      authDirExists: require('fs').existsSync(whatsappBot.authDir),
      timestamp: new Date().toISOString()
    };

    logger.info('WhatsApp debug info requested', debugInfo);
    res.json(debugInfo);
  } catch (error) {
    logger.error('Debug endpoint error', error);
    res.status(500).json({ error: error.message });
  }
});

// Open Qwen API endpoint - no password required for local use
app.post('/api/qwen/request', async (req, res) => {
  const requestId = Date.now().toString();
  try {
    const { prompt } = req.body;
    
    if (!prompt) {
      logger.warn('Invalid Qwen request - missing prompt', { requestId });
      return res.status(400).json({ error: 'Prompt is required' });
    }

    logger.info('Qwen request received', { requestId, promptLength: prompt.length });

    const response = await qwenClient.chat(prompt);
    
    // Store message
    const message = {
      id: requestId,
      type: 'qwen',
      content: response,
      timestamp: new Date().toISOString(),
      model: qwenClient.model
    };
    
    messageStorage.push(message);
    
    // Save messages to file for persistence
    saveMessagesToFile();

    logger.info('Qwen request completed', { requestId, responseLength: response.length });

    res.json({
      status: 'processed',
      response,
      model: qwenClient.model,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    logger.error('Qwen request failed', { requestId, error: error.message, stack: error.stack });
    res.status(500).json({ 
      error: error.message,
      requestId,
      timestamp: new Date().toISOString()
    });
  }
});

// Open messages endpoint - local access
app.get('/messages', (req, res) => {
  try {
    const { limit = 50, offset = 0 } = req.query;
    const startIndex = parseInt(offset);
    const endIndex = startIndex + parseInt(limit);
    
    const paginatedMessages = messageStorage.slice(startIndex, endIndex);
    
    logger.info('Messages requested', { 
      total: messageStorage.length, 
      returned: paginatedMessages.length,
      offset: startIndex,
      limit: parseInt(limit)
    });
    
    res.json({
      messages: paginatedMessages,
      total: messageStorage.length,
      offset: startIndex,
      limit: parseInt(limit),
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    logger.error('Messages endpoint failed', error);
    res.status(500).json({ error: error.message });
  }
});

// Clear messages endpoint
app.delete('/messages', (req, res) => {
  try {
    const clearedCount = messageStorage.length;
    messageStorage.length = 0;
    saveMessagesToFile();
    
    logger.info('Messages cleared', { clearedCount });
    res.json({
      success: true,
      message: `${clearedCount} messages cleared`,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    logger.error('Failed to clear messages', error);
    res.status(500).json({ error: error.message });
  }
});

// Start server
const server = app.listen(port, host, () => {
    logger.info('Server starting', { port, host });
    console.log(`🚀 Ultimate Agent + Qwen running on http://${host}:${port}`);
    console.log(`🧠 AI Engine: Qwen3-Coder-Plus`);
    console.log(`📊 Daily Limit: 2,000 free requests`);
    console.log(`🌐 Web UI: http://${host}:${port}`);
    console.log(`📱 WhatsApp Bot: Starting...`);
    
    // Start WhatsApp bot
    whatsappBot.start().then(() => {
        logger.info('WhatsApp bot started successfully');
        console.log(`🎉 Ultimate Agent ready!`);
        console.log(`💬 WhatsApp: Send messages to your bot`);
        console.log(`🌐 Web UI: http://${host}:${port}`);
    }).catch(error => {
        logger.error('WhatsApp bot failed to start', { error: error.message, stack: error.stack });
        console.error(`❌ WhatsApp bot failed:`, error.message);
    });
});

// Handle server errors
server.on('error', (error) => {
  if (error.code === 'EADDRINUSE') {
    logger.error(`Port ${port} already in use`);
    console.error(`❌ Port ${port} is already in use. Please choose a different port.`);
  } else {
    logger.error('Server error', error);
    console.error('❌ Server error:', error.message);
  }
  process.exit(1);
});

// WebSocket for real-time updates
const wss = new WebSocketServer({ server });

wss.on('connection', (ws) => {
  const clientId = Date.now().toString();
  logger.info('WebSocket client connected', { clientId });
  
  ws.send(JSON.stringify({
    type: 'welcome',
    message: 'Connected to Ultimate Agent + Qwen Simple Demo',
    features: ['qwen-demo', 'real-time-updates'],
    mode: 'production-qwen-simple',
    qwen: {
      model: qwenClient.model,
      dailyLimit: 2000,
      provider: 'Demo Client'
    },
    timestamp: new Date().toISOString()
  }));
  
  ws.on('message', async (message) => {
    const requestId = Date.now().toString();
    try {
      const data = JSON.parse(message);
      
      if (data.type === 'qwen_request') {
        logger.info('WebSocket Qwen request', { clientId, requestId, promptLength: data.payload?.prompt?.length });
        
        const response = await qwenClient.chat(data.payload.prompt);
        
        const msg = {
          id: requestId,
          type: 'qwen',
          content: response,
          timestamp: new Date().toISOString(),
          model: qwenClient.model
        };
        
        messageStorage.push(msg);
        
        // Save messages to file for persistence
        saveMessagesToFile();
        
        // Broadcast to all clients
        wss.clients.forEach(client => {
          if (client.readyState === 1) { // WebSocket.OPEN
            try {
              client.send(JSON.stringify({
                type: 'qwen_response',
                requestId: data.requestId,
                response,
                model: qwenClient.model,
                timestamp: new Date().toISOString()
              }));
            } catch (sendError) {
              logger.error('Failed to send WebSocket message', { clientId: clientId, error: sendError.message });
            }
          }
        });
      }
    } catch (error) {
      logger.error('WebSocket message error', { clientId, requestId, error: error.message, stack: error.stack });
      
      // Send error response to client
      try {
        ws.send(JSON.stringify({
          type: 'error',
          requestId: requestId,
          error: error.message,
          timestamp: new Date().toISOString()
        }));
      } catch (sendError) {
        logger.error('Failed to send error response', { clientId, error: sendError.message });
      }
    }
  });
  
  ws.on('close', (code, reason) => {
    logger.info('WebSocket client disconnected', { clientId, code, reason: reason?.toString() });
  });
  
  ws.on('error', (error) => {
    logger.error('WebSocket connection error', { clientId, error: error.message });
  });
});

console.log('🎯 Ultimate Agent + Qwen Initialized!');
console.log('📋 Features:');
console.log('  ✅ Qwen3-Coder-Plus Integration');
console.log('  ✅ WhatsApp Bot Integration');
console.log('  ✅ WebSocket Real-time Updates');
console.log('  ✅ Modern Web Dashboard');
console.log('  ✅ Production-Ready Architecture');
console.log('  ✅ 2,000 Free Daily Requests');