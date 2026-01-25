import asyncio
import os
import dns.resolver
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv('f:/VPS-Error-main/VPS-Error-main/backend/.env')

async def diagnose_dns():
    mongo_url = os.environ.get('MONGO_URL')
    print(f"Testing connection for: {mongo_url}")
    
    # Extract host
    try:
        host = mongo_url.split('@')[1].split('/')[0].split('?')[0]
        print(f"Target host: {host}")
        
        print("\n--- DNS RESOLUTION TEST ---")
        # Try default resolver
        try:
            print("Trying default DNS resolver...")
            answers = dns.resolver.resolve(f"_mongodb._tcp.{host}", 'SRV')
            print(f"✅ Success! Found {len(answers)} shards.")
        except Exception as e:
            print(f"❌ Default DNS failed: {e}")
            
            # Try Google DNS directly
            print("\nTrying Google DNS (8.8.8.8) directly...")
            resolver = dns.resolver.Resolver()
            resolver.nameservers = ['8.8.8.8', '8.8.4.4']
            try:
                answers = resolver.resolve(f"_mongodb._tcp.{host}", 'SRV')
                print(f"✅ Google DNS Success! Found {len(answers)} shards.")
                print("Suggestion: Your local ISP DNS is blocking or timing out. Switching to Google DNS in your system settings will fix this permanently.")
            except Exception as ge:
                print(f"❌ Google DNS also failed: {ge}")

        print("\n--- MONGODB CLIENT TEST ---")
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
        await client.admin.command('ping')
        print("✅ MongoDB Ping Success!")
        
    except Exception as e:
        print(f"\n❌ Final Error: {e}")

if __name__ == "__main__":
    asyncio.run(diagnose_dns())
