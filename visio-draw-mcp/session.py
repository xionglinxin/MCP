"""Visio COM 会话管理 — 实例复用、健康检查、超时控制"""
from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Any, Iterator

import pythoncom
import win32com.client as win32

from config import COM_TIMEOUT, STENCIL_DIR

logger = logging.getLogger(__name__)

# ── Visio 常量 ──────────────────────────────────────────────

VIS_OPEN_RO = 2
VIS_OPEN_HIDDEN = 64
VIS_OPEN_RW = 1
VIS_FIXED_FORMAT_PDF = 1


# ══════════════════════════════════════════════════════════
#  Visio 会话管理器
# ══════════════════════════════════════════════════════════


class VisioSessionManager:
    """在 MCP 服务器生命周期内复用 Visio COM 实例，避免反复启停。"""

    def __init__(self):
        self._visio = None
        self._lock = threading.Lock()
        self._stencil_cache: dict[str, list[str]] = {}  # stencil_name -> masters

    def _ensure_com(self):
        """确保 COM 已初始化（每个线程需要独立初始化）"""
        try:
            pythoncom.CoInitialize()
        except Exception:
            pass  # 已初始化

    def _create_visio(self):
        """创建新的 Visio 实例"""
        self._ensure_com()
        try:
            visio = win32.gencache.EnsureDispatch("Visio.Application")
        except Exception:
            visio = win32.Dispatch("Visio.Application")
        visio.Visible = False  # 无头模式，不弹出 Visio 窗口
        return visio

    def get(self) -> Any:
        """获取 Visio Application 对象（线程安全，自动恢复）"""
        with self._lock:
            if self._visio is None:
                self._visio = self._create_visio()
            else:
                # 健康检查：尝试访问属性
                try:
                    _ = self._visio.Version
                except Exception:
                    # Visio 崩溃或断开，重建
                    logger.debug("Visio health check failed, recreating instance")
                    try:
                        self._visio.Quit()
                    except Exception:
                        pass
                    self._visio = self._create_visio()
            return self._visio

    def reset(self):
        """强制重建 Visio 实例"""
        with self._lock:
            if self._visio is not None:
                try:
                    self._visio.Quit()
                except Exception as e:
                    logger.debug("Error quitting Visio during reset: %s", e)
                self._visio = None

    def shutdown(self):
        """关闭 Visio 并清理"""
        with self._lock:
            if self._visio is not None:
                try:
                    self._visio.Quit()
                except Exception as e:
                    logger.debug("Error quitting Visio during shutdown: %s", e)
                self._visio = None
            self._stencil_cache.clear()

    def get_stencil_masters_cached(self, stencil_name: str) -> list[str]:
        """从缓存获取 stencil masters，缓存未命中时启动 Visio 读取"""
        if stencil_name in self._stencil_cache:
            return self._stencil_cache[stencil_name]

        from drawing import _resolve_stencil_path

        stencil_path = _resolve_stencil_path(stencil_name)
        visio = self.get()
        stencil_doc = visio.Documents.OpenEx(
            str(stencil_path), VIS_OPEN_RO | VIS_OPEN_HIDDEN
        )
        try:
            masters = sorted(master.NameU for master in stencil_doc.Masters)
        finally:
            stencil_doc.Close()

        self._stencil_cache[stencil_name] = masters
        return masters

    def invalidate_stencil_cache(self, stencil_name: str | None = None):
        """清除 stencil 缓存"""
        if stencil_name:
            self._stencil_cache.pop(stencil_name, None)
        else:
            self._stencil_cache.clear()


# 全局会话管理器（由 server.py lifespan 管理）
_session_mgr: VisioSessionManager | None = None


def init_session_manager() -> VisioSessionManager:
    """初始化全局会话管理器"""
    global _session_mgr
    _session_mgr = VisioSessionManager()
    return _session_mgr


def get_session_manager() -> VisioSessionManager:
    """获取全局会话管理器"""
    if _session_mgr is None:
        raise RuntimeError("Session manager not initialized. Call init_session_manager() first.")
    return _session_mgr


@contextmanager
def _visio_session() -> Iterator:
    """向后兼容的独立会话上下文（用于预置案例脚本）"""
    pythoncom.CoInitialize()
    visio = None
    try:
        try:
            visio = win32.gencache.EnsureDispatch("Visio.Application")
        except Exception:
            visio = win32.Dispatch("Visio.Application")
        visio.Visible = False  # 无头模式
        yield visio
    finally:
        if visio is not None:
            try:
                visio.Quit()
            except Exception as e:
                logger.debug("Error quitting Visio in _visio_session cleanup: %s", e)
        pythoncom.CoUninitialize()


def _with_timeout(func, timeout: int = COM_TIMEOUT):
    """在指定秒数内执行函数，超时则抛出 TimeoutError"""
    result = [None]
    exc = [None]

    def _target():
        # COM 操作需要在工作线程中初始化
        pythoncom.CoInitialize()
        try:
            result[0] = func()
        except Exception as e:
            exc[0] = e
        finally:
            pythoncom.CoUninitialize()

    t = threading.Thread(target=_target)
    t.daemon = True
    t.start()
    t.join(timeout)

    if t.is_alive():
        raise TimeoutError(f"Visio COM 操作超时（>{timeout}秒）。Visio 可能已挂起，建议重试。")
    if exc[0]:
        raise exc[0]
    return result[0]
