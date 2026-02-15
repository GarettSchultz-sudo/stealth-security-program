// Add test request logs to simulate spending and trigger budget alerts
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.SUPABASE_URL
const serviceKey = process.env.SUPABASE_SERVICE_KEY

const supabase = createClient(supabaseUrl, serviceKey, {
  auth: {
    autoRefreshToken: false,
    persistSession: false
  }
})

const TEST_USER_ID = '6a7cbaad-b17d-43df-aab8-ba8345323da4'

async function addTestLogs() {
  // First, create an API key for the user
  const { data: existingKeys } = await supabase
    .from('api_keys')
    .select('id')
    .eq('user_id', TEST_USER_ID)
    .limit(1)

  let apiKeyId
  if (existingKeys && existingKeys.length > 0) {
    apiKeyId = existingKeys[0].id
    console.log('Using existing API key:', apiKeyId)
  } else {
    const { data: newKey, error: keyError } = await supabase
      .from('api_keys')
      .insert({
        user_id: TEST_USER_ID,
        key_hash: 'test_hash_' + Date.now(),
        name: 'Test API Key'
      })
      .select()
      .single()

    if (keyError) {
      console.error('Error creating API key:', keyError)
      return
    }
    apiKeyId = newKey.id
    console.log('Created API key:', apiKeyId)
  }

  // Add request logs to simulate spending - we'll add $8.50 to trigger 85% threshold
  const testLogs = [
    { model: 'gpt-4o', cost: 2.50, tokens: 50000 },
    { model: 'gpt-4o-mini', cost: 0.50, tokens: 100000 },
    { model: 'claude-3-sonnet', cost: 3.00, tokens: 75000 },
    { model: 'claude-3-haiku', cost: 0.25, tokens: 50000 },
    { model: 'gpt-4-turbo', cost: 2.25, tokens: 45000 },
  ]

  for (const log of testLogs) {
    const { error } = await supabase
      .from('api_logs')
      .insert({
        user_id: TEST_USER_ID,
        api_key_id: apiKeyId,
        provider: log.model.startsWith('gpt') ? 'openai' : 'anthropic',
        model: log.model,
        request_tokens: Math.floor(log.tokens * 0.7),
        response_tokens: Math.floor(log.tokens * 0.3),
        cost_usd: log.cost,
        latency_ms: Math.floor(Math.random() * 2000) + 100,
        status_code: 200,
        timestamp: new Date().toISOString()
      })

    if (error) {
      console.error(`Error adding log for ${log.model}:`, error)
    } else {
      console.log(`Added log: ${log.model} - $${log.cost.toFixed(2)}`)
    }
  }

  // Check total spend
  const { data: logs } = await supabase
    .from('api_logs')
    .select('cost_usd')
    .eq('user_id', TEST_USER_ID)

  const totalSpend = logs?.reduce((sum, l) => sum + parseFloat(l.cost_usd), 0) || 0
  console.log(`\nTotal spend: $${totalSpend.toFixed(2)}`)
  console.log(`Budget limit: $10.00`)
  console.log(`Percent used: ${((totalSpend / 10) * 100).toFixed(1)}%`)

  // Update the budget's current_spend_usd
  const { error: updateError } = await supabase
    .from('budgets')
    .update({ current_spend_usd: totalSpend })
    .eq('user_id', TEST_USER_ID)

  if (updateError) {
    console.error('Error updating budget:', updateError)
  } else {
    console.log('Budget spend updated')
  }
}

addTestLogs()
