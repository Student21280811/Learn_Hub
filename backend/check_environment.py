#!/usr/bin/env python3
"""
LearnHub Environment Diagnostic Tool
=====================================
Checks Python environment, package installations, and .env configuration.

Usage:
    python check_environment.py
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import importlib.metadata
from importlib import import_module

# ANSI color codes for better output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def print_header(text: str):
    """Print a formatted section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


# ==================== ENVIRONMENT CHECKS ====================

def check_python_version() -> Tuple[bool, str]:
    """Check Python version (should be 3.11+)"""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    
    if version.major >= 3 and version.minor >= 11:
        return True, f"Python {version_str}"
    else:
        return False, f"Python {version_str} (3.11+ recommended)"

def check_virtual_env() -> Tuple[bool, str]:
    """Check if running in a virtual environment"""
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if in_venv:
        venv_path = sys.prefix
        return True, f"Active virtual environment: {venv_path}"
    else:
        return False, "Not running in a virtual environment"

def check_venv_exists() -> Tuple[bool, str]:
    """Check if venv directory exists"""
    backend_dir = Path(__file__).parent
    venv_path = backend_dir / 'venv'
    
    if venv_path.exists() and venv_path.is_dir():
        return True, f"Virtual environment found at: {venv_path}"
    else:
        return False, "Virtual environment directory not found"


# ==================== PACKAGE CHECKS ====================

