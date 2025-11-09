"use client"

import { createBrowserClient } from '@supabase/ssr'

let client: ReturnType<typeof createBrowserClient> | null = null

export function createClient() {
  // Only create client in browser environment
  if (typeof window === 'undefined') {
    throw new Error('Supabase client can only be created in the browser. Use useState(() => createClient()) in your component.')
  }
  
  if (!client) {
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL
    const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    
    if (!url || !key) {
      throw new Error('Missing Supabase environment variables: NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY are required')
    }
    
    client = createBrowserClient(url, key)
  }
  
  return client
}

