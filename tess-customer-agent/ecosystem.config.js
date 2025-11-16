module.exports = {
  apps: [
    {
      name: 'tess-uat',
      script: 'venv/bin/python',
      args: '-m uvicorn src.main:app --host 0.0.0.0 --port 8000',
      cwd: __dirname,
      env_uat: {
        APP_ENV: 'uat',
        NODE_ENV: 'uat'
      },
      instances: 2,
      exec_mode: 'cluster',
      watch: false,
      max_memory_restart: '1G',
      error_file: './logs/uat-error.log',
      out_file: './logs/uat-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 4000,
      kill_timeout: 5000,
      listen_timeout: 10000,
      env: {
        // Load from .env.uat at runtime
      }
    },
    {
      name: 'tess-prod',
      script: 'venv/bin/python',
      args: '-m uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4',
      cwd: __dirname,
      env_prod: {
        APP_ENV: 'prod',
        NODE_ENV: 'production'
      },
      instances: 4,
      exec_mode: 'cluster',
      watch: false,
      max_memory_restart: '2G',
      error_file: './logs/prod-error.log',
      out_file: './logs/prod-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 4000,
      kill_timeout: 5000,
      listen_timeout: 10000,
      cron_restart: '0 3 * * *', // Restart daily at 3 AM
      env: {
        // Load from .env.prod at runtime
      }
    }
  ]
};
