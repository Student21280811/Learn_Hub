# LearnHub - Complete Deployment Guide

## 📋 Table of Contents
1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Environment Setup](#environment-setup)
4. [Database Setup (MongoDB)](#database-setup)
5. [Backend Deployment](#backend-deployment)
6. [Frontend Deployment](#frontend-deployment)
7. [Third-Party Services Configuration](#third-party-services)
8. [Domain & SSL Setup](#domain-ssl-setup)
9. [Deployment Options](#deployment-options)
10. [Post-Deployment Checklist](#post-deployment-checklist)
11. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software
- **Node.js**: v16+ (for frontend)
- **Python**: 3.11+ (for backend)
- **MongoDB**: 4.4+ or MongoDB Atlas account
- **Git**: Latest version
- **SSL Certificate**: (Let's Encrypt recommended)

### Required Accounts & API Keys
- **Stripe Account** (for payments)
- **SendGrid Account** (for emails)
- **OpenAI API Key** or Emergent LLM Key (for AI features)
- **Domain Name** (e.g., yourdomain.com)
- **Hosting Provider** (VPS, AWS, DigitalOcean, etc.)

### Recommended Server Specs (Minimum)
- **CPU**: 2 vCPUs
- **RAM**: 4GB
- **Storage**: 50GB SSD
- **OS**: Ubuntu 22.04 LTS (recommended)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      yourdomain.com                         │
│                      (HTTPS/SSL)                            │
└────────────────┬────────────────────────────────────────────┘
                 │
         ┌───────▼──────────┐
         │   Nginx/Caddy    │  (Reverse Proxy)
         │   Port 80/443    │
         └───────┬──────────┘
                 │
        ┌────────┴─────────┐
        │                  │
   ┌────▼─────┐      ┌────▼─────┐
   │ Frontend │      │ Backend  │
   │ React    │      │ FastAPI  │
   │ Port 3000│      │ Port 8001│
   └──────────┘      └────┬─────┘
                           │
                      ┌────▼─────┐
                      │ MongoDB  │
                      │ Port     │
                      │ 27017    │
                      └──────────┘
```

---

## Environment Setup

### 1. Server Setup (Ubuntu 22.04)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Node.js (v18 LTS)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install Yarn (for frontend)
npm install -g pnpm

# Install Nginx (reverse proxy)
sudo apt install -y nginx

# Install MongoDB (or use MongoDB Atlas)
# For local MongoDB:
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt update
sudo apt install -y mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod

# Install PM2 (process manager)
pnpm add -g pm2

# Install Certbot (for SSL)
sudo apt install -y certbot python3-certbot-nginx
```

---

## Database Setup

### Option 1: MongoDB Atlas (Recommended for Production)

1. **Create MongoDB Atlas Account**: https://www.mongodb.com/cloud/atlas
2. **Create a Cluster**:
   - Choose a cloud provider (AWS/Google Cloud/Azure)
   - Select a region close to your server
   - Choose free tier (M0) or paid tier based on needs
3. **Create Database User**:
   - Database Access → Add New Database User
   - Username: `learnhub_user`
   - Password: (generate strong password)
   - Database User Privileges: Atlas Admin
4. **Whitelist IP Address**:
   - Network Access → Add IP Address
   - Add your server's public IP or 0.0.0.0/0 (less secure)
5. **Get Connection String**:
   - Click "Connect" → "Connect your application"
   - Copy the connection string:
   ```
   mongodb+srv://learnhub_user:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```

### Option 2: Local MongoDB

```bash
# Start MongoDB
sudo systemctl start mongod

# Create database and user
mongosh
> use learnhub
> db.createUser({
    user: "learnhub_user",
    pwd: "your_secure_password",
    roles: [{ role: "readWrite", db: "learnhub" }]
  })
> exit

# Connection string will be:
# mongodb://learnhub_user:your_secure_password@localhost:27017/learnhub
```

---

## Backend Deployment

### 1. Clone Repository

```bash
cd /var/www
git clone <your-repo-url> learnhub
cd learnhub/backend
```

### 2. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create `/var/www/learnhub/backend/.env`:

```bash
# Database Configuration
MONGO_URL=mongodb+srv://learnhub_user:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
DB_NAME=learnhub

# JWT Configuration
JWT_SECRET=your_super_secure_random_jwt_secret_key_here_min_32_chars

# Admin Commission (15% = 0.15)
ADMIN_COMMISSION=0.15

# Stripe Configuration
STRIPE_SECRET_KEY=sk_live_xxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxx

# SendGrid Configuration
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxx
SENDER_EMAIL=noreply@yourdomain.com

# OpenAI Configuration (or use Emergent LLM Key)
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
# OR
EMERGENT_LLM_KEY=ell_xxxxxxxxxxxxxxxxxxxx

# Server Configuration
HOST=0.0.0.0
PORT=8001
```

**🔐 Security Notes:**
- Generate JWT_SECRET: `openssl rand -hex 32`
- Never commit .env to git
- Keep all API keys secure
- Use different keys for production vs development

### 5. Create PM2 Ecosystem File

Create `/var/www/learnhub/backend/ecosystem.config.js`:

```javascript
module.exports = {
  apps: [{
    name: 'learnhub-backend',
    script: 'venv/bin/uvicorn',
    args: 'server:app --host 0.0.0.0 --port 8001',
    cwd: '/var/www/learnhub/backend',
    instances: 2,
    exec_mode: 'cluster',
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production'
    },
    error_file: '/var/log/pm2/learnhub-backend-error.log',
    out_file: '/var/log/pm2/learnhub-backend-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
  }]
};
```

### 6. Start Backend with PM2

```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

### 7. Test Backend

```bash
curl http://localhost:8001/api/courses
# Should return course list or []
```

---

## Frontend Deployment

### 1. Navigate to Frontend Directory

```bash
cd /var/www/learnhub/frontend
```

### 2. Configure Environment Variables

Create `/var/www/learnhub/frontend/.env`:

```bash
# Backend API URL - CHANGE THIS TO YOUR DOMAIN
REACT_APP_BACKEND_URL=https://api.yourdomain.com

# OR if using same domain with /api prefix:
REACT_APP_BACKEND_URL=https://yourdomain.com
```

**🎯 Important**: 
- If using subdomain (api.yourdomain.com): Use `https://api.yourdomain.com`
- If using same domain: Use `https://yourdomain.com` (Nginx will route /api to backend)

### 3. Install Dependencies

```bash
pnpm install
```

### 4. Build for Production

```bash
pnpm run build
```

This creates an optimized production build in `/var/www/learnhub/frontend/build`

### 5. Option A: Serve with Nginx (Recommended)

Frontend will be served as static files by Nginx. See [Domain & SSL Setup](#domain-ssl-setup) section.

### 5. Option B: Serve with PM2 + Serve

```bash
pnpm add -g serve

# Create PM2 config for frontend
cat > /var/www/learnhub/frontend/ecosystem.frontend.js << 'EOF'
module.exports = {
  apps: [{
    name: 'learnhub-frontend',
    script: 'serve',
    args: '-s build -l 3000',
    cwd: '/var/www/learnhub/frontend',
    instances: 1,
    watch: false,
    env: {
      NODE_ENV: 'production'
    }
  }]
};
EOF

pm2 start ecosystem.frontend.js
pm2 save
```

---

## Third-Party Services

### 1. Stripe Setup

**Steps:**
1. Go to https://dashboard.stripe.com
2. Create account or login
3. Get API Keys:
   - Developers → API keys
   - Copy **Secret key** (starts with `sk_live_` for production)
4. Setup Webhook:
   - Developers → Webhooks → Add endpoint
   - Endpoint URL: `https://yourdomain.com/api/webhook/stripe`
   - Listen to events: `checkout.session.completed`, `payment_intent.succeeded`
   - Copy **Signing secret** (starts with `whsec_`)
5. Update backend `.env`:
   ```bash
   STRIPE_SECRET_KEY=sk_live_xxxxx
   STRIPE_WEBHOOK_SECRET=whsec_xxxxx
   ```

**Test Payment:**
- Test mode card: 4242 4242 4242 4242
- Expiry: Any future date
- CVC: Any 3 digits

### 2. SendGrid Setup

**Steps:**
1. Go to https://sendgrid.com
2. Create account (free tier: 100 emails/day)
3. Verify sender identity:
   - Settings → Sender Authentication
   - Verify single sender: noreply@yourdomain.com
4. Create API Key:
   - Settings → API Keys → Create API Key
   - Full Access or Mail Send only
   - Copy key (starts with `SG.`)
5. Update backend `.env`:
   ```bash
   SENDGRID_API_KEY=SG.xxxxx
   SENDER_EMAIL=noreply@yourdomain.com
   ```

**Email Templates to Setup:**
- Enrollment confirmation
- Certificate issued
- Course approval/rejection (for instructors)
- Payment receipt

### 3. OpenAI / Emergent LLM Setup

**Option A: OpenAI**
1. Go to https://platform.openai.com
2. Create account and add payment method
3. API Keys → Create new secret key
4. Copy key (starts with `sk-`)
5. Update backend `.env`:
   ```bash
   OPENAI_API_KEY=sk-xxxxx
   ```

**Option B: Emergent LLM (Universal Key)**
1. Get Emergent LLM Key from platform
2. Update backend `.env`:
   ```bash
   EMERGENT_LLM_KEY=ell_xxxxx
   ```

---

## Domain & SSL Setup

### 1. DNS Configuration

Point your domain to your server:

**For Main Domain (yourdomain.com):**
```
Type: A
Name: @
Value: YOUR_SERVER_IP
TTL: 3600
```

**For API Subdomain (api.yourdomain.com):**
```
Type: A
Name: api
Value: YOUR_SERVER_IP
TTL: 3600
```

**For WWW:**
```
Type: CNAME
Name: www
Value: yourdomain.com
TTL: 3600
```

Wait 10-30 minutes for DNS propagation.

### 2. Nginx Configuration

#### Option A: Same Domain Setup (yourdomain.com for both)

Create `/etc/nginx/sites-available/learnhub`:

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration (Certbot will add these)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Backend API Routes
    location /api {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Frontend Static Files
    location / {
        root /var/www/learnhub/frontend/build;
        try_files $uri $uri/ /index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/javascript application/json;
}
```

#### Option B: Subdomain Setup (api.yourdomain.com)

Create `/etc/nginx/sites-available/learnhub`:

```nginx
# Backend API - api.yourdomain.com
server {
    listen 80;
    listen [::]:80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}

# Frontend - yourdomain.com
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    root /var/www/learnhub/frontend/build;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 3. Enable Nginx Configuration

```bash
# Test configuration
sudo nginx -t

# Create symlink
sudo ln -s /etc/nginx/sites-available/learnhub /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Restart Nginx
sudo systemctl restart nginx
```

### 4. Install SSL Certificate (Let's Encrypt)

```bash
# For single domain setup
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# For subdomain setup
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com -d api.yourdomain.com

# Follow prompts:
# - Enter email for renewal notices
# - Agree to terms
# - Choose redirect HTTP to HTTPS (option 2)

# Auto-renewal (runs twice daily)
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

### 5. Verify SSL

```bash
# Check SSL grade
https://www.ssllabs.com/ssltest/analyze.html?d=yourdomain.com
```

---

## Deployment Options

### Option 1: VPS Providers (Recommended)

**DigitalOcean:**
```bash
# Create Droplet
# - Choose Ubuntu 22.04
# - Minimum: Basic ($12/mo - 2GB RAM)
# - Enable backups
# - Add SSH key

# Follow setup steps above
```

**Linode, Vultr, Hetzner:** Similar process

**Cost Estimate:**
- VPS: $10-20/month
- Domain: $10-15/year
- MongoDB Atlas: Free (M0) or $9+/month
- Stripe: 2.9% + $0.30 per transaction
- SendGrid: Free (100 emails/day) or $15+/month
- Total: ~$20-50/month

### Option 2: AWS (Scalable)

**Services:**
- EC2 (t3.medium): Backend + Frontend
- DocumentDB or MongoDB Atlas: Database
- CloudFront: CDN
- Route 53: DNS
- Certificate Manager: Free SSL

### Option 3: Google Cloud Platform

**Services:**
- Compute Engine: VM
- Cloud Run: Containers (alternative)
- MongoDB Atlas: Database

### Option 4: Heroku (Easiest but Limited)

**Backend:**
```bash
# Install Heroku CLI
heroku login
cd /var/www/learnhub/backend
heroku create learnhub-backend
heroku config:set MONGO_URL="..." STRIPE_SECRET_KEY="..." ...
git push heroku main
```

**Frontend:**
```bash
cd /var/www/learnhub/frontend
# Update .env with Heroku backend URL
pnpm run build
# Deploy to Netlify/Vercel (frontend)
```

---

## Post-Deployment Checklist

### 1. Create Admin User

```bash
# SSH into server
mongosh "YOUR_MONGO_URL"

# Use database
use learnhub

# Create admin user (change password!)
db.users.insertOne({
  id: "admin-" + Date.now(),
  name: "Admin User",
  email: "admin@yourdomain.com",
  password: "$2b$12$encrypted_password_here",  // Hash with bcrypt
  role: "admin",
  is_active: true,
  created_at: new Date().toISOString()
})

# Or use Python to hash password:
# python3 -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('your_password'))"
```

### 2. Test Core Features

```bash
# Test URLs
https://yourdomain.com                    # Landing page
https://yourdomain.com/courses            # Course catalog
https://yourdomain.com/login              # Login page
https://yourdomain.com/dashboard/admin    # Admin dashboard

# Test API
curl https://yourdomain.com/api/courses
```

### 3. Test Payment Flow

1. Create test course as instructor
2. Try to enroll with Stripe test card
3. Verify enrollment works
4. Check Stripe dashboard for payment

### 4. Test Email Delivery

1. Register new user
2. Check email received
3. Test password reset
4. Verify all email templates

### 5. Setup Monitoring

```bash
# Install monitoring tools
pnpm add -g pm2-logrotate
pm2 install pm2-logrotate

# Setup log rotation
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 7

# Setup monitoring (optional)
# - Uptime Robot: https://uptimerobot.com
# - New Relic: https://newrelic.com
# - Sentry: https://sentry.io
```

### 6. Backup Strategy

```bash
# MongoDB backup script
cat > /usr/local/bin/backup-mongodb.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/mongodb"
mkdir -p $BACKUP_DIR

# Backup
mongodump --uri="YOUR_MONGO_URL" --out=$BACKUP_DIR/$DATE

# Keep only last 7 days
find $BACKUP_DIR -type d -mtime +7 -exec rm -rf {} +

# Optional: Upload to S3
# aws s3 sync $BACKUP_DIR s3://your-bucket/mongodb-backups/
EOF

chmod +x /usr/local/bin/backup-mongodb.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup-mongodb.sh") | crontab -
```

### 7. Security Hardening

```bash
# Setup firewall
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw enable

# Disable root login
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# Setup fail2ban
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Regular updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

---

## Troubleshooting

### Backend Not Starting

```bash
# Check PM2 logs
pm2 logs learnhub-backend

# Check if port is in use
sudo netstat -tulpn | grep 8001

# Test backend directly
cd /var/www/learnhub/backend
source venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8001
```

### Frontend Shows Blank Page

```bash
# Check browser console for errors
# Common issue: REACT_APP_BACKEND_URL incorrect

# Rebuild frontend
cd /var/www/learnhub/frontend
yarn build

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Database Connection Failed

```bash
# Test MongoDB connection
mongosh "YOUR_MONGO_URL"

# Check firewall rules (MongoDB Atlas)
# Verify IP whitelist

# Check connection string format
# mongodb+srv://user:password@cluster.xxxxx.mongodb.net/dbname
```

### SSL Certificate Issues

```bash
# Renew certificate manually
sudo certbot renew

# Check certificate status
sudo certbot certificates

# Verify Nginx SSL config
sudo nginx -t
```

### API Returns 502 Bad Gateway

```bash
# Check if backend is running
pm2 status

# Check backend logs
pm2 logs learnhub-backend

# Restart backend
pm2 restart learnhub-backend

# Test backend directly
curl http://localhost:8001/api/courses
```

### Stripe Webhook Not Working

```bash
# Check webhook endpoint is accessible
curl https://yourdomain.com/api/webhook/stripe

# Verify webhook secret in .env
# Check Stripe dashboard → Webhooks for delivery attempts

# Test webhook locally with Stripe CLI
stripe listen --forward-to https://yourdomain.com/api/webhook/stripe
```

### Emails Not Sending

```bash
# Check SendGrid API key
# Verify sender email is verified in SendGrid
# Check backend logs for email errors
pm2 logs learnhub-backend | grep -i email

# Test SendGrid directly
curl --request POST \
  --url https://api.sendgrid.com/v3/mail/send \
  --header "Authorization: Bearer YOUR_SENDGRID_API_KEY" \
  --header 'Content-Type: application/json' \
  --data '{"personalizations":[{"to":[{"email":"test@example.com"}]}],"from":{"email":"noreply@yourdomain.com"},"subject":"Test","content":[{"type":"text/plain","value":"Test"}]}'
```

---

## Performance Optimization

### 1. Enable Caching

```nginx
# Add to Nginx config
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=1g inactive=60m;

location /api {
    proxy_cache api_cache;
    proxy_cache_valid 200 5m;
    proxy_cache_use_stale error timeout invalid_header updating;
    add_header X-Cache-Status $upstream_cache_status;
    # ... rest of config
}
```

### 2. CDN Setup (Cloudflare)

1. Add site to Cloudflare
2. Update nameservers at domain registrar
3. Enable "Full (strict)" SSL mode
4. Enable Auto Minify for JS, CSS, HTML
5. Enable Brotli compression

### 3. Database Indexing

```javascript
// Connect to MongoDB
mongosh "YOUR_MONGO_URL"

// Create indexes for better performance
use learnhub

db.users.createIndex({ email: 1 }, { unique: true })
db.courses.createIndex({ status: 1, category: 1 })
db.enrollments.createIndex({ user_id: 1, course_id: 1 })
db.reviews.createIndex({ course_id: 1 })
db.certificates.createIndex({ user_id: 1, course_id: 1 })
```

---

## Maintenance Commands

```bash
# Update application
cd /var/www/learnhub
git pull origin main

# Update backend
cd backend
source venv/bin/activate
pip install -r requirements.txt
pm2 restart learnhub-backend

# Update frontend
cd ../frontend
yarn install
yarn build
sudo systemctl reload nginx

# View logs
pm2 logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Monitor system resources
htop
df -h
free -m

# Database backup
mongodump --uri="YOUR_MONGO_URL" --out=/var/backups/mongodb/backup-$(date +%Y%m%d)

# Restart all services
pm2 restart all
sudo systemctl restart nginx
```

---

## Support & Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com
- **React Docs**: https://react.dev
- **MongoDB Docs**: https://docs.mongodb.com
- **Nginx Docs**: https://nginx.org/en/docs/
- **Stripe Docs**: https://stripe.com/docs
- **SendGrid Docs**: https://docs.sendgrid.com

---

## License

© 2024 LearnHub. All rights reserved.

---

**Need Help?** Open an issue on GitHub or contact support@yourdomain.com
