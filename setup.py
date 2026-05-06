import os
import shutil
from datetime import datetime

def get_timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def backup_if_exists(filepath):
    if os.path.exists(filepath):
        backup_path = f"{filepath}_{get_timestamp()}.bck"
        shutil.copy2(filepath, backup_path)
        return True
    return False

def load_existing_env(filepath):
    """Loads data from an existing .env file into a dictionary."""
    env_data = {}
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        key, value = parts
                        env_data[key.strip()] = value.strip()
    return env_data

def smart_input(prompt, current_value):
    """Asks for input: keeps current if ENTER is pressed, updates if new value is provided."""
    if current_value:
        print(f"   [Current]: {current_value}")
        choice = input(f"   {prompt} (Press ENTER to keep, or type new value): ").strip()
        return choice if choice else current_value
    else:
        return input(f"   {prompt}: ").strip()

def run_wizard():
    print("="*65)
    print("🚀 MIKE 'FOR DUMMIES' - INTELLIGENT 60-SECOND SETUP")
    print("="*65)

    backend_env = "backend/.env"
    frontend_env = "frontend/.env.local"
    
    # Merge data from both .env files to ensure we have everything
    existing_vars = load_existing_env(backend_env)
    existing_vars.update(load_existing_env(frontend_env))

    # --- 1. SUPABASE ---
    print("\n[STEP 1: SUPABASE CONFIGURATION]")
    
    # Try to find URL in both formats
    sb_url = existing_vars.get('SUPABASE_URL') or existing_vars.get('NEXT_PUBLIC_SUPABASE_URL')
    new_sb_url = smart_input("Project URL", sb_url)

    # Try to find Anon Key
    sb_anon = existing_vars.get('NEXT_PUBLIC_SUPABASE_ANON_KEY') or existing_vars.get('SUPABASE_ANON_KEY')
    new_sb_anon = smart_input("Anon Key", sb_anon)

    # Try to find Service Role Key
    sb_secret = existing_vars.get('SUPABASE_SECRET_KEY') or existing_vars.get('SUPABASE_SERVICE_ROLE_KEY')
    new_sb_secret = smart_input("Service Role Key (Secret)", sb_secret)

    # --- 2. STORAGE ---
    print("\n[STEP 2: CLOUDFLARE R2 STORAGE]")
    
    r2_end = existing_vars.get('R2_ENDPOINT_URL')
    new_r2_end = smart_input("R2 Endpoint URL", r2_end)
    if ".com/" in new_r2_end:
        new_r2_end = new_r2_end.split(".com/")[0] + ".com"
        print("      -> Auto-fixed: Bucket name removed from URL.")

    new_r2_bucket = smart_input("Bucket Name", existing_vars.get('R2_BUCKET_NAME') or "legal-mike")
    new_r2_access = smart_input("R2 Access Key ID", existing_vars.get('R2_ACCESS_KEY_ID'))
    new_r2_secret = smart_input("R2 Secret Access Key", existing_vars.get('R2_SECRET_ACCESS_KEY'))

    # --- 3. AI & EXTRA ---
    print("\n[STEP 3: AI & OBSIDIAN]")
    
    new_gemini = smart_input("Gemini API Key (Leave empty if local)", existing_vars.get('GEMINI_API_KEY'))
    new_obsidian = smart_input("Obsidian Vault Path (Optional)", existing_vars.get('OBSIDIAN_PATH'))

    # --- FINALIZING ---
    print("\n[STEP 4: SAVING CONFIGURATION]")
    
    # Backups
    if backup_if_exists(backend_env): print(f"   Backed up: {backend_env}")
    if backup_if_exists(frontend_env): print(f"   Backed up: {frontend_env}")

    # Write Backend .env
    with open(backend_env, "w") as f:
        f.write(f"SUPABASE_URL={new_sb_url}\n")
        f.write(f"SUPABASE_SECRET_KEY={new_sb_secret}\n")
        f.write(f"R2_ENDPOINT_URL={new_r2_end}\n")
        f.write(f"R2_BUCKET_NAME={new_r2_bucket}\n")
        f.write(f"R2_ACCESS_KEY_ID={new_r2_access}\n")
        f.write(f"R2_SECRET_ACCESS_KEY={new_r2_secret}\n")
        f.write(f"GEMINI_API_KEY={new_gemini}\n")
        f.write(f"OBSIDIAN_PATH={new_obsidian}\n")
        f.write("R2_REGION=auto\n")

    # Write Frontend .env.local
    with open(frontend_env, "w") as f:
        f.write(f"NEXT_PUBLIC_SUPABASE_URL={new_sb_url}\n")
        f.write(f"NEXT_PUBLIC_SUPABASE_ANON_KEY={new_sb_anon}\n")

    print("\n" + "="*65)
    print("✅ DONE! Files updated. Run 'docker-compose up --build' now.")
    print("="*65)

if __name__ == "__main__":
    run_wizard()