/**
 * Email notification service using Resend
 *
 * Used for budget alerts, security findings, and system notifications
 */

interface EmailOptions {
  to: string | string[]
  subject: string
  html: string
  text?: string
  from?: string
}

interface BudgetAlertData {
  budgetName: string
  limit: number
  currentSpend: number
  percentUsed: number
  period: string
  actionOnBreach: string
  dashboardUrl: string
}

interface SecurityAlertData {
  skillName: string
  skillId: string
  trustScore: number
  riskLevel: string
  findingsCount: number
  criticalCount: number
  highCount: number
  scanUrl: string
}

const RESEND_API_KEY = process.env.RESEND_API_KEY
const EMAIL_FROM = process.env.EMAIL_FROM || 'alerts@clawshell.io'

/**
 * Send an email using Resend API
 */
export async function sendEmail(options: EmailOptions): Promise<{ success: boolean; error?: string }> {
  if (!RESEND_API_KEY) {
    console.warn('RESEND_API_KEY not configured, email not sent')
    return { success: false, error: 'Email service not configured' }
  }

  try {
    const response = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${RESEND_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: options.from || EMAIL_FROM,
        to: Array.isArray(options.to) ? options.to : [options.to],
        subject: options.subject,
        html: options.html,
        text: options.text,
      }),
    })

    if (!response.ok) {
      const error = await response.text()
      console.error('Email send failed:', error)
      return { success: false, error }
    }

    return { success: true }
  } catch (error) {
    console.error('Email send error:', error)
    return { success: false, error: String(error) }
  }
}

/**
 * Generate budget alert email HTML
 */
