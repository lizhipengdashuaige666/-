from __future__ import annotations

import ctypes
import os
import re
import time
from pathlib import Path
from typing import Iterable

import keyboard
import psutil
import win32con
import win32gui
import win32process

from core.config import TESSDATA_DIR
from core.logger import logger
from core.utils import clipboard_has_files, copy_files_to_clipboard, copy_text_to_clipboard, clipboard_has_text
from uia_runtime import import_uiautomation

SW_RESTORE = 9
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)


class BaseMessenger:
    platform = ""
    process_names: tuple[str, ...] = ()
    title_keywords: tuple[str, ...] = ()

    def __init__(self) -> None:
        self.hwnd: int | None = None

    def activate(self) -> bool:
        candidates = self._find_platform_windows()
        if not candidates:
            logger.error(f"未找到{self.platform}窗口")
            logger.error(self.format_window_diagnosis())
            return False

        hwnd = max(candidates, key=self._window_score)
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, SW_RESTORE)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        self._set_foreground(hwnd)
        self.hwnd = hwnd
        title = win32gui.GetWindowText(hwnd)
        logger.info(f"{self.platform}窗口已激活: {title}")
        return True

    def open_chat_by_keyword(self, keyword: str) -> bool:
        raise NotImplementedError

    def prepare_search_keyword(self, keyword: str) -> bool:
        if not self.hwnd:
            logger.error("窗口未激活")
            return False
        self._set_foreground(self.hwnd)
        keyboard.press_and_release("ctrl+f")
        time.sleep(0.5)

        search_box = self._find_edit_by_names(("搜索", "Search"))
        if search_box:
            if not self._set_text(search_box, keyword):
                return False
        else:
            logger.warning("未找到搜索框，改用快捷键粘贴搜索关键词")
            if not self._paste_text(keyword):
                return False

        time.sleep(0.6)
        logger.info(f"[STEP_OK] 已输入搜索关键词: {keyword}")
        return True

    def open_prepared_search_result(self, keyword: str) -> bool:
        if self._open_search_result_by_ocr(keyword):
            if self._chat_title_contains(keyword):
                logger.info(f"[STEP_OK] 已进入目标群聊: {keyword}")
                return True
            logger.warning(f"OCR 点击后未确认进入目标群聊，尝试键盘: {keyword}")
            keyboard.press_and_release("esc")
            time.sleep(0.3)
            self.prepare_search_keyword(keyword)

        if self._open_search_result_by_keyboard(keyword):
            if self._chat_title_contains(keyword):
                logger.info(f"[STEP_OK] 已进入目标群聊: {keyword}")
                return True
            logger.warning(f"键盘操作后未确认进入目标群聊，尝试控件点击: {keyword}")
            keyboard.press_and_release("esc")
            time.sleep(0.3)

        self.prepare_search_keyword(keyword)
        item = self._find_matching_item(keyword)
        if not item:
            logger.error(f"未找到匹配聊天: {keyword}")
            return False
        if not self._click_control(item):
            return False
        time.sleep(0.8)
        if self._chat_title_contains(keyword):
            logger.info(f"[STEP_OK] 已进入目标群聊: {keyword}")
            return True
        logger.error(f"点击搜索结果后未确认进入目标群聊: {keyword}")
        return False

    def open_chat_for_manual_confirmation(self, keyword: str) -> bool:
        if not self.prepare_search_keyword(keyword):
            return False
        logger.info(f"搜索关键词已输入，等待用户手动选择聊天: {keyword}")
        return True

    def dump_visible_controls(self, limit: int = 80) -> list[str]:
        root = self._root_control()
        if not root:
            return []
        rows: list[str] = []

        def walk(control, depth: int) -> None:
            if len(rows) >= limit or depth > 4:
                return
            try:
                name = getattr(control, "Name", "") or ""
                class_name = getattr(control, "ClassName", "") or ""
                control_type = getattr(control, "ControlTypeName", "") or ""
                if name or class_name:
                    rows.append(f"depth={depth} type={control_type} class={class_name} name={name}")
                for child in self._children(control):
                    walk(child, depth + 1)
            except Exception:
                return

        walk(root, 0)
        return rows

    def send_file(self, file_path: str | Path) -> bool:
        path = Path(file_path).resolve()
        if not path.is_file():
            logger.error(f"文件不存在: {path}")
            return False
        if not self.hwnd:
            logger.error("窗口未激活")
            return False

        self._focus_message_input()
        copy_files_to_clipboard([path])
        if not clipboard_has_files():
            logger.error("文件剪贴板写入后校验失败")
            return False
        time.sleep(0.1)
        keyboard.press_and_release("ctrl+v")
        time.sleep(0.4)
        keyboard.press_and_release("enter")
        logger.info(f"已发送文件: {path.name}")
        return True

    def send_text(self, text: str) -> bool:
        text = text.strip()
        if not text:
            return True
        if not self.hwnd:
            logger.error("窗口未激活")
            return False

        try:
            self._focus_message_input()
            copy_text_to_clipboard(text)
            time.sleep(0.05)
            if not clipboard_has_text():
                logger.error("文字剪贴板写入后校验失败")
                return False
            keyboard.press_and_release("ctrl+v")
            time.sleep(0.3)
            keyboard.press_and_release("enter")
            logger.info("文字通知已发送")
            time.sleep(0.3)
            return True
        except Exception as exc:
            logger.error(f"文字通知发送失败: {exc}")
            return False

    def _find_platform_windows(self) -> list[int]:
        process_names = {name.lower() for name in self.process_names}
        title_keywords = tuple(self.title_keywords)
        exact_candidates: list[int] = []
        process_candidates: list[int] = []

        @EnumWindowsProc
        def enum_callback(hwnd: int, _: int) -> bool:
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                title = win32gui.GetWindowText(hwnd)
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    process_name = psutil.Process(pid).name().lower()
                except psutil.Error:
                    return True
                if process_name in process_names:
                    process_candidates.append(hwnd)
                    if title and any(keyword in title for keyword in title_keywords):
                        exact_candidates.append(hwnd)
            except Exception:
                return True
            return True

        ctypes.windll.user32.EnumWindows(enum_callback, 0)
        return exact_candidates or self._large_windows(process_candidates)

    def diagnose_window_access(self) -> dict[str, object]:
        process_names = {name.lower() for name in self.process_names}
        processes = self._matching_processes(process_names)
        windows, visible_count = self._visible_windows()
        matching_windows = [
            window for window in windows if window["process_name"].lower() in process_names
        ]
        return {
            "platform": self.platform,
            "processes": processes,
            "visible_window_count": visible_count,
            "matching_windows": matching_windows,
            "foreground": self._foreground_window(),
        }

    def format_window_diagnosis(self) -> str:
        diagnosis = self.diagnose_window_access()
        processes = diagnosis["processes"]
        visible_count = diagnosis["visible_window_count"]
        matching_windows = diagnosis["matching_windows"]
        foreground = diagnosis["foreground"]

        lines = [f"{self.platform}窗口诊断:"]
        lines.append(f"- 进程数量: {len(processes)}")
        lines.append(f"- 当前可见窗口数量: {visible_count}")
        lines.append(f"- 匹配到的可见{self.platform}窗口: {len(matching_windows)}")
        if foreground["hwnd"]:
            lines.append(
                f"- 当前前台窗口: {foreground['process_name']} / {foreground['title'] or '无标题'}"
            )
        else:
            lines.append("- 当前前台窗口: 系统未返回窗口句柄")

        if not processes:
            lines.append(f"结论: 未检测到{self.platform}进程，请先登录并打开{self.platform}。")
        elif not matching_windows:
            lines.append(
                f"结论: 检测到{self.platform}进程，但当前运行环境看不到可用主窗口。"
                "请确认主界面已打开；如果在 Codex 里运行测试，这通常表示桌面窗口不可访问。"
            )
        return "\n".join(lines)

    def _matching_processes(self, process_names: set[str]) -> list[dict[str, object]]:
        matches = []
        for proc in psutil.process_iter(("pid", "name")):
            try:
                name = (proc.info.get("name") or "").lower()
                if name in process_names:
                    matches.append({"pid": proc.info["pid"], "name": proc.info["name"]})
            except (psutil.Error, OSError):
                continue
        return matches

    def _visible_windows(self) -> tuple[list[dict[str, object]], int]:
        windows: list[dict[str, object]] = []
        visible_count = 0

        @EnumWindowsProc
        def enum_callback(hwnd: int, _: int) -> bool:
            nonlocal visible_count
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                visible_count += 1
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    process_name = psutil.Process(pid).name()
                except psutil.Error:
                    process_name = ""
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                windows.append(
                    {
                        "hwnd": hwnd,
                        "pid": pid,
                        "process_name": process_name,
                        "title": win32gui.GetWindowText(hwnd),
                        "class_name": win32gui.GetClassName(hwnd),
                        "width": max(0, right - left),
                        "height": max(0, bottom - top),
                    }
                )
            except Exception:
                return True
            return True

        ctypes.windll.user32.EnumWindows(enum_callback, 0)
        return windows, visible_count

    def _foreground_window(self) -> dict[str, object]:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd or not win32gui.IsWindow(hwnd):
            return {"hwnd": 0, "pid": 0, "process_name": "", "title": "", "class_name": ""}
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            process_name = psutil.Process(pid).name()
        except psutil.Error:
            process_name = ""
        return {
            "hwnd": hwnd,
            "pid": pid,
            "process_name": process_name,
            "title": win32gui.GetWindowText(hwnd),
            "class_name": win32gui.GetClassName(hwnd),
        }

    def _large_windows(self, hwnds: list[int]) -> list[int]:
        large_windows = []
        for hwnd in hwnds:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = max(0, right - left)
            height = max(0, bottom - top)
            if width >= 500 and height >= 400:
                large_windows.append(hwnd)
        return large_windows

    def _window_score(self, hwnd: int) -> tuple[int, int, int]:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        area = max(0, right - left) * max(0, bottom - top)
        title = win32gui.GetWindowText(hwnd)
        return area, len(title), hwnd

    def _set_foreground(self, hwnd: int) -> None:
        if not win32gui.IsWindow(hwnd):
            return
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, SW_RESTORE)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        try:
            win32gui.BringWindowToTop(hwnd)
        except Exception:
            pass
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            self._force_foreground(hwnd)
        time.sleep(0.2)

    def _force_foreground(self, hwnd: int) -> None:
        user32 = ctypes.windll.user32
        foreground = user32.GetForegroundWindow()
        current_thread = user32.GetCurrentThreadId()
        target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)
        foreground_thread = user32.GetWindowThreadProcessId(foreground, None)
        user32.AttachThreadInput(current_thread, target_thread, True)
        user32.AttachThreadInput(current_thread, foreground_thread, True)
        try:
            win32gui.SetForegroundWindow(hwnd)
        finally:
            user32.AttachThreadInput(current_thread, target_thread, False)
            user32.AttachThreadInput(current_thread, foreground_thread, False)

    def _root_control(self):
        if not self.hwnd:
            return None
        try:
            auto = import_uiautomation()
            return auto.ControlFromHandle(self.hwnd)
        except Exception as exc:
            logger.warning(f"读取窗口控件失败: {exc}")
            return None

    def _first_existing(self, controls: Iterable[object]):
        for control in controls:
            if control and getattr(control, "Exists", lambda *_: True)(0, 0):
                return control
        return None

    def _find_edit_by_names(self, names: tuple[str, ...]):
        root = self._root_control()
        if not root:
            return None

        candidates = []
        for depth in (3, 5, 8):
            for name in names:
                candidates.append(root.EditControl(searchDepth=depth, Name=name))
        for depth in (3, 5, 8):
            candidates.append(root.EditControl(searchDepth=depth))

        control = self._first_existing(candidates)
        if control:
            return control

        return None

    def _set_text(self, edit_control, text: str) -> bool:
        if not edit_control:
            return False
        try:
            edit_control.SetFocus()
        except Exception:
            pass
        try:
            edit_control.SetValue("")
            edit_control.SetValue(text)
        except Exception as exc:
            logger.error(f"输入搜索关键词失败: {exc}")
        if self._control_text_contains(edit_control, text):
            logger.info("搜索关键词已通过控件输入")
            return True
        return self._paste_text(text)

    def _control_text_contains(self, edit_control, text: str) -> bool:
        for getter in (
            lambda: edit_control.GetValuePattern().Value,
            lambda: edit_control.Name,
        ):
            try:
                value = getter()
                if value and text in value:
                    return True
            except Exception:
                continue
        return False

    def _paste_text(self, text: str) -> bool:
        try:
            logger.info(f"准备粘贴搜索关键词: {text}")
            copy_text_to_clipboard(text)
            time.sleep(0.05)
            keyboard.press_and_release("ctrl+a")
            time.sleep(0.03)
            keyboard.press_and_release("ctrl+v")
            time.sleep(0.2)
            logger.info("搜索关键词已通过剪贴板粘贴")
            return True
        except Exception as exc:
            logger.error(f"粘贴搜索关键词失败: {exc}")
            return False

    def _close_popups(self) -> None:
        try:
            import win32api

            keyboard.press_and_release("esc")
            time.sleep(0.1)
            left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
            x = left + 40
            y = top + 40
            win32api.SetCursorPos((x, y))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.03)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.15)
        except Exception:
            return

    _SEARCH_BLACKLIST = {"搜一搜", "搜一搜网络结果", "搜一搜更多", "Search"}
    _GROUP_MARKERS = {"群聊", "群", "Group"}

    def _find_matching_item(self, keyword: str):
        root = self._root_control()
        if not root:
            return None

        auto = import_uiautomation()
        escaped_keyword = re.escape(keyword)
        candidates: list[object] = []
        for depth in (4, 6, 8, 10):
            try:
                item = root.ListItemControl(searchDepth=depth, RegexName=f".*{escaped_keyword}.*")
                if item and item.Exists(0, 0) and not self._is_search_blacklisted(item):
                    candidates.append(item)
            except Exception:
                continue

        if not candidates:
            for depth in (4, 6, 8):
                for list_control in self._list_controls(root, depth):
                    for item in self._children(list_control):
                        name = getattr(item, "Name", "")
                        if name and keyword in name and not self._is_search_blacklisted(item):
                            candidates.append(item)

        if not candidates:
            return None

        scored = [(self._item_group_score(c), c) for c in candidates]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        best_score, best = scored[0]
        logger.info(f"UIA选中: name={getattr(best, 'Name', '')}, group_score={best_score}, candidates={len(candidates)}")
        return best

    def _item_group_score(self, control) -> int:
        parent = control
        for _ in range(6):
            try:
                parent_name = str(getattr(parent, "Name", "") or "")
                for marker in self._GROUP_MARKERS:
                    if marker in parent_name:
                        return 100
                for black in ("联系人", "Contact"):
                    if black in parent_name:
                        return -1
            except Exception:
                break
            try:
                parent = parent.GetParentControl()
            except Exception:
                break
        return 50

    def _is_search_blacklisted(self, control) -> bool:
        name = str(getattr(control, "Name", "") or "")
        return any(black in name for black in self._SEARCH_BLACKLIST)

    def _list_controls(self, root, depth: int):
        auto = import_uiautomation()
        controls = []
        for getter in (
            lambda: root.ListControl(searchDepth=depth),
            lambda: root.Control(searchDepth=depth, ControlType=auto.ControlType.ListControl),
            lambda: root.Control(searchDepth=depth, ControlType=auto.ControlType.PaneControl),
        ):
            try:
                control = getter()
                if control and control.Exists(0, 0):
                    controls.append(control)
            except Exception:
                pass
        return controls

    def _children(self, control) -> list[object]:
        try:
            return control.GetChildren()
        except Exception:
            return []

    def _click_control(self, control) -> bool:
        try:
            control.SetFocus()
        except Exception:
            pass
        try:
            control.Click()
            return True
        except Exception as exc:
            logger.error(f"点击搜索结果失败: {exc}")
            return False

    def _search_and_open(self, keyword: str, edit_names: tuple[str, ...]) -> bool:
        if not self.hwnd:
            logger.error("窗口未激活")
            return False

        if not self.prepare_search_keyword(keyword):
            return False

        if self.open_prepared_search_result(keyword):
            logger.info(f"已通过键盘打开搜索结果，继续发送: {keyword}")
            return True

        item = self._find_matching_item(keyword)
        if not item:
            logger.error(f"未找到匹配聊天: {keyword}")
            return False

        name = getattr(item, "Name", "")
        if not self._click_control(item):
            return False
        logger.info(f"已打开聊天: {name or keyword}")
        time.sleep(0.5)
        return True

    def _open_search_result_by_keyboard(self, keyword: str) -> bool:
        sequences = (
            ("enter",),
            ("down", "enter"),
            ("tab", "enter"),
            ("tab", "down", "enter"),
        )
        for sequence in sequences:
            try:
                self._set_foreground(self.hwnd)
                for key in sequence:
                    keyboard.press_and_release(key)
                    time.sleep(0.3)
                logger.info(f"键盘序列: {'+'.join(sequence)}")
                time.sleep(1.0)
                if self._chat_title_contains(keyword):
                    logger.info(f"键盘序列成功: {'+'.join(sequence)}")
                    return True
                keyboard.press_and_release("esc")
                time.sleep(0.4)
            except Exception as exc:
                logger.warning(f"键盘序列失败 ({'+'.join(sequence)}): {exc}")
        return False

    def _open_search_result_by_ocr(self, keyword: str) -> bool:
        if not self.hwnd:
            return False
        try:
            from PIL import ImageGrab
            import pytesseract
            import win32api

            left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
            if right <= left or bottom <= top:
                return False
            os.environ["TESSDATA_PREFIX"] = str(TESSDATA_DIR)
            compact_keyword = _compact_text(keyword)
            best = None
            seen_lines: list[str] = []
            for image, label in self._ocr_images(left, top, right, bottom):
                for psm in (6, 11):
                    data = pytesseract.image_to_data(
                        image,
                        lang="chi_sim",
                        config=f"--psm {psm}",
                        output_type=pytesseract.Output.DICT,
                    )
                    lines = self._ocr_lines(data)
                    seen_lines.extend(f"{label}/psm{psm}: {line}" for line in lines[:12])
                    best = self._find_ocr_line_match(data, compact_keyword)
                    if best:
                        break
                if best:
                    break
            if not best:
                logger.error(f"OCR 未识别到搜索结果文字: {keyword}")
                for line in seen_lines[:30]:
                    logger.info(f"OCR识别内容: {line}")
                return False

            x = left + int(best["x"])
            y = top + best["y"]
            win32api.SetCursorPos((x, y))
            time.sleep(0.1)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            logger.info(f"OCR 已点击搜索结果: {keyword}, x={x}, y={y}, text={best['text']}")
            time.sleep(1.0)
            return True
        except Exception as exc:
            logger.error(f"OCR 点击搜索结果失败: {exc}")
            return False

    def _ocr_images(self, left: int, top: int, right: int, bottom: int):
        from PIL import ImageGrab, ImageOps

        image = ImageGrab.grab(bbox=(left, top, right, bottom))
        width, height = image.size
        crops = (
            ("full", image),
            ("left", image.crop((0, 0, min(width, 520), height))),
            ("upper_left", image.crop((0, 0, min(width, 520), min(height, 420)))),
        )
        for label, crop in crops:
            gray = ImageOps.grayscale(crop)
            enhanced = ImageOps.autocontrast(gray)
            scaled = enhanced.resize((enhanced.width * 3, enhanced.height * 3))
            yield scaled, label

    def _ocr_lines(self, data: dict) -> list[str]:
        lines: dict[tuple[object, object, object], list[int]] = {}
        for index, text in enumerate(data.get("text", [])):
            if not _compact_text(text):
                continue
            key = (
                data.get("block_num", [0])[index],
                data.get("par_num", [0])[index],
                data.get("line_num", [0])[index],
            )
            lines.setdefault(key, []).append(index)
        return ["".join(str(data["text"][index]) for index in indexes) for indexes in lines.values()]

    def _find_ocr_line_match(self, data: dict, compact_keyword: str) -> dict[str, object] | None:
        lines: dict[tuple[object, object, object], list[int]] = {}
        for index, text in enumerate(data.get("text", [])):
            if not _compact_text(text):
                continue
            key = (
                data.get("block_num", [0])[index],
                data.get("par_num", [0])[index],
                data.get("line_num", [0])[index],
            )
            lines.setdefault(key, []).append(index)

        SECTION_LABELS = {"搜一搜", "群聊", "联系人", "聊天记录"}
        section_markers: list[tuple[int, str]] = []
        for indexes in lines.values():
            text = "".join(str(data["text"][index]) for index in indexes)
            top = int(min(int(data["top"][index]) for index in indexes) / 3)
            for label in SECTION_LABELS:
                if label in text:
                    section_markers.append((top, label))
                    break

        matches: list[dict[str, object]] = []
        for indexes in lines.values():
            text = "".join(str(data["text"][index]) for index in indexes)
            compact = _compact_text(text)
            if compact_keyword not in compact and compact not in compact_keyword:
                continue
            if any(black in text for black in self._SEARCH_BLACKLIST):
                continue
            left = min(int(data["left"][index]) for index in indexes)
            top = min(int(data["top"][index]) for index in indexes)
            right = max(int(data["left"][index]) + int(data["width"][index]) for index in indexes)
            bottom = max(int(data["top"][index]) + int(data["height"][index]) for index in indexes)
            real_top = int(top / 3)
            real_bottom = int(bottom / 3)
            real_left = int(left / 3)
            real_right = int(right / 3)
            if real_top < 50 or real_top > 420:
                continue
            section = "unknown"
            for marker_top, label in sorted(section_markers, reverse=True):
                if real_top > marker_top + 5:
                    section = label
                    break
            matches.append(
                {
                    "text": text,
                    "x": int((real_left + real_right) / 2),
                    "y": int((real_top + real_bottom) / 2),
                    "top": real_top,
                    "left": real_left,
                    "section": section,
                }
            )
        if not matches:
            return None

        good = [m for m in matches if m["section"] != "搜一搜"]
        chat = [m for m in good if m["section"] == "群聊"]
        unknown = [m for m in good if m["section"] == "unknown"]
        target = chat or unknown or good or matches
        target.sort(key=lambda item: (int(item["top"]), int(item["left"])))
        picked = target[0]
        logger.info(
            f"OCR选中: text={picked['text']}, y={picked['top']}, section={picked['section']}"
        )
        return picked

    def _chat_title_contains(self, keyword: str) -> bool:
        try:
            root = self._root_control()
            if not root:
                return False
            escaped_keyword = re.escape(keyword)
            for depth in (4, 6, 8, 10):
                for getter in (
                    lambda depth=depth: root.TextControl(searchDepth=depth, RegexName=f".*{escaped_keyword}.*"),
                    lambda depth=depth: root.Control(searchDepth=depth, RegexName=f".*{escaped_keyword}.*"),
                ):
                    try:
                        control = getter()
                        if control and control.Exists(0, 0):
                            return True
                    except Exception:
                        continue
        except Exception as exc:
            logger.warning(f"读取聊天标题失败: {exc}")
        return self._chat_title_contains_by_ocr(keyword)

    def _chat_title_contains_by_ocr(self, keyword: str) -> bool:
        if not self.hwnd:
            return False
        try:
            from PIL import ImageGrab, ImageOps
            import pytesseract

            left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
            width = right - left
            height = bottom - top
            if width <= 0 or height <= 0:
                return False
            os.environ["TESSDATA_PREFIX"] = str(TESSDATA_DIR)
            image = ImageGrab.grab(bbox=(left, top, right, bottom))
            crop = image.crop((int(width * 0.45), 0, width, min(140, height)))
            gray = ImageOps.autocontrast(ImageOps.grayscale(crop))
            scaled = gray.resize((gray.width * 3, gray.height * 3))
            for psm in (6, 11):
                text = pytesseract.image_to_string(scaled, lang="chi_sim", config=f"--psm {psm}")
                compact = _compact_text(text)
                if _compact_text(keyword) in compact:
                    if "搜一搜" in compact:
                        logger.warning(f"截图标题区域检测到搜一搜，判定未进入群聊: {keyword}")
                        return False
                    logger.info(f"截图已确认当前群聊标题: {keyword}")
                    return True
            logger.warning(f"截图未确认当前群聊标题: {keyword}")
        except Exception as exc:
            logger.warning(f"截图读取聊天标题失败: {exc}")
        return False

    def _focus_message_input(self) -> None:
        root = self._root_control()
        if root:
            for depth in (4, 6, 8, 10):
                for name in ("输入", "消息", "发送消息", "Input", "Message"):
                    try:
                        edit = root.EditControl(searchDepth=depth, RegexName=f".*{re.escape(name)}.*")
                        if edit and edit.Exists(0, 0):
                            edit.SetFocus()
                            logger.info("已聚焦消息输入框")
                            time.sleep(0.2)
                            return
                    except Exception:
                        continue
        if self._click_message_input_area():
            logger.info("已点击消息输入区域")
            return
        logger.warning("未能聚焦消息输入框")

    def _click_message_input_area(self) -> bool:
        if not self.hwnd:
            return False
        try:
            import win32api

            left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
            width = right - left
            height = bottom - top
            if width <= 0 or height <= 0:
                return False
            x = left + int(width * 0.72)
            y = top + int(height * 0.92)
            win32api.SetCursorPos((x, y))
            time.sleep(0.1)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.2)
            return True
        except Exception as exc:
            logger.warning(f"点击消息输入区域失败: {exc}")
            return False

    def _verify_file_visible(self, file_name: str) -> bool:
        time.sleep(3)
        try:
            root = self._root_control()
            if not root:
                return self._verify_file_visible_by_ocr(file_name)
            auto = import_uiautomation()
            stem = Path(file_name).stem
            for depth in (6, 8, 10, 12):
                for getter in (
                    lambda depth=depth: root.TextControl(searchDepth=depth, RegexName=f".*{re.escape(file_name)}.*"),
                    lambda depth=depth: root.TextControl(searchDepth=depth, RegexName=f".*{re.escape(stem)}.*"),
                ):
                    try:
                        item = getter()
                        if item and item.Exists(0, 0):
                            logger.info(f"UIA发送验证通过: {file_name}")
                            return True
                    except Exception:
                        continue
            return self._verify_file_visible_by_ocr(file_name)
        except Exception as exc:
            logger.warning(f"控件发送验证失败，改用截图验证: {exc}")
            return self._verify_file_visible_by_ocr(file_name)

    def _verify_file_visible_by_ocr(self, file_name: str) -> bool:
        if not self.hwnd:
            return False
        try:
            from PIL import ImageGrab, ImageOps, ImageFilter
            import pytesseract

            left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
            width = right - left
            height = bottom - top
            if width <= 0 or height <= 0:
                return False
            os.environ["TESSDATA_PREFIX"] = str(TESSDATA_DIR)
            image = ImageGrab.grab(bbox=(left, top, right, bottom))

            stem = Path(file_name).stem
            targets = {_compact_text(file_name), _compact_text(stem)}
            targets.update(re.findall(r"\d{8,}", file_name))
            targets.discard("")

            if not targets:
                return True

            for crop_region in (
                (0, int(height * 0.1), width, height),
                (int(width * 0.25), int(height * 0.1), width, height),
                (0, 0, width, height),
            ):
                x0, y0, x1, y1 = crop_region
                crop = image.crop((x0, y0, x1, y1))
                for preprocess, label in (
                    (self._ocr_preprocess(crop), "autocontrast"),
                    (self._ocr_preprocess_binarize(crop), "binarize"),
                ):
                    for scale in (3, 4):
                        scaled = preprocess.resize((preprocess.width * scale, preprocess.height * scale))
                        for psm in (6, 7, 11, 3):
                            try:
                                text = pytesseract.image_to_string(scaled, lang="chi_sim", config=f"--psm {psm}")
                            except Exception:
                                continue
                            compact = _compact_text(text)
                            for target in targets:
                                if len(target) >= 4 and target in compact:
                                    logger.info(f"OCR验证通过: {file_name}, psm={psm}, preprocess={label}")
                                    return True
            logger.error(f"发送后未在当前聊天截图中找到文件名: {file_name}")
            return False
        except Exception as exc:
            logger.error(f"截图发送验证失败: {exc}")
            return False

    @staticmethod
    def _ocr_preprocess(image):
        from PIL import ImageOps
        return ImageOps.autocontrast(ImageOps.grayscale(image))

    @staticmethod
    def _ocr_preprocess_binarize(image):
        from PIL import ImageOps, ImageFilter
        gray = ImageOps.grayscale(image)
        gray = gray.filter(ImageFilter.SHARPEN)
        gray = ImageOps.autocontrast(gray)
        threshold = 140
        return gray.point(lambda p: 255 if p > threshold else 0)


def _compact_text(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "")).replace("-", "").replace("－", "")


def _safe_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return -1.0
