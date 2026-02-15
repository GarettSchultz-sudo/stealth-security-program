// Quick script to confirm user email for testing
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.SUPABASE_URL
const serviceKey = process.env.SUPABASE_SERVICE_KEY

const supabase = createClient(supabaseUrl, serviceKey, {
  auth: {
    autoRefreshToken: false,
    persistSession: false
  }
})

async function confirmUser() {
  // Get the user by email
  const { data: { users }, error } = await supabase.auth.admin.listUsers()

  if (error) {
    console.error('Error listing users:', error)
    return
  }

  const testUser = users.find(u => u.email === 'budget.test.user@gmail.com')

  if (!testUser) {
    console.log('User not found. Available users:')
    users.forEach(u => console.log(`  - ${u.email} (confirmed: ${!!u.confirmed_at})`))
    return
  }

  console.log('Found user:', testUser.id)
  console.log('Email confirmed:', !!testUser.confirmed_at)

  if (!testUser.confirmed_at) {
    // Confirm the user
    const { error: confirmError } = await supabase.auth.admin.updateUserById(
      testUser.id,
      { email_confirm: true }
    )

    if (confirmError) {
      console.error('Error confirming user:', confirmError)
    } else {
      console.log('User confirmed successfully!')
    }
  }
}

confirmUser()
