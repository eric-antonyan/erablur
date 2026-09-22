import pymongo
from app.db.database import db                                   

def run_flatten():
    print("🚀 Starting database flattening...")
    count = 0
    
                                                         
    for hero in db.heroes.find():
                                                                                
        if 'name' in hero:
            update = {
                "first_name": hero['name'].get('first', ''),
                "last_name": hero['name'].get('last', ''),
                "birth_date": hero.get('date', {}).get('birth', ''),
                "death_date": hero.get('date', {}).get('dead', '')
            }
            
                                                                                  
            db.heroes.update_one(
                {"_id": hero["_id"]}, 
                {
                    "$set": update, 
                    "$unset": {"name": "", "date": ""}
                }
            )
            count += 1
            print(f"✅ Flattened: {update['first_name']} {update['last_name']}")

    print(f"🏁 Done! Processed {count} heroes.")

if __name__ == "__main__":
    run_flatten()