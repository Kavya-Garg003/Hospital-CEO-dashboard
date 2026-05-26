@echo off
REM ============================================================
REM  Database Initialization Script
REM  Creates tables + seeds 2000 patient records
REM ============================================================
echo.
echo  [init_db] Installing Python dependencies...
cd backend
pip install -r requirements.txt

echo.
echo  [init_db] Generating RSA keys for JWT...
if not exist "keys" mkdir keys
if not exist "keys\private.pem" (
    openssl genrsa -out keys\private.pem 2048
    openssl rsa -in keys\private.pem -pubout -out keys\public.pem
    echo  [init_db] RSA keys generated.
) else (
    echo  [init_db] RSA keys already exist.
)

echo.
echo  [init_db] Generating encryption key...
python -c "import secrets; key=secrets.token_hex(32); print('ENCRYPTION_KEY='+key)" >> .env.new
echo  [init_db] Add the ENCRYPTION_KEY from .env.new to your .env file

echo.
echo  [init_db] Seeding database with synthetic data...
python seed_data.py --records 2000

echo.
echo  [init_db] Building RAG index (ChromaDB)...
python -c "from rag.embedder import build_index; build_index(); print('RAG index built.')"

echo.
echo  ============================================================
echo   Database initialized!
echo   CEO Login: username=ceo, password=Aarogya@2024
echo  ============================================================
pause
