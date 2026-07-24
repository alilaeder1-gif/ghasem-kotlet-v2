import asyncio
import json
import logging
import os
import shutil
import zipfile
from datetime import datetime

from database import db

# Off-site backup targets (set via env vars)
#   GITHUB_TOKEN=<pat> BACKUP_GITHUB_REPO=owner/repo  → upload as GitHub Release
#   BACKUP_S3_ENDPOINT=... BACKUP_S3_BUCKET=...       → S3-compatible (R2, B2, etc)
#   BACKUP_WEBHOOK_URL=...                             → POST to webhook

logger = logging.getLogger(__name__)

_BACKUP_DIR = None
_BACKUP_INTERVAL = 86400


def _ensure_dir() -> str:
    global _BACKUP_DIR
    if _BACKUP_DIR:
        return _BACKUP_DIR
    candidates = ["/data/backups", "/app/backups", "backups"]
    for d in candidates:
        try:
            os.makedirs(d, exist_ok=True)
            testf = os.path.join(d, ".write_test")
            with open(testf, "w") as f:
                f.write("ok")
            os.remove(testf)
            _BACKUP_DIR = d
            return d
        except:
            continue
    _BACKUP_DIR = "backups"
    os.makedirs(_BACKUP_DIR, exist_ok=True)
    return _BACKUP_DIR


async def _export_table_to_json(table: str) -> list[dict]:
    try:
        async with db.db.execute(f"SELECT * FROM {table}") as c:
            rows = await c.fetchall()
            return [dict(r) for r in rows]
    except:
        return []


async def _export_settings_json() -> dict:
    settings = {}
    try:
        async with db.db.execute("SELECT key, value FROM bot_settings") as c:
            for row in await c.fetchall():
                settings[row["key"]] = row["value"]
    except:
        pass
    return settings


async def create_backup() -> str | None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = _ensure_dir()
    zip_path = os.path.join(backup_dir, f"backup_{ts}.zip")
    tmp_dir = os.path.join(backup_dir, f"_tmp_{ts}")
    os.makedirs(tmp_dir, exist_ok=True)

    try:
        # 1. SQLite database file
        if db.resolved_path and os.path.exists(db.resolved_path):
            shutil.copy2(db.resolved_path, os.path.join(tmp_dir, "bot_data.db"))

        # 2. Export tables as JSON
        tables = [
            "offline_answers", "knowledge_base", "api_keys", "providers",
            "bot_settings", "ai_cache", "ai_log", "group_users",
            "group_settings", "bot_groups", "user_memory", "personality_sliders",
            "custom_commands", "auto_replies", "welcome_settings", "rules",
            "user_roles", "admin_log",
        ]
        table_counts = {}
        for table in tables:
            data = await _export_table_to_json(table)
            with open(os.path.join(tmp_dir, f"{table}.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, default=str)
            table_counts[table] = len(data)

        # 3. Settings as JSON
        with open(os.path.join(tmp_dir, "settings.json"), "w", encoding="utf-8") as f:
            json.dump(await _export_settings_json(), f, ensure_ascii=False, indent=2)

        # 4. Meta
        meta = {
            "created_at": ts,
            "version": "1.0",
            "tables": table_counts,
            "tables_count": sum(table_counts.values()),
        }
        with open(os.path.join(tmp_dir, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # 5. Create ZIP
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(tmp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, tmp_dir)
                    zf.write(file_path, arcname)

        # 6. Cleanup temp
        shutil.rmtree(tmp_dir, ignore_errors=True)

        # 7. Remove old backups (keep last 7)
        all_zips = sorted(
            [f for f in os.listdir(backup_dir) if f.startswith("backup_") and f.endswith(".zip")],
            reverse=True
        )
        for old in all_zips[7:]:
            try:
                os.remove(os.path.join(backup_dir, old))
                logger.info(f"Backup: removed old {old}")
            except:
                pass

        size_mb = round(os.path.getsize(zip_path) / (1024 * 1024), 2)
        logger.info(f"Backup: {zip_path} ({size_mb} MB, {meta['tables_count']} rows)")
        return zip_path
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None


async def _upload_to_github(zip_path: str) -> bool:
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("BACKUP_GITHUB_REPO", "")
    if not token or not repo:
        return False
    try:
        import requests
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        tag = f"backup-{ts}"
        # Create release
        r = requests.post(
            f"https://api.github.com/repos/{repo}/releases",
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"},
            json={"tag_name": tag, "name": f"Backup {ts}", "prerelease": True},
            timeout=30,
        )
        if r.status_code not in (201, 422):
            logger.warning(f"Backup: GitHub release failed ({r.status_code})")
            return False
        release_id = r.json().get("id")
        if not release_id:
            return False
        # Upload asset
        with open(zip_path, "rb") as f:
            r2 = requests.post(
                f"https://uploads.github.com/repos/{repo}/releases/{release_id}/assets?name=backup_{ts}.zip",
                headers={
                    "Authorization": f"token {token}",
                    "Content-Type": "application/zip",
                },
                data=f,
                timeout=60,
            )
        ok = r2.status_code == 201
        if ok:
            logger.info(f"Backup: uploaded to GitHub Release ({repo})")
        return ok
    except Exception as e:
        logger.warning(f"Backup: GitHub upload failed: {e}")
        return False


async def _upload_to_s3(zip_path: str) -> bool:
    endpoint = os.environ.get("BACKUP_S3_ENDPOINT", "")
    bucket = os.environ.get("BACKUP_S3_BUCKET", "")
    access_key = os.environ.get("BACKUP_S3_ACCESS_KEY", "")
    secret_key = os.environ.get("BACKUP_S3_SECRET_KEY", "")
    if not endpoint or not bucket:
        return False
    try:
        import boto3
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        key = f"backups/backup_{ts}.zip"
        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        client.upload_file(zip_path, bucket, key)
        logger.info(f"Backup: uploaded to S3 ({bucket}/{key})")
        return True
    except ImportError:
        logger.info("Backup: boto3 not installed, skipping S3 upload")
        return False
    except Exception as e:
        logger.warning(f"Backup: S3 upload failed: {e}")
        return False


async def _upload_to_webhook(zip_path: str) -> bool:
    url = os.environ.get("BACKUP_WEBHOOK_URL", "")
    if not url:
        return False
    try:
        import requests
        with open(zip_path, "rb") as f:
            r = requests.post(url, files={"backup": f}, timeout=60)
        if r.status_code < 500:
            logger.info(f"Backup: uploaded via webhook")
            return True
        return False
    except Exception as e:
        logger.warning(f"Backup: webhook upload failed: {e}")
        return False


async def upload_backup(zip_path: str):
    """Try all configured off-site targets."""
    uploaded = False
    if await _upload_to_github(zip_path):
        uploaded = True
    if await _upload_to_s3(zip_path):
        uploaded = True
    if await _upload_to_webhook(zip_path):
        uploaded = True
    if not uploaded:
        logger.info("Backup: no off-site target configured (local only)")


async def backup_worker():
    from handlers.distributed_lock import distributed_lock
    await asyncio.sleep(300)
    while True:
        try:
            locked = await distributed_lock.acquire("backup", ttl=600)
            if not locked:
                logger.debug("Backup: lock held by another replica, skipping")
            else:
                try:
                    path = await create_backup()
                    if path:
                        logger.info(f"Auto backup saved: {path}")
                        await upload_backup(path)
                    else:
                        logger.warning("Auto backup failed")
                finally:
                    await distributed_lock.release("backup")
        except Exception as e:
            logger.error(f"Auto backup error: {e}")
        await asyncio.sleep(_BACKUP_INTERVAL)
