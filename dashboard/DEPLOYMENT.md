# ClawShell Deployment Guide

This guide covers deploying the ClawShell MVP to production.

## Prerequisites

- Supabase account with project configured
- Vercel account
- Railway account (for proxy)
- Upstash account (for Redis rate limiting)
- Domain name (optional)

## Step 1: Supabase Configuration

### 1.1 Enable Realtime (Optional but Recommended)

1. Go to your Supabase Dashboard
2. Navigate to **Database > Replication**
3. Enable replication for the `request_logs` table
4. This enables real-time dashboard updates

### 1.2 Configure Authentication

1. Go to **Authentication > URL Configuration**
2. Add your production URL to **Site URL**: `https://your-domain.com`
3. Add to **Redirect URLs**:
   - `https://your-domain.com/auth/callback`
   - `http://localhost:3000/auth/callback` (for development)

### 1.3 Run Migrations

Ensure all migrations have been run:
```bash
# If using Supabase CLI
supabase db push

# Or run migrations via SQL Editor in dashboard
```

## Step 2: Deploy Dashboard to Vercel

### 2.1 Create Vercel Project

1. Push your code to GitHub
2. Go to [vercel.com](https://vercel.com)
3. Click **New Project**
4. Import your GitHub repository
5. Set **Root Directory** to `dashboard`
6. Configure framework preset: **Next.js**

### 2.2 Configure Environment Variables

In Vercel Dashboard > Settings > Environment Variables:

```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
NEXT_PUBLIC_APP_URL=https://your-domain.com
NEXT_PUBLIC_API_URL=https://your-proxy.railway.app
CRON_SECRET=your-secure-random-string
```

### 2.3 Configure Domain

1. In Vercel Dashboard > Settings > Domains
2. Add your custom domain
3. Configure DNS records as instructed

### 2.4 Deploy

Click **Deploy** and wait for the build to complete.

### 2.5 Verify Cron Jobs

Vercel Cron Jobs are automatically configured via `vercel.json`:
- `/api/cron/reset-budgets` - Runs hourly (resets budget periods)
- `/api/cron/check-breaches` - Runs every 15 minutes (checks budget limits)

## Step 3: Configure Upstash Redis

### 3.1 Create Redis Instance

1. Go to [upstash.com](https://upstash.com)
2. Create a new Redis database
3. Name it `clawshell-ratelimit`
4. Select a region close to your users

### 3.2 Get Credentials

From the Redis database dashboard, copy:
- `UPSTASH_REDIS_REST_URL`
- `UPSTASH_REDIS_REST_TOKEN`

These will be used by the proxy for rate limiting.

## Step 4: Deploy Proxy to Railway

### 4.1 Create Railway Project

1. Go to [railway.app](https://railway.app)
2. Create new project
3. Deploy from GitHub repo
4. Set root directory to `proxy`

### 4.2 Configure Environment Variables

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# Upstash Redis
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-token

# API Keys
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
# Add other provider keys as needed

# CORS
ALLOWED_ORIGINS=https://your-domain.com,http://localhost:3000
```

### 4.3 Configure Domain

1. In Railway > Settings > Domains
2. Generate a domain or add custom domain
3. Note the URL for `NEXT_PUBLIC_API_URL`

## Step 5: Configure CORS

### 5.1 Dashboard CORS

The dashboard doesn't need CORS configuration.

### 5.2 Proxy CORS

In Railway environment variables:
```bash
ALLOWED_ORIGINS=https://your-domain.com
```

## Step 6: Post-Deployment Verification

### 6.1 Test Authentication

1. Visit your production URL
2. Sign up with email
3. Check email for verification
4. Sign in

### 6.2 Test API Key Creation

1. Go to API Keys page
2. Create a new key
3. Copy the key

### 6.3 Test Proxy Connection

```bash
curl -X POST https://your-proxy.railway.app/v1/chat/completions \
  -H "Authorization: Bearer acc_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### 6.4 Test Budget Creation

1. Go to Budgets page
2. Create a test budget
3. Verify it appears in the list

### 6.5 Check Dashboard Stats

1. Make a few API requests
2. Check Dashboard page for stats
3. Verify Analytics page shows data
4. Check Logs page for request history

## Troubleshooting

### Common Issues

**Authentication not working:**
- Check Supabase URL configuration
- Verify redirect URLs in Supabase dashboard
- Check browser console for errors

**API requests failing:**
- Verify CORS configuration
- Check API key is valid
- Verify proxy is running

**Real-time updates not working:**
- Enable Supabase Realtime in database settings
- Check browser network tab for WebSocket connections

**Cron jobs not running:**
- Verify CRON_SECRET is set
- Check Vercel logs for cron job execution
- Test cron endpoints manually

## Monitoring

### Vercel Logs
- Go to Vercel Dashboard > Deployments
- Click on a deployment to view logs

### Railway Logs
- Go to Railway > Project > Deployments
- View logs for each deployment

### Supabase Logs
- Go to Supabase Dashboard > Logs
- View database, auth, and API logs

## Scaling Considerations

- **Vercel**: Automatically scales
- **Railway**: Upgrade plan for more resources
- **Supabase**: Upgrade for more database capacity
- **Upstash**: Monitor Redis usage

## Security Checklist

- [ ] All secrets stored in environment variables
- [ ] CORS configured for production domain only
- [ ] API keys hashed before storage
- [ ] Rate limiting enabled
- [ ] Budget enforcement active
- [ ] Cron job endpoints secured with CRON_SECRET