def load_requirements() -> Dict[str, str]:
    """Load and parse requirements.txt"""
    backend_dir = Path(__file__).parent
    req_file = backend_dir / 'requirements.txt'
    
    requirements = {}
    
    if not req_file.exists():
        print_error(f"requirements.txt not found at {req_file}")
        return requirements
    
    with open(req_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '==' in line:
                    package, version = line.split('==')
                    requirements[package.strip()] = version.strip()
    
    return requirements

def check_package_installed(package_name: str, required_version: str) -> Tuple[bool, str, Optional[str]]:
    """Check if a package is installed and get its version"""
    try:
        # Handle package name variations
        package_lookup = {
            'python-dotenv': 'dotenv',
            'python-jose': 'jose',
            'python-multipart': 'multipart',
            'python-dateutil': 'dateutil',
            'python-http-client': 'http_client'
        }
        
        check_name = package_lookup.get(package_name, package_name)
        
        # Try to get installed version
        try:
            installed_version = importlib.metadata.version(package_name)
        except importlib.metadata.PackageNotFoundError:
            installed_version = importlib.metadata.version(check_name)
        
        # Check if version matches
        if installed_version == required_version:
            return True, installed_version, None
        else:
            return True, installed_version, f"Expected {required_version}, got {installed_version}"
    
    except Exception as e:
        return False, None, f"Not installed: {str(e)}"

def check_critical_imports() -> Dict[str, Tuple[bool, str]]:
    """Check if critical packages used in server.py can be imported"""
    critical_packages = {
        'fastapi': 'FastAPI',
        'motor': 'Motor (MongoDB async driver)',
        'dotenv': 'python-dotenv',
        'passlib': 'Passlib (password hashing)',
        'jose': 'python-jose (JWT)',
        'pydantic': 'Pydantic',
        'sendgrid': 'SendGrid',
        'reportlab': 'ReportLab (PDF generation)',
        'openai': 'OpenAI',
        'stripe': 'Stripe'
    }
    
    results = {}
    
    for module_name, display_name in critical_packages.items():
        try:
            import_module(module_name)
            results[display_name] = (True, "Importable")
        except ImportError as e:
            results[display_name] = (False, f"Import failed: {str(e)}")
    
    return results


# ==================== ENV FILE CHECKS ====================

def check_env_file_exists() -> Tuple[bool, Path]:
    """Check if .env file exists"""
    backend_dir = Path(__file__).parent
    env_file = backend_dir / '.env'
    
    return env_file.exists(), env_file

def load_env_file() -> Dict[str, str]:
    """Load .env file and return variables"""
    backend_dir = Path(__file__).parent
    env_file = backend_dir / '.env'
    
    if not env_file.exists():
        return {}
    
    env_vars = {}
    
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars

def verify_dotenv_loading() -> Tuple[bool, str]:
    """Test if python-dotenv actually loads the .env file"""
    try:
        from dotenv import load_dotenv
        
        backend_dir = Path(__file__).parent
        env_file = backend_dir / '.env'
        
        # Load the .env file
        loaded = load_dotenv(env_file)
        
        if loaded:
            return True, "python-dotenv successfully loaded .env file"
        else:
            return False, "python-dotenv failed to load .env file"
    
    except Exception as e:
        return False, f"Error testing python-dotenv: {str(e)}"

def check_required_env_vars() -> Dict[str, Tuple[bool, str]]:
    """Check if required environment variables are set"""
    # Required for server.py to run
    required_vars = {
        'MONGO_URL': 'MongoDB connection string',
        'DB_NAME': 'Database name',
        'JWT_SECRET': 'JWT secret key',
        'CORS_ORIGINS': 'CORS allowed origins'
    }
    
    # Optional but recommended
    optional_vars = {
        'STRIPE_SECRET_KEY': 'Stripe payment integration',
        'SENDGRID_API_KEY': 'SendGrid email service',
        'SENDER_EMAIL': 'Email sender address',
        'EMERGENT_LLM_KEY': 'OpenAI API key for AI features',
        'ADMIN_COMMISSION': 'Admin commission percentage'
    }
    
    results = {}
    
    # Load .env file first (simulate server.py behavior)
    try:
        from dotenv import load_dotenv
        backend_dir = Path(__file__).parent
        load_dotenv(backend_dir / '.env')
    except Exception as e:
        print_warning(f"Could not load .env file: {e}")
    
    # Check required variables
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if value:
            # Mask sensitive values
            if any(secret in var.lower() for secret in ['secret', 'key', 'password']):
                display_value = f"Set ({len(value)} chars)"
            else:
                display_value = f"Set: {value[:50]}{'...' if len(value) > 50 else ''}"
            results[f"{var} (REQUIRED)"] = (True, display_value)
        else:
            results[f"{var} (REQUIRED)"] = (False, f"NOT SET - {description}")
    
    # Check optional variables
    for var, description in optional_vars.items():
        value = os.environ.get(var)
        if value:
            if any(secret in var.lower() for secret in ['secret', 'key', 'password']):
                display_value = f"Set ({len(value)} chars)"
            else:
                display_value = f"Set: {value[:50]}{'...' if len(value) > 50 else ''}"
            results[f"{var} (optional)"] = (True, display_value)
        else:
            results[f"{var} (optional)"] = (False, f"Not set - {description}")
    
    return results


# ==================== MAIN DIAGNOSTIC FUNCTION ====================

def run_diagnostics():
    """Run all diagnostic checks"""
    
    print(f"{Colors.BOLD}\nLearnHub Environment Diagnostic Tool{Colors.RESET}")
    print(f"{Colors.BOLD}Running comprehensive environment checks...{Colors.RESET}")
    
    issues_found = []
    warnings_found = []
    
    # ==================== Python Environment ====================
    print_header("Python Environment")
    
    success, msg = check_python_version()
    if success:
        print_success(msg)
    else:
        print_warning(msg)
        warnings_found.append("Python version < 3.11")
    
    success, msg = check_virtual_env()
    if success:
        print_success(msg)
    else:
        print_warning(msg)
        warnings_found.append("Not running in virtual environment")
    
    success, msg = check_venv_exists()
    if success:
        print_success(msg)
    else:
        print_warning(msg)
        warnings_found.append("Virtual environment directory not found")
    
    # ==================== Package Installation ====================
    print_header("Package Installation Check")
    
    requirements = load_requirements()
    print_info(f"Found {len(requirements)} packages in requirements.txt")
    
    # Check critical packages
    critical_packages = [
        'fastapi', 'motor', 'python-dotenv', 'passlib', 'python-jose',
        'pydantic', 'sendgrid', 'reportlab', 'openai', 'stripe', 'uvicorn'
    ]
    
    print(f"\n{Colors.BOLD}Critical Packages:{Colors.RESET}")
    for package in critical_packages:
        if package in requirements:
            success, version, error = check_package_installed(package, requirements[package])
            if success:
                if error:
                    print_warning(f"{package}: {version} {error}")
                    warnings_found.append(f"{package} version mismatch")
                else:
                    print_success(f"{package}=={version}")
            else:
                print_error(f"{package}: {error}")
                issues_found.append(f"{package} not installed")
        else:
            print_warning(f"{package}: Not in requirements.txt")
    
    # ==================== Import Test ====================
    print_header("Import Test")
    
    import_results = check_critical_imports()
    for package, (success, msg) in import_results.items():
        if success:
            print_success(f"{package}: {msg}")
        else:
            print_error(f"{package}: {msg}")
            issues_found.append(f"Cannot import {package}")
    
    # ==================== .env File Check ====================
    print_header(".env File Configuration")
    
    env_exists, env_path = check_env_file_exists()
    if env_exists:
        print_success(f".env file found at: {env_path}")
        
        # Load and display env vars
        env_vars = load_env_file()
        print_info(f"Found {len(env_vars)} variables in .env file")
        
        # Test python-dotenv loading
        success, msg = verify_dotenv_loading()
        if success:
            print_success(msg)
        else:
            print_error(msg)
            issues_found.append("python-dotenv loading failed")
    else:
        print_error(f".env file NOT FOUND at: {env_path}")
        issues_found.append(".env file missing")
        print_warning("Create .env file using the template provided in previous analysis")
    
    # ==================== Environment Variables ====================
    print_header("Environment Variables")
    
    env_var_results = check_required_env_vars()
    
    for var, (success, msg) in env_var_results.items():
        if success:
            print_success(f"{var}: {msg}")
        else:
            if "REQUIRED" in var:
                print_error(f"{var}: {msg}")
                issues_found.append(f"Required env var {var.split()[0]} not set")
            else:
                print_warning(f"{var}: {msg}")
    
    # ==================== Summary ====================
    print_header("Summary")
    
    if not issues_found and not warnings_found:
        print_success("✓ All checks passed! Your environment is properly configured.")
        print_info("\nYou can now run the server with:")
        print(f"  {Colors.BOLD}uvicorn server:app --reload --port 8001{Colors.RESET}")
    else:
        if issues_found:
            print(f"\n{Colors.RED}{Colors.BOLD}Critical Issues Found ({len(issues_found)}):{Colors.RESET}")
            for i, issue in enumerate(issues_found, 1):
                print(f"  {i}. {issue}")
        
        if warnings_found:
            print(f"\n{Colors.YELLOW}{Colors.BOLD}Warnings ({len(warnings_found)}):{Colors.RESET}")
            for i, warning in enumerate(warnings_found, 1):
                print(f"  {i}. {warning}")
        
        print(f"\n{Colors.BOLD}Recommended Actions:{Colors.RESET}")
        
        if any("not installed" in issue for issue in issues_found):
            print(f"  1. Install missing packages:")
            print(f"     {Colors.BOLD}pip install -r requirements.txt{Colors.RESET}")
        
        if any(".env" in issue for issue in issues_found):
            print(f"  2. Create .env file:")
            print(f"     Copy the backend_env_template.txt to backend/.env")
            print(f"     Then update with your actual configuration values")
        
        if any("env var" in issue for issue in issues_found):
            print(f"  3. Add missing environment variables to .env file")
        
        if warnings_found and not issues_found:
            print(f"  {Colors.YELLOW}Warnings can be addressed but won't prevent server from running{Colors.RESET}")
    
    print()  # Final newline

if __name__ == "__main__":
    try:
        run_diagnostics()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Diagnostic interrupted by user{Colors.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {str(e)}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
