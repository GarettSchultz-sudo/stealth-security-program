// Push budget over 100% to trigger exceeded alert
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
const API_KEY_ID = '11ddf1df-cfb1-43f1-9c3d-50d564771ff1'

async function exceedBudget() {
  // Add $1.00 more to push over 100%
  const { error } = await supabase
    .from('api_logs')
    .insert({
      user_id: TEST_USER_ID,
      api_key_id: API_KEY_ID,
      provider: 'openai',
      model: 'gpt-4o',
      request_tokens: 20000,
      response_tokens: 10000,
      cost_usd: 1.00,
      latency_ms: 1500,
      status_code: 200,
      timestamp: new Date().toISOString()
    })

  if (error) {
    console.error('Error adding log:', error)
    return
  }

  console.log('Added $1.00 more spend')

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
    console.log('Budget spend updated - BUDGET EXCEEDED!')
  }
}

exceedBudget()
