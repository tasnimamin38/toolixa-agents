import requests
from bs4 import BeautifulSoup
import json
import sys

def scrape_website(url):
    print(f"🔍 এজেন্ট স্ক্র্যাপিং শুরু করছে: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # টাইটেল এবং সব লিঙ্ক বের করা
        data = {
            "url": url,
            "title": soup.title.string if soup.title else "No Title",
            "links": [a['href'] for a in soup.find_all('a', href=True)][:10] # প্রথম ১০টি লিঙ্ক
        }
        
        # ডেটা সেভ করা
        with open("output.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        print("✅ স্ক্র্যাপিং সফল! 'output.json' ফাইলে ডেটা সেভ হয়েছে।")
        print(f"📌 টাইটেল: {data['title']}")
        
    except Exception as e:
        print(f"❌ এরর: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
    else:
        target_url = input("🌐 ওয়েবসাইটের URL দিন: ")
    
    scrape_website(target_url)