import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_NEXT_PUBLIC_SUPABASE_URL; 
const supabaseAnonkey = import.meta.env.VITE_NEXT_ANON_KEY

if (!supabaseUrl || !supabaseAnonkey) { 
  console.warn('Supabase credentials are missing from enviroment variables. '); 
} 

export const supabase = createClient(supabaseUrl, supabaseAnonkey); 