import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL; 
const supabaseAnonkey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonkey) { 
  console.warn('Supabase credentials are missing from environment variables. ');  
  supabase = null;  // Avoid creating the Supabase client when credentials are missing to prevent hard-to-debug runtime errors.
}  
else { 
  supabase = createClient(supabaseUrl , supabaseAnonkey) // create a supabase client if both the credentials are provided 
}

export { supabase }