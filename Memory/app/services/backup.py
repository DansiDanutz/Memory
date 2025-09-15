"""
Automated backup service for Memory App
Implements scheduled backups with rotation and recovery
"""

import os
import json
import shutil
import tarfile
import hashlib
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import aiofiles
import logging
from dataclasses import dataclass, asdict
import boto3
from botocore.exceptions import ClientError
import schedule
import time

logger = logging.getLogger(__name__)


@dataclass
class BackupMetadata:
    """Backup metadata"""
    backup_id: str
    timestamp: datetime
    size_bytes: int
    file_count: int
    checksum: str
    version: str
    environment: str
    retention_days: int


class BackupService:
    """Comprehensive backup and recovery service"""

    def __init__(
        self,
        data_dir: str = "./app/memory-system",
        backup_dir: str = "./backups",
        retention_days: int = 30,
        use_s3: bool = False,
        s3_bucket: Optional[str] = None
    ):
        self.data_dir = Path(data_dir)
        self.backup_dir = Path(backup_dir)
        self.retention_days = retention_days
        self.use_s3 = use_s3
        self.s3_bucket = s3_bucket

        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # S3 client if configured
        self.s3_client = None
        if use_s3 and s3_bucket:
            self._init_s3()

        # Backup history
        self.history_file = self.backup_dir / "backup_history.json"
        self.backup_history = self._load_history()

    def _init_s3(self):
        """Initialize S3 client"""
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_REGION', 'us-east-1')
            )
            # Test connection
            self.s3_client.head_bucket(Bucket=self.s3_bucket)
            logger.info(f"Connected to S3 bucket: {self.s3_bucket}")
        except ClientError as e:
            logger.error(f"Failed to connect to S3: {e}")
            self.use_s3 = False

    def _load_history(self) -> List[BackupMetadata]:
        """Load backup history"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    return [
                        BackupMetadata(
                            **{**item, 'timestamp': datetime.fromisoformat(item['timestamp'])}
                        )
                        for item in data
                    ]
            except Exception as e:
                logger.error(f"Failed to load backup history: {e}")
        return []

    def _save_history(self):
        """Save backup history"""
        try:
            data = [
                {**asdict(backup), 'timestamp': backup.timestamp.isoformat()}
                for backup in self.backup_history
            ]
            with open(self.history_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save backup history: {e}")

    async def create_backup(self, description: str = "") -> BackupMetadata:
        """Create a new backup"""
        logger.info("Starting backup creation...")
        start_time = datetime.now()

        # Generate backup ID
        backup_id = f"backup_{start_time.strftime('%Y%m%d_%H%M%S')}"
        backup_file = self.backup_dir / f"{backup_id}.tar.gz"

        try:
            # Count files
            file_count = sum(1 for _ in self.data_dir.rglob("*") if _.is_file())

            # Create tar archive
            with tarfile.open(backup_file, "w:gz") as tar:
                tar.add(self.data_dir, arcname="memory-system")

                # Add metadata
                metadata = {
                    "backup_id": backup_id,
                    "timestamp": start_time.isoformat(),
                    "description": description,
                    "file_count": file_count,
                    "source_dir": str(self.data_dir),
                    "version": os.getenv("APP_VERSION", "1.0.0"),
                    "environment": os.getenv("ENVIRONMENT", "production")
                }
                metadata_file = self.backup_dir / f"{backup_id}_metadata.json"
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
                tar.add(metadata_file, arcname="metadata.json")
                os.unlink(metadata_file)

            # Calculate checksum
            checksum = await self._calculate_checksum(backup_file)

            # Get file size
            size_bytes = backup_file.stat().st_size

            # Create backup metadata
            backup_metadata = BackupMetadata(
                backup_id=backup_id,
                timestamp=start_time,
                size_bytes=size_bytes,
                file_count=file_count,
                checksum=checksum,
                version=os.getenv("APP_VERSION", "1.0.0"),
                environment=os.getenv("ENVIRONMENT", "production"),
                retention_days=self.retention_days
            )

            # Add to history
            self.backup_history.append(backup_metadata)
            self._save_history()

            # Upload to S3 if configured
            if self.use_s3:
                await self._upload_to_s3(backup_file, backup_id)

            # Clean old backups
            await self._cleanup_old_backups()

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Backup completed in {elapsed:.2f} seconds: {backup_id}")

            return backup_metadata

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            # Clean up partial backup
            if backup_file.exists():
                os.unlink(backup_file)
            raise

    async def restore_backup(self, backup_id: str, target_dir: Optional[str] = None) -> bool:
        """Restore from backup"""
        logger.info(f"Starting restore from backup: {backup_id}")

        # Find backup
        backup = next((b for b in self.backup_history if b.backup_id == backup_id), None)
        if not backup:
            raise ValueError(f"Backup not found: {backup_id}")

        backup_file = self.backup_dir / f"{backup_id}.tar.gz"

        # Download from S3 if needed
        if not backup_file.exists() and self.use_s3:
            await self._download_from_s3(backup_id)

        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")

        # Verify checksum
        checksum = await self._calculate_checksum(backup_file)
        if checksum != backup.checksum:
            raise ValueError(f"Backup checksum mismatch! Expected: {backup.checksum}, Got: {checksum}")

        # Determine target directory
        if not target_dir:
            target_dir = str(self.data_dir)

        try:
            # Create restore point
            if Path(target_dir).exists():
                restore_point = f"{target_dir}_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.move(target_dir, restore_point)
                logger.info(f"Created restore point: {restore_point}")

            # Extract backup
            with tarfile.open(backup_file, "r:gz") as tar:
                tar.extractall(Path(target_dir).parent)

            logger.info(f"Restore completed successfully: {backup_id}")
            return True

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            raise

    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate file checksum"""
        sha256_hash = hashlib.sha256()
        async with aiofiles.open(file_path, "rb") as f:
            while chunk := await f.read(8192):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    async def _upload_to_s3(self, file_path: Path, backup_id: str):
        """Upload backup to S3"""
        if not self.s3_client:
            return

        try:
            key = f"backups/{backup_id}/{file_path.name}"
            self.s3_client.upload_file(
                str(file_path),
                self.s3_bucket,
                key,
                ExtraArgs={
                    'ServerSideEncryption': 'AES256',
                    'StorageClass': 'STANDARD_IA'
                }
            )
            logger.info(f"Uploaded backup to S3: {key}")

        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")

    async def _download_from_s3(self, backup_id: str):
        """Download backup from S3"""
        if not self.s3_client:
            raise ValueError("S3 not configured")

        try:
            backup_file = self.backup_dir / f"{backup_id}.tar.gz"
            key = f"backups/{backup_id}/{backup_id}.tar.gz"

            self.s3_client.download_file(
                self.s3_bucket,
                key,
                str(backup_file)
            )
            logger.info(f"Downloaded backup from S3: {key}")

        except ClientError as e:
            logger.error(f"S3 download failed: {e}")
            raise

    async def _cleanup_old_backups(self):
        """Remove old backups beyond retention period"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        removed_count = 0

        for backup in list(self.backup_history):
            if backup.timestamp < cutoff_date:
                # Remove local file
                backup_file = self.backup_dir / f"{backup.backup_id}.tar.gz"
                if backup_file.exists():
                    os.unlink(backup_file)
                    removed_count += 1

                # Remove from S3
                if self.use_s3:
                    try:
                        key = f"backups/{backup.backup_id}/{backup.backup_id}.tar.gz"
                        self.s3_client.delete_object(Bucket=self.s3_bucket, Key=key)
                    except:
                        pass

                # Remove from history
                self.backup_history.remove(backup)

        if removed_count > 0:
            self._save_history()
            logger.info(f"Cleaned up {removed_count} old backups")

    async def get_backup_list(self) -> List[Dict[str, Any]]:
        """Get list of available backups"""
        return [
            {
                "backup_id": backup.backup_id,
                "timestamp": backup.timestamp.isoformat(),
                "size_mb": round(backup.size_bytes / (1024 * 1024), 2),
                "file_count": backup.file_count,
                "version": backup.version,
                "environment": backup.environment,
                "expires_at": (backup.timestamp + timedelta(days=backup.retention_days)).isoformat()
            }
            for backup in sorted(self.backup_history, key=lambda x: x.timestamp, reverse=True)
        ]

    async def verify_backup(self, backup_id: str) -> Dict[str, Any]:
        """Verify backup integrity"""
        backup = next((b for b in self.backup_history if b.backup_id == backup_id), None)
        if not backup:
            raise ValueError(f"Backup not found: {backup_id}")

        backup_file = self.backup_dir / f"{backup_id}.tar.gz"

        # Check local file
        local_exists = backup_file.exists()
        local_valid = False
        if local_exists:
            checksum = await self._calculate_checksum(backup_file)
            local_valid = checksum == backup.checksum

        # Check S3
        s3_exists = False
        if self.use_s3:
            try:
                key = f"backups/{backup_id}/{backup_id}.tar.gz"
                self.s3_client.head_object(Bucket=self.s3_bucket, Key=key)
                s3_exists = True
            except:
                pass

        return {
            "backup_id": backup_id,
            "local_exists": local_exists,
            "local_valid": local_valid,
            "s3_exists": s3_exists,
            "checksum": backup.checksum,
            "status": "valid" if local_valid or s3_exists else "corrupted"
        }


class BackupScheduler:
    """Automated backup scheduler"""

    def __init__(self, backup_service: BackupService):
        self.backup_service = backup_service
        self.running = False

    def start(self):
        """Start backup scheduler"""
        if self.running:
            return

        self.running = True

        # Schedule daily backup at 2 AM
        schedule.every().day.at("02:00").do(self._run_backup)

        # Schedule weekly full backup on Sunday
        schedule.every().sunday.at("03:00").do(self._run_full_backup)

        # Start scheduler in background
        asyncio.create_task(self._scheduler_loop())

        logger.info("Backup scheduler started")

    async def _scheduler_loop(self):
        """Scheduler loop"""
        while self.running:
            schedule.run_pending()
            await asyncio.sleep(60)  # Check every minute

    def _run_backup(self):
        """Run scheduled backup"""
        asyncio.create_task(
            self.backup_service.create_backup("Scheduled daily backup")
        )

    def _run_full_backup(self):
        """Run full backup"""
        asyncio.create_task(
            self.backup_service.create_backup("Scheduled weekly full backup")
        )

    def stop(self):
        """Stop scheduler"""
        self.running = False
        logger.info("Backup scheduler stopped")


# Singleton instances
_backup_service: Optional[BackupService] = None
_backup_scheduler: Optional[BackupScheduler] = None


def get_backup_service() -> BackupService:
    """Get backup service instance"""
    global _backup_service
    if _backup_service is None:
        _backup_service = BackupService(
            use_s3=os.getenv("BACKUP_S3_ENABLED", "false").lower() == "true",
            s3_bucket=os.getenv("BACKUP_S3_BUCKET")
        )
    return _backup_service


def start_backup_scheduler():
    """Start automated backup scheduler"""
    global _backup_scheduler
    if _backup_scheduler is None:
        _backup_scheduler = BackupScheduler(get_backup_service())
        _backup_scheduler.start()