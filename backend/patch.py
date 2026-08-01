import os
import glob
import re

files = glob.glob('p:/PROJECTS/DATA ANALYST COPILOT/backend/routes/*.py')
for f in files:
    with open(f, 'r', encoding="utf-8") as file:
        content = file.read()
    
    if any(x in f for x in ['upload.py', 'chat.py', 'profile.py']):
        continue
        
    print(f"Processing {f}")
    
    if "get_current_user" not in content:
        content = content.replace("from fastapi import APIRouter", "from fastapi import APIRouter, Depends\nfrom services.auth_service import get_current_user")
        
    # Add current_user to endpoints
    content = re.sub(r'async def ([a-zA-Z0-9_]+)\(([^)]*dataset_id[^)]*)\):', r'async def \1(\2, current_user = Depends(get_current_user)):', content)
    
    # Add uid to get_dataframe
    content = re.sub(r'get_dataframe\((.*?dataset_id.*?)\)', r'get_dataframe(\1, current_user.uid)', content)

    with open(f, 'w', encoding="utf-8") as file:
        file.write(content)
print("Done patching.")
