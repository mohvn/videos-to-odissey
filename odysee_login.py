#!/usr/bin/env python3
"""
Selenium RPA script to log in to Odysee at https://odysee.com/$/signin
and optionally upload videos from a local folder.
Uses ODYSEE_EMAIL and ODYSEE_PASSWORD from environment or .env file.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
import traceback
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

SIGNIN_URL = "https://odysee.com/$/signin"
UPLOAD_URL = "https://odysee.com/$/upload"
UPLOADS_URL = "https://odysee.com/$/uploads"
HOME_URL_PATTERN = re.compile(r"^https://odysee\.com(/.*)?$")
DEFAULT_TIMEOUT = 15
UPLOAD_PAGE_LOAD_WAIT = 5
UPLOAD_WAIT_AFTER_VIDEO = 3
UPLOAD_WAIT_AFTER_THUMB_SELECT = 0.5
UPLOAD_WAIT_AFTER_THUMB = 2
UPLOAD_COMPLETE_TIMEOUT = 600
STEP_TIMEOUT = 60
REDIRECT_TIMEOUT = 180
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mkv", ".mov", ".avi"}

# ANSI colors (desativados se não for TTY)
C_RESET = "\033[0m"
C_RED = "\033[91m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_CYAN = "\033[96m"


def _color(code: str, text: str, use_color: bool = True) -> str:
    tty = sys.stdout.isatty() or sys.stderr.isatty()
    return f"{code}{text}{C_RESET}" if use_color and tty else text


def _log(msg: str, verbose: bool = True, prefix: str = "[ - ]", color: str = C_CYAN) -> None:
    if verbose:
        p = _color(color, prefix)
        print(f"  {p} {msg}")


def load_credentials(base_path: Path | None = None) -> tuple[str, str]:
    """Load email and password from env or .env. Raises SystemExit if missing."""
    if load_dotenv:
        if base_path is not None:
            env_path = base_path / ".env"
            if env_path.is_file():
                load_dotenv(env_path)
        else:
            load_dotenv()
    email = os.environ.get("ODYSEE_EMAIL", "").strip()
    password = os.environ.get("ODYSEE_PASSWORD", "").strip()
    if not email:
        print(_color(C_RED, "[ x ] ODYSEE_EMAIL não definido. Defina no .env ou nas variáveis de ambiente."), file=sys.stderr)
        sys.exit(1)
    if not password:
        print(_color(C_RED, "[ x ] ODYSEE_PASSWORD não definido. Defina no .env ou nas variáveis de ambiente."), file=sys.stderr)
        sys.exit(1)
    return email, password


def create_driver(headless: bool) -> webdriver.Chrome:
    """Create Chrome WebDriver, using webdriver-manager if available."""
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    except ImportError:
        return webdriver.Chrome(options=options)


def login(
    driver: webdriver.Chrome,
    email: str,
    password: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> bool:
    """
    Perform Odysee signin flow: email -> Log In -> password -> Continue.
    Returns True if redirected to https://odysee.com/, False otherwise.
    """
    wait = WebDriverWait(driver, timeout)
    driver.get(SIGNIN_URL)

    # Step 1: Email
    email_input = wait.until(EC.presence_of_element_located((By.ID, "username")))
    email_input.clear()
    email_input.send_keys(email)

    log_in_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Log In"]')))
    log_in_btn.click()

    # Step 2: Password (appears after Log In)
    password_input = wait.until(EC.presence_of_element_located((By.ID, "password")))
    password_input.clear()
    password_input.send_keys(password)

    continue_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Continue"]')))
    continue_btn.click()

    # Step 3: Wait for redirect off signin page (e.g. https://odysee.com/ or /$/discover)
    wait.until(lambda d: "signin" not in d.current_url and HOME_URL_PATTERN.match(d.current_url))
    return True


SUCCESS_MODAL_LABELS = ("Update published", "File published")


def _dismiss_success_modals(driver: webdriver.Chrome, verbose: bool = True) -> bool:
    """Fechar modais 'Update published' ou 'File published' se visíveis. Retorna True se algum foi fechado."""
    try:
        for label in SUCCESS_MODAL_LABELS:
            modals = driver.find_elements(By.CSS_SELECTOR, f'[aria-label="{label}"]')
            for m in modals:
                if m.is_displayed():
                    # Prefer "View My Uploads" (navega para /$/uploads); senão Close
                    view_uploads = m.find_elements(By.CSS_SELECTOR, 'button[aria-label="View My Uploads"]')
                    if view_uploads and view_uploads[0].is_displayed():
                        view_uploads[0].click()
                        _log(f"Modal '{label}': clicado 'View My Uploads'", verbose, "[ + ]", C_GREEN)
                        time.sleep(0.5)
                        return True
                    close_btns = m.find_elements(By.CSS_SELECTOR, 'button[aria-label="Close"]')
                    for btn in close_btns:
                        if btn.is_displayed():
                            btn.click()
                            _log(f"Modal '{label}' fechado", verbose, "[ + ]", C_GREEN)
                            time.sleep(0.3)
                            return True
    except Exception:
        pass
    return False


def _dismiss_update_published_modal(driver: webdriver.Chrome, verbose: bool = True) -> bool:
    """Alias para compatibilidade."""
    return _dismiss_success_modals(driver, verbose)

def _describe_button(btn) -> str:
    try:
        aria = btn.get_attribute("aria-label")
        cls = btn.get_attribute("class")
        text = (btn.text or "").strip()
        displayed = btn.is_displayed()
        enabled = btn.is_enabled()
        return f"aria={aria!r} class={cls!r} text={text!r} displayed={displayed} enabled={enabled}"
    except Exception:
        return "<button>"


def _get_clickable_primary_upload_buttons(driver: webdriver.Chrome, wait: WebDriverWait, verbose: bool) -> list:
    """
    Odysee has multiple buttons with aria-label='Upload' (including a header icon).
    Filter to primary action buttons only.
    """
    # Grab all candidates first (presence), then filter.
    candidates = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'button[aria-label="Upload"]')))
    filtered = []
    for b in candidates:
        try:
            cls = b.get_attribute("class") or ""
            if "button--primary" not in cls:
                continue
            if not b.is_displayed() or not b.is_enabled():
                continue
            filtered.append(b)
        except Exception:
            continue

    if verbose:
        _log(f"Upload candidates (all): {len(candidates)}", verbose)
        for i, b in enumerate(candidates):
            _log(f"  cand[{i}] {_describe_button(b)}", verbose)
        _log(f"Upload candidates (primary+visible): {len(filtered)}", verbose)
        for i, b in enumerate(filtered):
            _log(f"  prim[{i}] {_describe_button(b)}", verbose)

    return filtered


def _send_file_to_input(
    driver: webdriver.Chrome, file_path: Path, input_index: int = 0, verbose: bool = True
) -> None:
    """Find input[type=file] and send absolute path. Uses index if multiple inputs exist."""
    path_str = str(file_path.resolve())
    inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
    _log(f"Encontrados {len(inputs)} input(s) de ficheiro", verbose)
    if not inputs:
        raise RuntimeError("No file input found on page")
    inp = inputs[min(input_index, len(inputs) - 1)]
    _log(f"Enviando ficheiro para input {input_index}: {file_path.name}", verbose)
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", inp)
    driver.execute_script(
        "arguments[0].style.setProperty('visibility','visible'); arguments[0].style.setProperty('opacity','1');",
        inp,
    )
    time.sleep(0.5)
    inp.send_keys(path_str)


def upload_video(
    driver: webdriver.Chrome,
    video_path: Path,
    thumb_path: Path,
    wait: WebDriverWait,
    verbose: bool = True,
    step_timeout: int = STEP_TIMEOUT,
) -> None:
    """
    Upload a single video: select file, upload, select thumbnail, upload thumb,
    mark sync_toggle, confirm.
    """
    video_path = video_path.resolve()
    thumb_path = thumb_path.resolve()
    if not video_path.is_file():
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not thumb_path.is_file():
        raise FileNotFoundError(f"Thumbnail not found: {thumb_path}")

    # Step 1: Select video file
    _log("Passo 1: Selecionando vídeo", verbose, "[ * ]", C_YELLOW)
    _send_file_to_input(driver, video_path, 0, verbose)
    _log("Passo 2: Aguardando upload do vídeo", verbose, "[ * ]", C_YELLOW)
    # After upload, the form shows: input.form-field--copyable with value="<filename>"
    step_wait = WebDriverWait(driver, step_timeout)
    video_name = video_path.name

    def _video_uploaded(d) -> bool:
        try:
            for inp in d.find_elements(By.CSS_SELECTOR, "input.form-field--copyable"):
                if inp.get_attribute("value") == video_name:
                    return True
        except Exception:
            pass
        return False

    step_wait.until(_video_uploaded)
    time.sleep(UPLOAD_WAIT_AFTER_VIDEO)

    # Step 3: Select thumbnail
    _log("Passo 3: Selecionando thumbnail", verbose, "[ * ]", C_YELLOW)
    _send_file_to_input(driver, thumb_path, 1, verbose)
    time.sleep(UPLOAD_WAIT_AFTER_THUMB_SELECT)

    # Step 4: Modal "Confirm Thumbnail Upload" - click Upload inside it
    _log("Passo 4: Clicando Upload no modal de confirmação da thumbnail", verbose, "[ * ]", C_YELLOW)
    modal = step_wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label="Confirm Thumbnail Upload"]'))
    )
    thumb_upload = modal.find_element(By.CSS_SELECTOR, 'button[aria-label="Upload"]')
    step_wait.until(EC.element_to_be_clickable(thumb_upload))
    thumb_upload.click()
    # Wait for modal overlay to disappear, otherwise it can intercept later clicks
    _log("Aguardando fecho do modal da thumbnail", verbose)
    step_wait.until(
        EC.invisibility_of_element_located((By.CSS_SELECTOR, '.ReactModal__Overlay.modal-overlay'))
    )
    time.sleep(UPLOAD_WAIT_AFTER_THUMB)

    # Fechar modais "File published" / "Update published" que possam bloquear o canal
    for _ in range(5):
        if not _dismiss_success_modals(driver, verbose):
            break
        time.sleep(0.3)

    def _no_modal_overlay(d):
        for o in d.find_elements(By.CSS_SELECTOR, ".ReactModal__Overlay.modal-overlay"):
            if o.is_displayed():
                return False
        return True

    step_wait.until(_no_modal_overlay)
    time.sleep(0.5)

    # Step 5: Select channel (click selector, then option 0)
    _log("Passo 5: Selecionando canal", verbose, "[ * ]", C_YELLOW)
    # Avoid clicking the \"Prefill\" menu (also data-reach-menu-button). Target the publish channel selector only.
    channel_btn = step_wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, '.channel-selector--publish button[data-reach-menu-button]'))
    )
    channel_btn.click()
    time.sleep(0.5)
    menu_items = step_wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[role="menuitem"]'))
    )
    if not menu_items:
        raise RuntimeError("No channel option found in menu")
    step_wait.until(EC.element_to_be_clickable(menu_items[0]))
    menu_items[0].click()
    time.sleep(0.5)

    # Fechar modais "File published" / "Update published" antes de clicar no Upload principal
    for _ in range(5):
        if not _dismiss_success_modals(driver, verbose):
            break
        time.sleep(0.3)
    step_wait.until(_no_modal_overlay)
    time.sleep(0.5)

    # Step 6: Scroll to bottom and click main Upload button
    _log("Passo 6: Rolando até ao fim e clicando Upload", verbose, "[ * ]", C_YELLOW)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(0.5)
    primary_uploads = driver.find_elements(By.CSS_SELECTOR, 'button[aria-label="Upload"].button--primary')
    if not primary_uploads:
        raise RuntimeError("Primary Upload button not found at bottom of page")
    main_upload = primary_uploads[-1]
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", main_upload)
    step_wait.until(EC.element_to_be_clickable(main_upload))
    main_upload.click()
    time.sleep(UPLOAD_WAIT_AFTER_THUMB)

    # Step 7 & 8: sync_toggle + Confirm (optional - not shown when "Currently Uploading")
    sync_cbs = driver.find_elements(By.ID, "sync_toggle")
    if sync_cbs and sync_cbs[0].is_displayed():
        _log("Passo 7: Marcando sync_toggle", verbose, "[ * ]", C_YELLOW)
        sync_cb = sync_cbs[0]
        if not sync_cb.is_selected():
            try:
                label = driver.find_element(By.CSS_SELECTOR, 'label[for="sync_toggle"]')
                label.click()
            except Exception:
                driver.execute_script("arguments[0].click();", sync_cb)
        _log("Passo 8: Clicando Confirmar", verbose, "[ * ]", C_YELLOW)
        confirm_btn = step_wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Confirm"]')))
        confirm_btn.click()
    else:
        _log("sync_toggle não presente (vista 'A enviar'), a saltar", verbose)

    # Step 9: Dismiss "Update published" modal if it appears, then wait for redirect to /$/uploads
    _log("Passo 9: Aguardando redirecionamento para /$/uploads", verbose, "[ * ]", C_YELLOW)

    def _redirect_or_dismiss_modal(d):
        if _dismiss_success_modals(d, verbose):
            return False
        return d.current_url.startswith(UPLOADS_URL)

    redirect_wait = WebDriverWait(driver, REDIRECT_TIMEOUT)
    redirect_wait.until(_redirect_or_dismiss_modal)


def upload_all(
    driver: webdriver.Chrome,
    videos_dir: Path,
    thumb_path: Path,
    timeout: int = DEFAULT_TIMEOUT,
    verbose: bool = True,
    step_timeout: int = STEP_TIMEOUT,
) -> int:
    """
    Upload all videos from videos_dir. Returns number of successfully uploaded videos.
    """
    wait = WebDriverWait(driver, timeout)
    videos_dir = videos_dir.resolve()
    thumb_path = thumb_path.resolve()

    videos = sorted(
        f for f in videos_dir.iterdir()
        if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS
    )
    if not videos:
        print(_color(C_RED, f"[ x ] Nenhum vídeo encontrado em {videos_dir}"), file=sys.stderr)
        return 0

    print(_color(C_CYAN, f"[ - ] Encontrados {len(videos)} vídeo(s) em: {videos_dir}"))
    for idx, v in enumerate(videos, start=1):
        print(f"      {idx}. {v.name}")

    _log(f"Navegando para {UPLOAD_URL}", verbose)
    driver.get(UPLOAD_URL)
    _log(f"Aguardando {UPLOAD_PAGE_LOAD_WAIT}s para a página carregar", verbose)
    time.sleep(UPLOAD_PAGE_LOAD_WAIT)
    page_wait = WebDriverWait(driver, step_timeout)
    page_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']")))
    _log("Página de upload pronta", verbose, "[ + ]", C_GREEN)

    success_count = 0
    for i, video_path in enumerate(videos):
        try:
            print(_color(C_YELLOW, f"[ * ] A enviar ({i + 1}/{len(videos)}): {video_path.name}"))
            upload_video(driver, video_path, thumb_path, wait, verbose=verbose, step_timeout=step_timeout)
            success_count += 1
            print(_color(C_GREEN, f"  [ + ] Enviado: {video_path.name}"))
        except Exception as e:
            print(_color(C_RED, f"  [ x ] Vídeo falhou em upload: {video_path.name}"), file=sys.stderr)
            if verbose:
                print(f"      {e}", file=sys.stderr)
                traceback.print_exc()
            # Em falha, continua para o próximo vídeo.
            continue

        # Ir para o próximo vídeo: navegar para /$/upload
        if i < len(videos) - 1:
            _dismiss_success_modals(driver, verbose)
            _log("Navegando para página de upload", verbose)
            driver.get(UPLOAD_URL)
            time.sleep(UPLOAD_PAGE_LOAD_WAIT)
            next_wait = WebDriverWait(driver, step_timeout)
            next_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']")))

    return success_count


def _verify_uploads_confirming(driver: webdriver.Chrome, verbose: bool = True) -> None:
    """Navega para /$/uploads e verifica quantos cards estão em 'Confirming'."""
    if not driver.current_url.startswith(UPLOADS_URL):
        driver.get(UPLOADS_URL)
        time.sleep(3)
    else:
        time.sleep(2)
    try:
        cards = driver.find_elements(By.CSS_SELECTOR, ".claim-preview__wrapper.claim-preview__wrapper--row")
        confirming = [c for c in cards if c.find_elements(By.CSS_SELECTOR, ".confirming-change")]
        total = len(cards)
        conf_count = len(confirming)
        if total > 0:
            print(_color(C_CYAN, f"[ - ] Verificação: {conf_count}/{total} card(s) em 'Confirming'"))
            if conf_count == total:
                print(_color(C_GREEN, f"[ + ] Todos os cards estão a confirmar."))
            elif conf_count < total and verbose:
                print(_color(C_YELLOW, f"      Aguarde ou atualize a página para ver o estado final."))
    except Exception:
        pass


def main() -> int:
    if getattr(sys, "frozen", False):
        script_dir = Path(sys.executable).resolve().parent
    else:
        script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Log in to Odysee via Selenium RPA and optionally upload videos.")
    parser.add_argument("--no-headless", action="store_true", help="Mostrar janela do browser (por defeito corre em headless)")
    parser.add_argument("--keep-open", action="store_true", help="Manter browser aberto no fim (automático com --upload)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Wait timeout in seconds")
    parser.add_argument("--upload", action="store_true", help="After login, upload videos from --videos-dir")
    parser.add_argument(
        "--videos-dir",
        type=Path,
        default=script_dir / "videos",
        help="Folder containing videos to upload (default: videos/ in project)",
    )
    parser.add_argument(
        "--thumbnail",
        type=Path,
        default=script_dir / "thumb.jpg",
        help="Thumbnail image for all uploads (default: thumb.jpg in project)",
    )
    parser.add_argument("--no-log", action="store_true", help="Desativar logs passo a passo")
    parser.add_argument(
        "--step-timeout",
        type=int,
        default=STEP_TIMEOUT,
        help=f"Timeout por passo em segundos (default: {STEP_TIMEOUT})",
    )
    args = parser.parse_args()

    if args.upload:
        videos_dir = args.videos_dir.resolve()
        thumb_path = args.thumbnail.resolve()
        if not videos_dir.is_dir():
            print(_color(C_RED, f"[ x ] Pasta de vídeos não existe: {videos_dir}"), file=sys.stderr)
            return 1
        if not thumb_path.is_file():
            print(_color(C_RED, f"[ x ] Thumbnail não encontrada: {thumb_path}"), file=sys.stderr)
            return 1

    email, password = load_credentials(script_dir)
    driver = create_driver(headless=not args.no_headless)

    try:
        login(driver, email, password, timeout=args.timeout)
        print(_color(C_GREEN, "[ + ] Login efetuado. Redirecionado para https://odysee.com/"))

        if args.upload:
            count = upload_all(
                driver, args.videos_dir, args.thumbnail,
                timeout=args.timeout, verbose=not args.no_log,
                step_timeout=args.step_timeout,
            )
            print(_color(C_GREEN, f"[ + ] Upload concluído. {count} vídeo(s) enviado(s)."))
            _verify_uploads_confirming(driver, verbose=not args.no_log)
            args.keep_open = True  # Manter janela aberta para verificação dos cards

        if args.keep_open:
            input(_color(C_YELLOW, "Pressione Enter para fechar o browser..."))
        return 0
    except Exception as e:
        print(_color(C_RED, f"[ x ] Erro: {e}"), file=sys.stderr)
        if args.keep_open:
            input(_color(C_YELLOW, "Pressione Enter para fechar o browser..."))
        return 1
    finally:
        if not args.keep_open:
            driver.quit()


if __name__ == "__main__":
    sys.exit(main())
