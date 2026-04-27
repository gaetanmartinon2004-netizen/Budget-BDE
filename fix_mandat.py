#!/usr/bin/env python
"""Fix mandat deletion and UI issues."""
import re

def fix_app_js():
    """Fix app.js functions."""
    with open('app/frontend/static/js/app.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix getSelectedMandatFromManager to be more robust
    old_pattern = r'getSelectedMandatFromManager\(\) \{[^}]*?return this\.mandats\.find\(\(m\) => Number\(m\.id\) === selectedId\) \|\| null;[^}]*?\}'
    
    new_func = '''getSelectedMandatFromManager() {
        const select = document.getElementById('mandat-select');
        if (!select || !select.value) {
            // Fallback: retourner le premier mandat actif ou le premier mandat
            const active = this.mandats.find((m) => m.active);
            return active || this.mandats[0] || null;
        }
        const selectedId = Number(select.value);
        if (!Number.isFinite(selectedId) || selectedId <= 0) {
            const active = this.mandats.find((m) => m.active);
            return active || this.mandats[0] || null;
        }
        const found = this.mandats.find((m) => Number(m.id) === selectedId);
        if (!found && this.mandats.length > 0) {
            return this.mandats[0];
        }
        return found || null;
    }'''
    
    # Find and replace more precisely
    start = content.find('getSelectedMandatFromManager() {')
    if start != -1:
        # Find the closing brace of the function
        brace_count = 0
        i = start + len('getSelectedMandatFromManager()')
        while i < len(content):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break
            i += 1
        
        if i < len(content):
            content = content[:start] + new_func + content[end:]
            print("✓ getSelectedMandatFromManager fixed")
    
    with open('app/frontend/static/js/app.js', 'w', encoding='utf-8') as f:
        f.write(content)

def fix_build_bat():
    """Fix build.bat to avoid creating empty DB files."""
    with open('build.bat', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the section that creates empty files and remove it
    old_section = '''for %%F in ("data\\budget.db" "data\\mandats.db") do (
    if exist "%%~fF" (
        copy /Y "%%~fF" "%DIST_DIR%\\%%~nxF" >nul
        if exist "%%~fF-wal" copy /Y "%%~fF-wal" "%DIST_DIR%\\%%~nxF-wal" >nul
        if exist "%%~fF-shm" copy /Y "%%~fF-shm" "%DIST_DIR%\\%%~nxF-shm" >nul
    ) else (
        type nul > "%DIST_DIR%\\%%~nxF"
    )
)'''
    
    new_section = '''for %%F in ("data\\budget.db" "data\\mandats.db") do (
    if exist "%%~fF" (
        copy /Y "%%~fF" "%DIST_DIR%\\%%~nxF" >nul
        if exist "%%~fF-wal" copy /Y "%%~fF-wal" "%DIST_DIR%\\%%~nxF-wal" >nul
        if exist "%%~fF-shm" copy /Y "%%~fF-shm" "%DIST_DIR%\\%%~nxF-shm" >nul
    )
)'''
    
    content = content.replace(old_section, new_section)
    print("✓ build.bat fixed - removed empty DB file creation")
    
    with open('build.bat', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    fix_app_js()
    fix_build_bat()
    print("✓ All fixes applied!")
