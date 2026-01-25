import dns.resolver
import os
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

def get_standard_connection_string():
    env_path = 'f:/VPS-Error-main/VPS-Error-main/backend/.env'
    load_dotenv(env_path)
    
    mongo_url = os.environ.get('MONGO_URL')
    if not mongo_url or not mongo_url.startswith('mongodb+srv://'):
        print("❌ Not a mongodb+srv connection string or already fixed.")
        return

    print(f"Original URL: {mongo_url}")
    
    try:
        # Parse credentials and host
        parts = mongo_url.replace('mongodb+srv://', '').split('@')
        creds = parts[0]
        remaining = parts[1].split('/')
        host = remaining[0]
        
        # Get SRV records
        print(f"Resolving SRV records for {host}...")
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ['8.8.8.8', '8.8.4.4', '1.1.1.1']
        resolver.timeout = 10
        resolver.lifetime = 10
        
        srv_records = resolver.resolve(f'_mongodb._tcp.{host}', 'SRV')
        shards = [str(r.target).rstrip('.') + ':' + str(r.port) for r in srv_records]
        
        # Get TXT records (for replicaSet)
        try:
            txt_records = resolver.resolve(host, 'TXT')
            txt_data = str(txt_records[0].strings[0], 'utf-8')
            print(f"TXT Data: {txt_data}")
        except:
            txt_data = "replicaSet=atlas-xxxx-shard-0"
            print("⚠️ Could not resolve TXT record, using default replicaSet guess.")

        # Construct standard string
        shard_string = ','.join(shards)
        db_name = os.environ.get('DB_NAME', 'learnhub')
        
        # Build the final standard URL
        new_url = f"mongodb://{creds}@{shard_string}/{db_name}?ssl=true&authSource=admin&{txt_data}"
        
        # Add other params from original URL if any
        if '?' in mongo_url:
            params = mongo_url.split('?')[1]
            if 'appName=' in params:
                new_url += f"&{params}"

        print(f"\n✅ Generated Standard Connection String:\n{new_url}\n")
        
        # Write back to .env
        with open(env_path, 'r') as f:
            lines = f.readlines()
            
        with open(env_path, 'w') as f:
            for line in lines:
                if line.startswith('MONGO_URL='):
                    f.write(f"MONGO_URL={new_url}\n")
                else:
                    f.write(line)
                    
        print(f"🚀 Successfully updated {env_path}")
        print("Please try running uvicorn again!")

    except Exception as e:
        print(f"❌ Error while converting connection string: {e}")

if __name__ == "__main__":
    get_standard_connection_string()
