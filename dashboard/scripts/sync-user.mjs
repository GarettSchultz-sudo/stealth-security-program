// Quick script to sync auth user to public.users table
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.SUPABASE_URL
const serviceKey = process.env.SUPABASE_SERVICE_KEY

const supabase = createClient(supabaseUrl, serviceKey, {
  auth: {
    autoRefreshToken: false,
    persistSession: false
  }
})

async function syncUser() {
  // Get the user from auth
  const { data: { users }, error } = await supabase.auth.admin.listUsers()

  if (error) {
    console.error('Error listing users:', error)
    return
  }

  const testUser = users.find(u => u.email === 'budget.test.user@gmail.com')

  if (!testUser) {
    console.log('User not found')
    return
  }

  console.log('Found auth user:', testUser.id)
  console.log('Email:', testUser.email)

  // Check if user exists in public.users
  const { data: existingUser, error: checkError } = await supabase
    .from('users')
    .select('id')
    .eq('id', testUser.id)
    .single()

  if (existingUser) {
    console.log('User already exists in public.users')
    return
  }

  // Create user in public.users
  const { data: newUser, error: insertError } = await supabase
    .from('users')
    .insert({
      id: testUser.id,
      email: testUser.email,
      plan: 'free'
    })
    .select()
    .single()

  if (insertError) {
    console.error('Error creating user:', insertError)
  } else {
    console.log('User synced to public.users:', newUser)
  }
}

syncUser()
