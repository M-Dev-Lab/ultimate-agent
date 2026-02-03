module.exports = {
  apps: [{
    name: 'ultimate-agent-qwen',
    script: 'dist/server.js',
    env: { 
      NODE_ENV: 'production', 
      LOG_LEVEL: 'info',
      OPENAI_API_KEY: process.env.OPENAI_API_KEY,
      OPENAI_BASE_URL: process.env.OPENAI_BASE_URL,
      OPENAI_MODEL: process.env.OPENAI_MODEL
    },
    systemd: true,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env_file: '.env'
  }]
};