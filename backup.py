from pathlib import Path
from datetime import datetime
import shutil
from config import DB_PATH, BACKUP_DIR

def create_backup():
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    if not Path(DB_PATH).exists():
        return None
    name = "backup_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".db"
    target = Path(BACKUP_DIR) / name
    shutil.copy2(DB_PATH, target)
    return str(target)
