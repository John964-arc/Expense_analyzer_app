import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://bkjtyuzndsaeplwhdicn.supabase.co'
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJranR5dXpuZHNhZXBsd2hkaWNuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY4NzcyMDQsImV4cCI6MjA5MjQ1MzIwNH0.Dv7OUthB8ZhqrABkadMIrpDxS5tU71Yngt0sIq-ml1w'

export const supabase = createClient(
    supabaseUrl,
    supabaseKey
)

// Re-applying the fix: Wrapping in functions to avoid 'data' redeclaration errors
export const signUp = async (email, password) => {
    const { data, error } = await supabase.auth.signUp({
        email,
        password
    })
    return { data, error }
}

export const signIn = async (email, password) => {
    const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password
    })
    return { data, error }
}