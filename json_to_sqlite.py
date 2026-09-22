import json
import sqlite3
import os
import uuid
from datetime import datetime
from typing import Dict, List, Any

def create_tables(conn: sqlite3.Connection):
    """Create all necessary tables"""
    cursor = conn.cursor()
    
                  
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS heroes (
            id TEXT PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            birth_date TEXT,
            death_date TEXT,
            region TEXT,
            war TEXT,
            img_url TEXT,
            bio_link TEXT,
            bio TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
                 
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            search_count INTEGER DEFAULT 0,
            last_query TEXT,
            joined_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    ''')
    
                          
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            query TEXT NOT NULL,
            hero_id TEXT,
            hero_name TEXT,
            searched_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (hero_id) REFERENCES heroes(id)
        )
    ''')
    
                              
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            channel_id INTEGER PRIMARY KEY,
            title TEXT,
            owner_id TEXT NOT NULL,
            connected_at TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users(id)
        )
    ''')
    
                      
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP
        )
    ''')
    
                                           
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_heroes_name ON heroes(first_name, last_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_heroes_war ON heroes(war)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_user ON search_history(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_time ON search_history(searched_at)')
    
    conn.commit()
    print("✅ Tables created successfully")

def convert_json_to_sqlite(json_file_path: str, sqlite_db_path: str):
    """
    Convert JSON file to SQLite database
    
    Args:
        json_file_path: Path to the JSON file containing heroes data
        sqlite_db_path: Path where SQLite database will be created
    """
    
                               
    if not os.path.exists(json_file_path):
        print(f"❌ JSON file not found: {json_file_path}")
        return False
    
                    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            heroes_data = json.load(f)
        print(f"✅ Loaded {len(heroes_data)} heroes from JSON")
    except Exception as e:
        print(f"❌ Error loading JSON: {e}")
        return False
    
                                                     
    os.makedirs(os.path.dirname(sqlite_db_path), exist_ok=True)
    
                                
    conn = sqlite3.connect(sqlite_db_path)
    conn.row_factory = sqlite3.Row
    
    try:
                       
        create_tables(conn)
        
        cursor = conn.cursor()
        
                       
        success_count = 0
        error_count = 0
        
        for hero in heroes_data:
            try:
                                                     
                hero_id = hero.get('_id', str(uuid.uuid4()))
                if isinstance(hero_id, dict) and '$oid' in hero_id:
                    hero_id = hero_id['$oid']
                else:
                    hero_id = str(hero_id)
                
                              
                name = hero.get('name', {})
                first_name = name.get('first', '')
                last_name = name.get('last', '')
                
                date = hero.get('date', {})
                birth_date = date.get('birth', '')
                death_date = date.get('dead', '')
                
                region = hero.get('region', '')
                war = hero.get('war', '')
                img_url = hero.get('img_url', '')
                bio_link = hero.get('bio_link', '')
                bio = hero.get('bio', '')
                
                                        
                cursor.execute('''
                    INSERT OR REPLACE INTO heroes 
                    (id, first_name, last_name, birth_date, death_date, region, war, img_url, bio_link, bio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (hero_id, first_name, last_name, birth_date, death_date, region, war, img_url, bio_link, bio))
                
                success_count += 1
                
            except Exception as e:
                error_count += 1
                print(f"⚠️ Error inserting hero {hero.get('name', {}).get('first', 'Unknown')}: {e}")
        
        conn.commit()
        
        print(f"\n📊 Conversion Summary:")
        print(f"   ✅ Successfully inserted: {success_count} heroes")
        print(f"   ⚠️ Errors: {error_count}")
        print(f"   📁 Database saved to: {sqlite_db_path}")
        
                     
        cursor.execute('SELECT COUNT(*) as count FROM heroes')
        count = cursor.fetchone()['count']
        print(f"   📊 Total heroes in database: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        return False
    finally:
        conn.close()

def merge_json_to_sqlite(json_file_path: str, sqlite_db_path: str, overwrite: bool = False):
    """
    Merge JSON data into existing SQLite database
    
    Args:
        json_file_path: Path to JSON file
        sqlite_db_path: Path to SQLite database
        overwrite: If True, overwrite existing heroes with same ID
    """
    
    if not os.path.exists(json_file_path):
        print(f"❌ JSON file not found: {json_file_path}")
        return False
    
                    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            heroes_data = json.load(f)
        print(f"✅ Loaded {len(heroes_data)} heroes from JSON")
    except Exception as e:
        print(f"❌ Error loading JSON: {e}")
        return False
    
                              
    db_exists = os.path.exists(sqlite_db_path)
    
                         
    conn = sqlite3.connect(sqlite_db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        if not db_exists:
            create_tables(conn)
        
        cursor = conn.cursor()
        
                                            
        existing_ids = set()
        if not overwrite:
            cursor.execute('SELECT id FROM heroes')
            existing_ids = {row['id'] for row in cursor.fetchall()}
            print(f"📊 Found {len(existing_ids)} existing heroes in database")
        
                              
        inserted = 0
        updated = 0
        skipped = 0
        
        for hero in heroes_data:
            try:
                                    
                hero_id = hero.get('_id', str(uuid.uuid4()))
                if isinstance(hero_id, dict) and '$oid' in hero_id:
                    hero_id = hero_id['$oid']
                else:
                    hero_id = str(hero_id)
                
                                 
                if hero_id in existing_ids and not overwrite:
                    skipped += 1
                    continue
                
                              
                name = hero.get('name', {})
                first_name = name.get('first', '')
                last_name = name.get('last', '')
                
                date = hero.get('date', {})
                birth_date = date.get('birth', '')
                death_date = date.get('dead', '')
                
                region = hero.get('region', '')
                war = hero.get('war', '')
                img_url = hero.get('img_url', '')
                bio_link = hero.get('bio_link', '')
                bio = hero.get('bio', '')
                
                                   
                cursor.execute('''
                    INSERT OR REPLACE INTO heroes 
                    (id, first_name, last_name, birth_date, death_date, region, war, img_url, bio_link, bio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (hero_id, first_name, last_name, birth_date, death_date, region, war, img_url, bio_link, bio))
                
                if hero_id in existing_ids:
                    updated += 1
                else:
                    inserted += 1
                
            except Exception as e:
                print(f"⚠️ Error processing hero: {e}")
        
        conn.commit()
        
        print(f"\n📊 Merge Summary:")
        print(f"   ✅ Inserted: {inserted} new heroes")
        print(f"   🔄 Updated: {updated} existing heroes")
        print(f"   ⏭️ Skipped: {skipped} existing heroes")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during merge: {e}")
        return False
    finally:
        conn.close()

def export_sqlite_to_json(sqlite_db_path: str, json_output_path: str):
    """
    Export SQLite database back to JSON format
    
    Args:
        sqlite_db_path: Path to SQLite database
        json_output_path: Path where JSON file will be saved
    """
    
    if not os.path.exists(sqlite_db_path):
        print(f"❌ SQLite database not found: {sqlite_db_path}")
        return False
    
    conn = sqlite3.connect(sqlite_db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM heroes ORDER BY first_name, last_name')
        
        heroes = []
        for row in cursor.fetchall():
            hero = {
                "name": {
                    "first": row['first_name'],
                    "last": row['last_name']
                },
                "date": {
                    "birth": row['birth_date'],
                    "dead": row['death_date']
                },
                "region": row['region'],
                "war": row['war'],
                "img_url": row['img_url'],
                "bio_link": row['bio_link'],
                "bio": row['bio']
            }
            heroes.append(hero)
        
                      
        os.makedirs(os.path.dirname(json_output_path), exist_ok=True)
        with open(json_output_path, 'w', encoding='utf-8') as f:
            json.dump(heroes, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Exported {len(heroes)} heroes to {json_output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error exporting to JSON: {e}")
        return False
    finally:
        conn.close()

def verify_database(sqlite_db_path: str):
    """Verify database integrity and show statistics"""
    
    if not os.path.exists(sqlite_db_path):
        print(f"❌ Database not found: {sqlite_db_path}")
        return
    
    conn = sqlite3.connect(sqlite_db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        cursor = conn.cursor()
        
                        
        cursor.execute('SELECT COUNT(*) as count FROM heroes')
        total_heroes = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(DISTINCT war) as count FROM heroes WHERE war != ""')
        total_wars = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(DISTINCT region) as count FROM heroes WHERE region != ""')
        total_regions = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM heroes WHERE bio != ""')
        heroes_with_bio = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM heroes WHERE img_url != ""')
        heroes_with_image = cursor.fetchone()['count']
        
        print("\n📊 Database Statistics:")
        print(f"   🦸 Total Heroes: {total_heroes}")
        print(f"   ⚔️ Unique Wars: {total_wars}")
        print(f"   📍 Unique Regions: {total_regions}")
        print(f"   📝 Heroes with Bio: {heroes_with_bio}")
        print(f"   🖼️ Heroes with Image: {heroes_with_image}")
        
                          
        print("\n📋 Sample Heroes:")
        cursor.execute('SELECT first_name, last_name, war FROM heroes LIMIT 5')
        for row in cursor.fetchall():
            print(f"   • {row['first_name']} {row['last_name']} - {row['war']}")
        
    except Exception as e:
        print(f"❌ Error verifying database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert JSON to SQLite for Armenian Heroes Bot')
    parser.add_argument('--json', default='data/heroes.json', help='Path to JSON file')
    parser.add_argument('--db', default='data/heroes.db', help='Path to SQLite database')
    parser.add_argument('--merge', action='store_true', help='Merge with existing database')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing heroes')
    parser.add_argument('--export', help='Export SQLite to JSON file')
    parser.add_argument('--verify', action='store_true', help='Verify database integrity')
    
    args = parser.parse_args()
    
    if args.export:
                     
        export_sqlite_to_json(args.db, args.export)
    elif args.verify:
                     
        verify_database(args.db)
    elif args.merge:
                    
        merge_json_to_sqlite(args.json, args.db, args.overwrite)
    else:
                          
        convert_json_to_sqlite(args.json, args.db)