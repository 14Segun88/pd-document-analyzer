from pathlib import Path
import subprocess
import sys

def main():
    target_file = Path(__file__).parent / 'web_app_v6_cot_fallback.py'
    if not target_file.exists():
        print(f"Error: {target_file} not found")
        sys.exit(1)

    # Use subprocess instead of exec() for better isolation and security
    try:
        subprocess.run([sys.executable, str(target_file)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Server exited with error: {e}")
    except KeyboardInterrupt:
        print("\nServer stopped by user")

if __name__ == "__main__":
    main()
