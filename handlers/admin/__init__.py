from aiogram import Router
from handlers.admin.ban import router as ban_router
from handlers.admin.mute import router as mute_router
from handlers.admin.warn import router as warn_router

router = Router()
router.include_routers(ban_router, mute_router, warn_router)
