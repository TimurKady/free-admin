# -*- coding: utf-8 -*-
"""
upload

File upload endpoint for the admin interface.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Request
from config.settings import settings

from ..core.services.auth import AdminUserDTO
from ..core.auth import admin_auth_service
from ..core.services.permissions import PermAction, permissions_service
from ..core.settings import SettingsKey, system_config
from ..crud import SafePathSegment


class UploadAPI:
    """API endpoints for uploading files."""

    def __init__(self) -> None:
        self.router = APIRouter()
        self.router.post("/{app}/{model}/upload")(self.upload)

    async def _ensure_permission(self, request: Request, app: str, model: str) -> None:
        perm_add = permissions_service.require_model_permission(
            PermAction.add, app_value=app, model_value=model
        )
        perm_change = permissions_service.require_model_permission(
            PermAction.change, app_value=app, model_value=model
        )
        try:
            await perm_add(request)
        except HTTPException:
            await perm_change(request)

    async def upload(
        self,
        request: Request,
        app: str,
        model: str,
        file: UploadFile = File(...),
        user: AdminUserDTO = Depends(admin_auth_service.get_current_admin_user),
    ):
        if not file or not getattr(file, "filename", None):
            raise HTTPException(status_code=400, detail="No file provided")
        await self._ensure_permission(request, app, model)
        media_root = Path(
            system_config.get_cached(SettingsKey.MEDIA_ROOT, settings.MEDIA_ROOT)
        )
        safe_app = SafePathSegment(app)
        safe_model = SafePathSegment(model)
        rel_dir = Path(safe_app) / safe_model
        target = media_root / rel_dir
        target.mkdir(parents=True, exist_ok=True)
        filename = Path(file.filename or "upload").name
        dest = target / filename
        stem = dest.stem
        suffix = dest.suffix
        idx = 1
        while dest.exists():
            dest = target / f"{stem}-{idx}{suffix}"
            idx += 1
        data = await file.read()
        with open(dest, "wb") as fh:
            fh.write(data)
        await file.close()
        rel_path = rel_dir / dest.name
        return {"url": str(rel_path).replace("\\", "/")}


_api = UploadAPI()
router = _api.router

__all__ = ["router"]

# The End

