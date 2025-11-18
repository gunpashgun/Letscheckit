"""Выполнение миграции через прямой SQL запрос к Supabase."""
import os
import httpx
import json
from dotenv import load_dotenv

load_dotenv()

def execute_migration():
    """Выполняет миграцию через Supabase REST API."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL и SUPABASE_SERVICE_ROLE_KEY должны быть установлены")
        return False
    
    # Читаем SQL миграцию
    with open("migrations/003_detailed_analysis.sql", "r") as f:
        sql = f.read()
    
    print("Выполняю миграцию через Supabase...")
    
    # Пробуем выполнить через PostgREST с использованием функции
    # Но сначала нужно создать функцию в БД
    
    # Альтернатива: выполняем команды по одной через ALTER TABLE
    # Но Supabase REST API не поддерживает DDL команды
    
    # Единственный способ - использовать Supabase Management API
    # Или выполнить через psql
    
    # Пробуем через прямой HTTP запрос к Supabase
    # Используя специальный endpoint (если существует)
    
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
    }
    
    # Пробуем выполнить через rpc endpoint
    # Но нужна функция в БД
    
    # Пробуем через Supabase Management API
    project_ref = supabase_url.split("//")[1].split(".")[0]
    
    # Management API требует отдельный ключ
    # Попробуем через прямой SQL запрос
    
    # Разбиваем SQL на команды
    commands = []
    current_command = ""
    
    for line in sql.split("\n"):
        line = line.strip()
        if not line or line.startswith("--"):
            continue
        current_command += line + " "
        if line.endswith(";"):
            commands.append(current_command.strip())
            current_command = ""
    
    print(f"Найдено {len(commands)} SQL команд")
    
    # Пробуем выполнить каждую команду через PostgREST
    # Но ALTER TABLE не поддерживается
    
    # Единственный способ - выполнить вручную
    print("\n⚠️  Supabase REST API не поддерживает выполнение DDL команд")
    print("Выполните SQL в Supabase Dashboard -> SQL Editor")
    print("\nSQL миграция:")
    print("=" * 60)
    print(sql)
    print("=" * 60)
    
    return False

if __name__ == "__main__":
    execute_migration()

