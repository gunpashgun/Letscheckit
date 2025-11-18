"""Выполнение миграции через Supabase."""
import os
import subprocess
from dotenv import load_dotenv

load_dotenv()

def run_migration():
    """Выполняет миграцию через psql или показывает инструкции."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL и SUPABASE_SERVICE_ROLE_KEY должны быть установлены")
        return
    
    # Извлекаем connection string из URL
    # Формат: https://xxx.supabase.co
    # Нужен: postgresql://postgres:[password]@db.xxx.supabase.co:5432/postgres
    
    # Читаем SQL миграцию
    with open("migrations/003_detailed_analysis.sql", "r") as f:
        sql = f.read()
    
    print("📋 SQL миграция:")
    print("=" * 60)
    print(sql)
    print("=" * 60)
    print("\n⚠️  Выполните этот SQL в Supabase Dashboard:")
    print("   1. Откройте https://supabase.com/dashboard")
    print("   2. Выберите ваш проект")
    print("   3. Перейдите в SQL Editor")
    print("   4. Вставьте SQL выше и выполните")
    print("\nИли используйте psql:")
    print("   psql 'postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres' -f migrations/003_detailed_analysis.sql")

if __name__ == "__main__":
    run_migration()


