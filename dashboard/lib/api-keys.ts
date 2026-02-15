import { createClient } from '@supabase/supabase-js'
import crypto from 'crypto'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY!

// Generate a new API key with acc_ prefix
export function generateApiKey(): string {
  const randomBytes = crypto.randomBytes(24).toString('hex')
  return `acc_${randomBytes}`
}

// Hash an API key for storage (SHA-256)
export function hashApiKey(key: string): string {
  return crypto.createHash('sha256').update(key).digest('hex')
}

// Validate API key format
export function isValidApiKeyFormat(key: string): boolean {
  return /^acc_[a-f0-9]{48}$/.test(key)
}

// Verify an API key against a hash
export function verifyApiKey(key: string, hash: string): boolean {
  return hashApiKey(key) === hash
}

// Get Supabase admin client for server-side operations
function getSupabaseAdmin() {
  return createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  })
}

// Create a new API key for a user
export async function createApiKey(userId: string, name: string): Promise<{ key: string; id: string } | null> {
  const supabase = getSupabaseAdmin()

  const rawKey = generateApiKey()
  const keyHash = hashApiKey(rawKey)

  const { data, error } = await supabase
    .from('api_keys')
    .insert({
      user_id: userId,
      key_hash: keyHash,
      name: name,
    })
    .select('id')
    .single()

  if (error || !data) {
    console.error('Error creating API key:', error)
    return null
  }

  return { key: rawKey, id: data.id }
}

// List API keys for a user (without revealing the actual key)
export async function listApiKeys(userId: string) {
  const supabase = getSupabaseAdmin()

  const { data, error } = await supabase
    .from('api_keys')
    .select('id, name, last_used_at, created_at, is_active')
    .eq('user_id', userId)
    .order('created_at', { ascending: false })

  if (error) {
    console.error('Error listing API keys:', error)
    return []
  }

  return data
}

// Delete an API key
export async function deleteApiKey(userId: string, keyId: string): Promise<boolean> {
  const supabase = getSupabaseAdmin()

  const { error } = await supabase
    .from('api_keys')
    .delete()
    .eq('id', keyId)
    .eq('user_id', userId)

  return !error
}

// Validate an API key and return user ID
export async function validateApiKeyAndGetUser(key: string): Promise<string | null> {
  if (!isValidApiKeyFormat(key)) {
    return null
  }

  const supabase = getSupabaseAdmin()
  const keyHash = hashApiKey(key)

  const { data, error } = await supabase
    .from('api_keys')
    .select('user_id, is_active')
    .eq('key_hash', keyHash)
    .eq('is_active', true)
    .single()

  if (error || !data) {
    return null
  }

  // Update last_used_at
  await supabase
    .from('api_keys')
    .update({ last_used_at: new Date().toISOString() })
    .eq('key_hash', keyHash)

  return data.user_id
}
