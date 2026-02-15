#!/bin/bash
set -e

echo "🚀 Deploying AgentCostControl..."

# Check for vercel CLI
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found. Install with: npm i -g vercel"
    exit 1
fi

# Check for .env.local
if [ ! -f ".env.local" ]; then
    echo "⚠️  Warning: .env.local not found. Make sure environment variables are set in Vercel."
fi

# Deploy to Vercel
echo "📦 Deploying to Vercel..."
vercel --prod

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Proxy URL: https://your-app.vercel.app"
echo "Dashboard: https://your-app.vercel.app/dashboard"
echo ""
echo "Usage with OpenClaw:"
echo '{'
echo '  "llm": {'
echo '    "provider": "anthropic",'
echo '    "baseUrl": "https://your-app.vercel.app",'
echo '    "headers": { "x-acc-api-key": "acc_your_key" }'
echo '  }'
echo '}'