export function generateBudgetAlertEmail(data: BudgetAlertData, type: 'warning' | 'critical' | 'exceeded'): string {
  const isExceeded = type === 'exceeded'
  const isCritical = type === 'critical'

  const title = isExceeded
    ? 'Budget Exceeded'
    : isCritical
    ? 'Budget Critical - Action Required'
    : 'Budget Warning'

  const color = isExceeded ? '#ef4444' : isCritical ? '#f97316' : '#eab308'
  const remaining = Math.max(0, data.limit - data.currentSpend)

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; margin: 0; padding: 20px;">
  <div style="max-width: 600px; margin: 0 auto; background: #1e293b; border-radius: 12px; overflow: hidden;">
    <!-- Header -->
    <div style="background: linear-gradient(135deg, #0891b2, #0284c7); padding: 24px; text-align: center;">
      <h1 style="color: white; margin: 0; font-size: 24px;">ClawShell</h1>
      <p style="color: rgba(255,255,255,0.8); margin: 8px 0 0;">Budget Alert</p>
    </div>

    <!-- Alert Banner -->
    <div style="background: ${color}; padding: 16px; text-align: center;">
      <span style="color: white; font-weight: 600; font-size: 18px;">
        ${isExceeded ? '🚨' : isCritical ? '⚠️' : '⚡'} ${title}
      </span>
    </div>

    <!-- Content -->
    <div style="padding: 24px; color: #e2e8f0;">
      <p style="margin: 0 0 16px;">
        Your budget <strong>"${data.budgetName}"</strong> has reached a threshold that requires your attention.
      </p>

      <!-- Stats -->
      <div style="background: #0f172a; border-radius: 8px; padding: 16px; margin: 16px 0;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
          <span style="color: #94a3b8;">Budget Limit</span>
          <span style="color: white; font-weight: 600;">$${data.limit.toFixed(2)}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
          <span style="color: #94a3b8;">Current Spend</span>
          <span style="color: ${color}; font-weight: 600;">$${data.currentSpend.toFixed(2)}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
          <span style="color: #94a3b8;">Usage</span>
          <span style="color: ${color}; font-weight: 600;">${data.percentUsed.toFixed(1)}%</span>
        </div>
        <div style="display: flex; justify-content: space-between;">
          <span style="color: #94a3b8;">Remaining</span>
          <span style="color: white; font-weight: 600;">$${remaining.toFixed(2)}</span>
        </div>
      </div>

      <!-- Progress Bar -->
      <div style="background: #334155; border-radius: 4px; height: 8px; margin: 16px 0; overflow: hidden;">
        <div style="background: ${color}; width: ${Math.min(100, data.percentUsed)}%; height: 100%;"></div>
      </div>

      ${isExceeded ? `
      <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; padding: 12px; margin: 16px 0;">
        <p style="margin: 0; color: #fca5a5; font-size: 14px;">
          <strong>Action:</strong> ${data.actionOnBreach === 'block' ? 'API requests have been blocked.' : data.actionOnBreach === 'downgrade' ? 'Model downgrade is active.' : 'Please review your usage.'}
        </p>
      </div>
      ` : ''}

      <div style="text-align: center; margin: 24px 0;">
        <a href="${data.dashboardUrl}" style="display: inline-block; background: linear-gradient(135deg, #06b6d4, #0284c7); color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600;">
          View Budget Dashboard
        </a>
      </div>

      <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
        Budget Period: ${data.period} • You can adjust your budget limits in the dashboard settings.
      </p>
    </div>

    <!-- Footer -->
    <div style="background: #0f172a; padding: 16px; text-align: center; border-top: 1px solid #334155;">
      <p style="color: #64748b; font-size: 12px; margin: 0;">
        ClawShell • AI Cost Control & Security
      </p>
    </div>
  </div>
</body>
</html>
  `.trim()
}

/**
 * Generate security alert email HTML
 */
export function generateSecurityAlertEmail(data: SecurityAlertData): string {
  const color = data.trustScore >= 70 ? '#22c55e' : data.trustScore >= 40 ? '#eab308' : '#ef4444'
  const recommendation = data.trustScore >= 70 ? 'Safe to Use' : data.trustScore >= 40 ? 'Use with Caution' : 'Avoid'

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Security Alert - ClawShell Scan</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; margin: 0; padding: 20px;">
  <div style="max-width: 600px; margin: 0 auto; background: #1e293b; border-radius: 12px; overflow: hidden;">
    <!-- Header -->
    <div style="background: linear-gradient(135deg, #0891b2, #0284c7); padding: 24px; text-align: center;">
      <h1 style="color: white; margin: 0; font-size: 24px;">🛡️ ClawShell Scan</h1>
      <p style="color: rgba(255,255,255,0.8); margin: 8px 0 0;">Security Scan Complete</p>
    </div>

    <!-- Trust Score Banner -->
    <div style="background: ${color}; padding: 20px; text-align: center;">
      <div style="font-size: 48px; font-weight: 700; color: white;">${data.trustScore}</div>
      <div style="color: rgba(255,255,255,0.9); font-size: 14px; margin-top: 4px;">Trust Score</div>
    </div>

    <!-- Content -->
    <div style="padding: 24px; color: #e2e8f0;">
      <h2 style="margin: 0 0 8px; font-size: 18px;">${data.skillName}</h2>
      <p style="color: #64748b; font-size: 14px; margin: 0 0 16px;">${data.skillId}</p>

      <!-- Summary -->
      <div style="background: #0f172a; border-radius: 8px; padding: 16px; margin: 16px 0;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
          <span style="color: #94a3b8;">Risk Level</span>
          <span style="color: ${color}; font-weight: 600; text-transform: capitalize;">${data.riskLevel}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
          <span style="color: #94a3b8;">Recommendation</span>
          <span style="color: ${color}; font-weight: 600;">${recommendation}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
          <span style="color: #94a3b8;">Total Findings</span>
          <span style="color: white; font-weight: 600;">${data.findingsCount}</span>
        </div>
        ${data.criticalCount > 0 ? `
        <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
          <span style="color: #fca5a5;">Critical Issues</span>
          <span style="color: #ef4444; font-weight: 600;">${data.criticalCount}</span>
        </div>
        ` : ''}
        ${data.highCount > 0 ? `
        <div style="display: flex; justify-content: space-between;">
          <span style="color: #fdba74;">High Severity</span>
          <span style="color: #f97316; font-weight: 600;">${data.highCount}</span>
        </div>
        ` : ''}
      </div>

      ${data.criticalCount > 0 || data.highCount > 0 ? `
      <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; padding: 12px; margin: 16px 0;">
        <p style="margin: 0; color: #fca5a5; font-size: 14px;">
          <strong>⚠️ Action Required:</strong> This skill has security issues that need attention before use in production.
        </p>
      </div>
      ` : ''}

      <div style="text-align: center; margin: 24px 0;">
        <a href="${data.scanUrl}" style="display: inline-block; background: linear-gradient(135deg, #06b6d4, #0284c7); color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600;">
          View Full Report
        </a>
      </div>

      <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
        Scan completed on ${new Date().toLocaleDateString()} • Powered by ClawShell Scan
      </p>
    </div>

    <!-- Footer -->
    <div style="background: #0f172a; padding: 16px; text-align: center; border-top: 1px solid #334155;">
      <p style="color: #64748b; font-size: 12px; margin: 0;">
        ClawShell • AI Cost Control & Security
      </p>
    </div>
  </div>
</body>
</html>
  `.trim()
}

/**
 * Send a budget alert email
 */
export async function sendBudgetAlertEmail(
  email: string,
  data: BudgetAlertData,
  type: 'warning' | 'critical' | 'exceeded'
): Promise<{ success: boolean; error?: string }> {
  const subject = type === 'exceeded'
    ? `🚨 Budget Exceeded: ${data.budgetName}`
    : type === 'critical'
    ? `⚠️ Budget Critical: ${data.budgetName} at ${data.percentUsed.toFixed(0)}%`
    : `⚡ Budget Alert: ${data.budgetName} at ${data.percentUsed.toFixed(0)}%`

  return sendEmail({
    to: email,
    subject,
    html: generateBudgetAlertEmail(data, type),
  })
}

/**
 * Send a security alert email
 */
export async function sendSecurityAlertEmail(
  email: string,
  data: SecurityAlertData
): Promise<{ success: boolean; error?: string }> {
  const subject = data.trustScore >= 70
    ? `✅ Security Scan Complete: ${data.skillName}`
    : data.trustScore >= 40
    ? `⚠️ Security Issues Found: ${data.skillName}`
    : `🚨 Critical Security Alert: ${data.skillName}`

  return sendEmail({
    to: email,
    subject,
    html: generateSecurityAlertEmail(data),
  })
}
