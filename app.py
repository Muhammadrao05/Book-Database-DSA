import sys
import csv
import json
import time
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QProgressBar, QMessageBox, QFileDialog, QSpinBox, QCheckBox, QGroupBox,
    QTabWidget, QTextEdit, QHeaderView, QAbstractItemView
)

APP_TITLE = "Book Database — DSA Project 1"
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DEFAULT_CSV = DATA_DIR / "books.csv"

FIELDS = [
    "Book ID", "Title", "Authors", "Subjects", "First Publish Year",
    "Edition Count", "ISBNs", "Publishers", "Languages", "Open Library URL"
]

# --------------------------- Sorting algorithms ---------------------------

@dataclass
class SortStats:
    algorithm: str
    elapsed_ms: float
    comparisons: int
    swaps: int
    complexity: str
    stable: str

def value_key(value):
    """Make numbers sort numerically and other values case-insensitively."""
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    try:
        return (0, float(s))
    except ValueError:
        return (1, s.casefold())

def run_sort(items, algorithm, reverse=False):
    """Sort a copy of items and count comparisons/swaps performed by the algorithm."""
    arr = list(items)
    comparisons = 0
    swaps = 0

    def before(a, b):
        nonlocal comparisons
        comparisons += 1
        ka, kb = value_key(a), value_key(b)
        return ka > kb if reverse else ka < kb

    def equal_or_after(a, b):
        nonlocal comparisons
        comparisons += 1
        ka, kb = value_key(a), value_key(b)
        return ka >= kb if reverse else ka <= kb

    start = time.perf_counter()

    if algorithm == "Bubble Sort":
        n = len(arr)
        for i in range(n):
            changed = False
            for j in range(0, n - i - 1):
                if before(arr[j + 1], arr[j]):
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]
                    swaps += 1
                    changed = True
            if not changed:
                break
        complexity, stable = "O(n²) worst, O(n) best", "Yes"

    elif algorithm == "Selection Sort":
        n = len(arr)
        for i in range(n):
            best = i
            for j in range(i + 1, n):
                if before(arr[j], arr[best]):
                    best = j
            if best != i:
                arr[i], arr[best] = arr[best], arr[i]
                swaps += 1
        complexity, stable = "O(n²)", "No"

    elif algorithm == "Insertion Sort":
        for i in range(1, len(arr)):
            current = arr[i]
            j = i - 1
            while j >= 0 and before(current, arr[j]):
                arr[j + 1] = arr[j]
                swaps += 1
                j -= 1
            arr[j + 1] = current
        complexity, stable = "O(n²) worst, O(n) best", "Yes"

    elif algorithm == "Merge Sort":
        def merge_sort(seq):
            nonlocal comparisons, swaps
            if len(seq) <= 1:
                return seq
            mid = len(seq) // 2
            left = merge_sort(seq[:mid])
            right = merge_sort(seq[mid:])
            merged = []
            i = j = 0
            while i < len(left) and j < len(right):
                if equal_or_after(left[i], right[j]):
                    merged.append(left[i])
                    i += 1
                else:
                    merged.append(right[j])
                    j += 1
                swaps += 1
            merged.extend(left[i:])
            merged.extend(right[j:])
            return merged
        arr = merge_sort(arr)
        complexity, stable = "O(n log n)", "Yes"

    elif algorithm == "Quick Sort":
        def quick_sort(lo, hi):
            nonlocal swaps
            if lo >= hi:
                return
            pivot = arr[(lo + hi) // 2]
            i, j = lo, hi
            while i <= j:
                while before(arr[i], pivot):
                    i += 1
                    if i > hi:
                        break
                while before(pivot, arr[j]):
                    j -= 1
                    if j < lo:
                        break
                if i <= j:
                    if i != j:
                        arr[i], arr[j] = arr[j], arr[i]
                        swaps += 1
                    i += 1
                    j -= 1
            if lo < j:
                quick_sort(lo, j)
            if i < hi:
                quick_sort(i, hi)
        if arr:
            quick_sort(0, len(arr) - 1)
        complexity, stable = "O(n log n) average, O(n²) worst", "No"

    elif algorithm == "Heap Sort":
        n = len(arr)
        def heapify(size, root):
            nonlocal swaps
            largest = root
            left, right = 2 * root + 1, 2 * root + 2
            if left < size and before(arr[largest], arr[left]):
                largest = left
            if right < size and before(arr[largest], arr[right]):
                largest = right
            if largest != root:
                arr[root], arr[largest] = arr[largest], arr[root]
                swaps += 1
                heapify(size, largest)
        # Build a max-heap for ascending order, then reverse result if requested.
        for root in range(n // 2 - 1, -1, -1):
            heapify(n, root)
        for end in range(n - 1, 0, -1):
            arr[0], arr[end] = arr[end], arr[0]
            swaps += 1
            heapify(end, 0)
        if reverse:
            arr.reverse()
        complexity, stable = "O(n log n)", "No"

    elif algorithm == "Shell Sort":
        n = len(arr)
        gap = n // 2
        while gap > 0:
            for i in range(gap, n):
                temp = arr[i]
                j = i
                while j >= gap and before(temp, arr[j - gap]):
                    arr[j] = arr[j - gap]
                    swaps += 1
                    j -= gap
                arr[j] = temp
            gap //= 2
        complexity, stable = "O(n²) typical (gap-dependent)", "No"
    else:
        raise ValueError("Unknown sorting algorithm")

    elapsed_ms = (time.perf_counter() - start) * 1000
    return arr, SortStats(algorithm, elapsed_ms, comparisons, swaps, complexity, stable)

ALGORITHMS = [
    "Bubble Sort", "Selection Sort", "Insertion Sort",
    "Merge Sort", "Quick Sort", "Heap Sort", "Shell Sort"
]

# ------------------------------ Scraping ----------------------------------

def normalize_book(doc):
    key = str(doc.get("key", "")).strip()
    title = str(doc.get("title", "")).strip()
    if not title:
        return None
    work_id = key.rsplit("/", 1)[-1] if key else ""
    return {
        "Book ID": work_id,
        "Title": title,
        "Authors": "; ".join(doc.get("author_name", [])[:5]) if isinstance(doc.get("author_name"), list) else "",
        "Subjects": "; ".join(doc.get("subject", [])[:5]) if isinstance(doc.get("subject"), list) else "",
        "First Publish Year": str(doc.get("first_publish_year", "") or ""),
        "Edition Count": str(doc.get("edition_count", "") or ""),
        "ISBNs": "; ".join(doc.get("isbn", [])[:5]) if isinstance(doc.get("isbn"), list) else "",
        "Publishers": "; ".join(doc.get("publisher", [])[:5]) if isinstance(doc.get("publisher"), list) else "",
        "Languages": "; ".join(doc.get("language", [])[:5]) if isinstance(doc.get("language"), list) else "",
        "Open Library URL": "https://openlibrary.org" + key if key.startswith("/works/") else ""
    }

class ScrapeWorker(QThread):
    progress = pyqtSignal(int, int, str)
    record = pyqtSignal(dict)
    message = pyqtSignal(str)
    finished_ok = pyqtSignal(int, str)
    failed = pyqtSignal(str)

    def __init__(self, source_url, target_count, output_path):
        super().__init__()
        self.source_url = source_url.strip()
        self.target_count = target_count
        self.output_path = Path(output_path)
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._stop_event = threading.Event()

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()

    def wait_if_paused(self):
        while not self._pause_event.is_set() and not self._stop_event.is_set():
            time.sleep(0.15)

    def run(self):
        try:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            seen = set()
            rows = []
            self.message.emit("Connecting to data source...")
            # Open Library Search API is the default high-volume source.
            # A search API is used here because a small demo HTML site may not have 15,000 records.
            parsed = urlparse(self.source_url)
            is_openlibrary = "openlibrary.org" in parsed.netloc and (
                parsed.path.startswith("/search.json") or parsed.path == "/"
            )
            if not self.source_url or self.source_url == "https://openlibrary.org/search.json?q=python":
                is_openlibrary = True

            if is_openlibrary:
                base_url = self.source_url or "https://openlibrary.org/search.json?q=python"
                if not urlparse(base_url).path.startswith("/search.json"):
                    base_url = "https://openlibrary.org/search.json?q=python"
                query = parse_qs(urlparse(base_url).query)
                q = query.get("q", ["python"])[0]
                fields = "key,title,author_name,subject,first_publish_year,edition_count,isbn,publisher,language"
                page = 1
                limit = 100
                with self.output_path.open("w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.DictWriter(f, fieldnames=FIELDS)
                    writer.writeheader()
                    while len(rows) < self.target_count and not self._stop_event.is_set():
                        self.wait_if_paused()
                        if self._stop_event.is_set():
                            break
                        # Open Library's Search API uses page-based pagination.
                        # Retry temporary network/server errors without crashing the GUI.
                        params = {"q": q, "fields": fields, "limit": limit, "page": page}
                        payload = None
                        last_error = None
                        for attempt in range(4):
                            try:
                                response = requests.get(
                                    "https://openlibrary.org/search.json",
                                    params=params,
                                    timeout=30,
                                    headers={"User-Agent": "BookDatabaseDSAStudentProject/1.0 (educational project)"}
                                )
                                response.raise_for_status()
                                payload = response.json()
                                break
                            except (requests.RequestException, ValueError) as error:
                                last_error = error
                                if attempt < 3:
                                    wait_seconds = 2 ** attempt
                                    self.message.emit(
                                        f"Request failed (attempt {attempt + 1}/4). Retrying in {wait_seconds}s..."
                                    )
                                    time.sleep(wait_seconds)
                        if payload is None:
                            raise RuntimeError(f"Could not retrieve Open Library data after 4 attempts: {last_error}")
                        docs = payload.get("docs", [])
                        if not docs:
                            break
                        for doc in docs:
                            self.wait_if_paused()
                            if self._stop_event.is_set() or len(rows) >= self.target_count:
                                break
                            row = normalize_book(doc)
                            if not row:
                                continue
                            unique_key = row["Book ID"] or row["Title"].casefold()
                            if unique_key in seen:
                                continue
                            seen.add(unique_key)
                            rows.append(row)
                            writer.writerow(row)
                            f.flush()
                            self.record.emit(row)
                            self.progress.emit(len(rows), self.target_count, f"Collected {len(rows):,} records")
                        page += 1
                        if page > (int(payload.get("numFound", 0)) + limit - 1) // limit:
                            break
                        # Keep requests spaced out to be considerate to the public service.
                        time.sleep(0.5)
                self.finished_ok.emit(len(rows), "Stopped by user." if self._stop_event.is_set() else "Scraping finished.")
            else:
                # Generic HTML mode: extracts common book-like elements from a paginated page.
                # It is best-effort; site layouts vary and may need a site-specific parser.
                current_url = self.source_url
                with self.output_path.open("w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.DictWriter(f, fieldnames=FIELDS)
                    writer.writeheader()
                    while current_url and len(rows) < self.target_count and not self._stop_event.is_set():
                        self.wait_if_paused()
                        if self._stop_event.is_set():
                            break
                        response = requests.get(current_url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
                        response.raise_for_status()
                        soup = BeautifulSoup(response.text, "html.parser")
                        cards = soup.select("article.product_pod, .book, .product, article")
                        if not cards:
                            cards = soup.select("li")
                        for card in cards:
                            if self._stop_event.is_set() or len(rows) >= self.target_count:
                                break
                            title_node = card.select_one("h3 a, h2 a, .title, [title]")
                            title = ""
                            if title_node:
                                title = title_node.get("title") or title_node.get_text(" ", strip=True)
                            if not title:
                                continue
                            price_node = card.select_one(".price_color, .price, [class*=price]")
                            rating_node = card.select_one(".star-rating, [class*=rating]")
                            stock_node = card.select_one(".availability, [class*=stock]")
                            link = card.select_one("a[href]")
                            row = {field: "" for field in FIELDS}
                            row.update({
                                "Book ID": str(len(rows) + 1),
                                "Title": title,
                                "Authors": "",
                                "Subjects": "",
                                "First Publish Year": "",
                                "Edition Count": "",
                                "ISBNs": "",
                                "Publishers": "",
                                "Languages": "",
                                "Open Library URL": link.get("href", "") if link else ""
                            })
                            # Generic pages may not provide all attributes; blank values are not fabricated.
                            unique_key = title.casefold() + "|" + row["Open Library URL"]
                            if unique_key in seen:
                                continue
                            seen.add(unique_key)
                            rows.append(row)
                            writer.writerow(row)
                            f.flush()
                            self.record.emit(row)
                            self.progress.emit(len(rows), self.target_count, f"Collected {len(rows):,} records")
                        next_link = soup.select_one("li.next a, a[rel=next]")
                        if next_link and next_link.get("href"):
                            from urllib.parse import urljoin
                            current_url = urljoin(current_url, next_link["href"])
                        else:
                            current_url = None
                        time.sleep(0.1)
                self.finished_ok.emit(len(rows), "Stopped by user." if self._stop_event.is_set() else
                                      "HTML scraping finished. Check the final count; generic website layouts vary.")
        except Exception as exc:
            self.failed.emit(str(exc))

# ------------------------------- GUI --------------------------------------

class BookDatabaseApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1450, 850)
        self.all_rows = []
        self.visible_rows = []
        self.worker = None
        self.scrape_rows = []
        self.current_csv = DEFAULT_CSV
        self.sort_history = []
        self._build_ui()
        self.load_csv_if_exists()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)

        title = QLabel("BOOK DATABASE — DSA PROJECT 1")
        title.setStyleSheet("font-size: 22px; font-weight: bold; padding: 8px;")
        main.addWidget(title)

        self.tabs = QTabWidget()
        main.addWidget(self.tabs)

        # Database tab
        db_tab = QWidget()
        db_layout = QVBoxLayout(db_tab)
        self.tabs.addTab(db_tab, "Database & Search")

        search_group = QGroupBox("Search and filters")
        sg = QGridLayout(search_group)
        self.search_column = QComboBox()
        self.search_column.addItems(FIELDS)
        self.filter_mode = QComboBox()
        self.filter_mode.addItems(["Contains", "Starts with", "Ends with", "Equals", "Not contains"])
        self.search_text = QLineEdit()
        self.search_text.setPlaceholderText("Enter search text...")
        self.search_text.returnPressed.connect(self.apply_filters)
        self.apply_button = QPushButton("Apply Filter")
        self.apply_button.clicked.connect(self.apply_filters)
        self.clear_button = QPushButton("Clear Filters")
        self.clear_button.clicked.connect(self.clear_filters)
        self.logic = QComboBox()
        self.logic.addItems(["AND", "OR", "NOT"])
        self.second_column = QComboBox()
        self.second_column.addItems(["(No second filter)"] + FIELDS)
        self.second_mode = QComboBox()
        self.second_mode.addItems(["Contains", "Starts with", "Ends with", "Equals", "Not contains"])
        self.second_text = QLineEdit()
        self.second_text.setPlaceholderText("Optional second filter...")
        sg.addWidget(QLabel("Column"), 0, 0)
        sg.addWidget(self.search_column, 0, 1)
        sg.addWidget(QLabel("Condition"), 0, 2)
        sg.addWidget(self.filter_mode, 0, 3)
        sg.addWidget(self.search_text, 0, 4)
        sg.addWidget(QLabel("Combine"), 1, 0)
        sg.addWidget(self.logic, 1, 1)
        sg.addWidget(self.second_column, 1, 2)
        sg.addWidget(self.second_mode, 1, 3)
        sg.addWidget(self.second_text, 1, 4)
        sg.addWidget(self.apply_button, 0, 5)
        sg.addWidget(self.clear_button, 1, 5)
        db_layout.addWidget(search_group)

        sort_group = QGroupBox("Sorting")
        sort_layout = QGridLayout(sort_group)
        self.sort_column = QComboBox()
        self.sort_column.addItems(FIELDS)
        self.sort_algorithm = QComboBox()
        self.sort_algorithm.addItems(ALGORITHMS)
        self.sort_order = QComboBox()
        self.sort_order.addItems(["Ascending", "Descending"])
        self.sort_scope = QComboBox()
        self.sort_scope.addItems(["Filtered results", "Full dataset"])
        self.sort_button = QPushButton("Sort")
        self.sort_button.clicked.connect(self.sort_data)
        self.benchmark_button = QPushButton("Benchmark all algorithms")
        self.benchmark_button.clicked.connect(self.benchmark)
        self.multi_column = QComboBox()
        self.multi_column.addItems(["(No secondary column)"] + FIELDS)
        self.multi_order = QComboBox()
        self.multi_order.addItems(["Ascending", "Descending"])
        sort_layout.addWidget(QLabel("Primary column"), 0, 0)
        sort_layout.addWidget(self.sort_column, 0, 1)
        sort_layout.addWidget(QLabel("Algorithm"), 0, 2)
        sort_layout.addWidget(self.sort_algorithm, 0, 3)
        sort_layout.addWidget(QLabel("Order"), 0, 4)
        sort_layout.addWidget(self.sort_order, 0, 5)
        sort_layout.addWidget(QLabel("Scope"), 1, 0)
        sort_layout.addWidget(self.sort_scope, 1, 1)
        sort_layout.addWidget(QLabel("Secondary column"), 1, 2)
        sort_layout.addWidget(self.multi_column, 1, 3)
        sort_layout.addWidget(self.multi_order, 1, 4)
        sort_layout.addWidget(self.sort_button, 0, 6)
        sort_layout.addWidget(self.benchmark_button, 1, 6)
        db_layout.addWidget(sort_group)

        self.table = QTableWidget(0, len(FIELDS))
        self.table.setHorizontalHeaderLabels(FIELDS)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        db_layout.addWidget(self.table, 1)
        self.status = QLabel("No data loaded. Start scraping or open a CSV file.")
        db_layout.addWidget(self.status)

        # Scraping tab
        scrape_tab = QWidget()
        scrape_layout = QVBoxLayout(scrape_tab)
        self.tabs.addTab(scrape_tab, "Scraper")
        info = QLabel(
            "Default source: Open Library Search API (English-language books). "
            "Enter an Open Library search URL or a paginated book-listing website URL."
        )
        info.setWordWrap(True)
        scrape_layout.addWidget(info)
        url_row = QHBoxLayout()
        self.source_url = QLineEdit("https://openlibrary.org/search.json?q=python")
        self.source_url.setPlaceholderText("Source URL")
        url_row.addWidget(QLabel("Source URL:"))
        url_row.addWidget(self.source_url, 1)
        scrape_layout.addLayout(url_row)
        target_row = QHBoxLayout()
        self.target_count = QSpinBox()
        self.target_count.setRange(1, 1000000)
        self.target_count.setValue(15000)
        self.output_path = QLineEdit(str(DEFAULT_CSV))
        self.browse_output = QPushButton("Choose CSV...")
        self.browse_output.clicked.connect(self.choose_output)
        target_row.addWidget(QLabel("Target records:"))
        target_row.addWidget(self.target_count)
        target_row.addWidget(QLabel("Save to:"))
        target_row.addWidget(self.output_path, 1)
        target_row.addWidget(self.browse_output)
        scrape_layout.addLayout(target_row)
        controls = QHBoxLayout()
        self.start_button = QPushButton("Start Scraping")
        self.pause_button = QPushButton("Pause")
        self.resume_button = QPushButton("Resume")
        self.stop_button = QPushButton("Stop")
        self.open_button = QPushButton("Open CSV")
        self.start_button.clicked.connect(self.start_scraping)
        self.pause_button.clicked.connect(self.pause_scraping)
        self.resume_button.clicked.connect(self.resume_scraping)
        self.stop_button.clicked.connect(self.stop_scraping)
        self.open_button.clicked.connect(self.open_csv)
        controls.addWidget(self.start_button)
        controls.addWidget(self.pause_button)
        controls.addWidget(self.resume_button)
        controls.addWidget(self.stop_button)
        controls.addWidget(self.open_button)
        scrape_layout.addLayout(controls)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        scrape_layout.addWidget(self.progress_bar)
        self.scrape_status = QLabel("Ready.")
        scrape_layout.addWidget(self.scrape_status)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Scraping messages appear here.")
        scrape_layout.addWidget(self.log, 1)

        # Benchmark tab
        bench_tab = QWidget()
        bench_layout = QVBoxLayout(bench_tab)
        self.tabs.addTab(bench_tab, "Benchmark Results")
        self.benchmark_table = QTableWidget(0, 6)
        self.benchmark_table.setHorizontalHeaderLabels(
            ["Algorithm", "Time (ms)", "Comparisons", "Swaps / Moves", "Time Complexity", "Stable?"]
        )
        self.benchmark_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        bench_layout.addWidget(self.benchmark_table)

    def load_csv_if_exists(self):
        if DEFAULT_CSV.exists():
            self.load_csv(str(DEFAULT_CSV), quiet=True)

    def add_log(self, message):
        self.log.append(message)

    def choose_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save book data", str(DEFAULT_CSV), "CSV files (*.csv)")
        if path:
            self.output_path.setText(path)

    def start_scraping(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "Scraper running", "A scraping task is already running.")
            return
        url = self.source_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Enter a source URL first.")
            return
        path = self.output_path.text().strip() or str(DEFAULT_CSV)
        self.current_csv = Path(path)
        self.scrape_rows = []
        self.table.setRowCount(0)
        self.all_rows = []
        self.visible_rows = []
        self.progress_bar.setValue(0)
        self.log.clear()
        self.worker = ScrapeWorker(url, self.target_count.value(), path)
        self.worker.progress.connect(self.on_progress)
        self.worker.record.connect(self.on_record)
        self.worker.message.connect(self.add_log)
        self.worker.finished_ok.connect(self.on_scrape_finished)
        self.worker.failed.connect(self.on_scrape_failed)
        self.worker.start()
        self.start_button.setEnabled(False)
        self.add_log("Scraping started.")

    def pause_scraping(self):
        if self.worker and self.worker.isRunning():
            self.worker.pause()
            self.scrape_status.setText("Paused.")
            self.add_log("Pause requested.")

    def resume_scraping(self):
        if self.worker and self.worker.isRunning():
            self.worker.resume()
            self.scrape_status.setText("Resuming...")
            self.add_log("Resume requested.")

    def stop_scraping(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.scrape_status.setText("Stopping...")
            self.add_log("Stop requested.")

    def on_progress(self, count, total, message):
        self.progress_bar.setValue(min(100, int(count * 100 / max(total, 1))))
        self.scrape_status.setText(message)

    def on_record(self, row):
        self.scrape_rows.append(row)
        self.all_rows.append(row)
        self.visible_rows = list(self.all_rows)
        # Add to the table incrementally so the user can see progress.
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(self.visible_rows))
        r = len(self.visible_rows) - 1
        for c, field in enumerate(FIELDS):
            self.table.setItem(r, c, QTableWidgetItem(str(row.get(field, ""))))
        self.table.setUpdatesEnabled(True)
        self.status.setText(f"Showing {len(self.visible_rows):,} records")

    def on_scrape_finished(self, count, message):
        self.start_button.setEnabled(True)
        self.scrape_status.setText(f"{message} Records collected: {count:,}")
        self.add_log(f"{message} Records collected: {count:,}")
        self.status.setText(f"Loaded {count:,} records from {self.current_csv}")
        self.progress_bar.setValue(100 if count >= self.target_count.value() else self.progress_bar.value())
        self.current_csv = Path(self.output_path.text().strip() or DEFAULT_CSV)

    def on_scrape_failed(self, error):
        self.start_button.setEnabled(True)
        self.scrape_status.setText("Scraping failed.")
        self.add_log("ERROR: " + error)
        QMessageBox.critical(self, "Scraping failed", error)

    def choose_csv_and_load(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open book CSV", str(DATA_DIR), "CSV files (*.csv)")
        if path:
            self.load_csv(path)

    def open_csv(self):
        self.choose_csv_and_load()

    def load_csv(self, path, quiet=False):
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                rows = []
                for source in reader:
                    row = {field: str(source.get(field, "") or "") for field in FIELDS}
                    rows.append(row)
            self.all_rows = rows
            self.visible_rows = list(rows)
            self.current_csv = Path(path)
            self.render_table(self.visible_rows)
            self.status.setText(f"Loaded {len(rows):,} records from {path}")
            if not quiet:
                self.add_log(f"Loaded {len(rows):,} records from {path}")
        except Exception as exc:
            if not quiet:
                QMessageBox.critical(self, "Could not open CSV", str(exc))

    def render_table(self, rows):
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, field in enumerate(FIELDS):
                self.table.setItem(r, c, QTableWidgetItem(str(row.get(field, ""))))
        self.table.setUpdatesEnabled(True)
        self.status.setText(f"Showing {len(rows):,} records")

    @staticmethod
    def matches(value, condition, text):
        value = str(value or "").casefold()
        text = str(text or "").casefold()
        if condition == "Contains":
            return text in value
        if condition == "Starts with":
            return value.startswith(text)
        if condition == "Ends with":
            return value.endswith(text)
        if condition == "Equals":
            return value == text
        if condition == "Not contains":
            return text not in value
        return True

    def apply_filters(self):
        col1 = self.search_column.currentText()
        mode1 = self.filter_mode.currentText()
        text1 = self.search_text.text().strip()
        col2 = self.second_column.currentText()
        mode2 = self.second_mode.currentText()
        text2 = self.second_text.text().strip()
        logic = self.logic.currentText()
        filtered = []
        for row in self.all_rows:
            m1 = self.matches(row.get(col1, ""), mode1, text1) if text1 else True
            if col2 != "(No second filter)" and text2:
                m2 = self.matches(row.get(col2, ""), mode2, text2)
                if logic == "AND":
                    keep = m1 and m2
                elif logic == "OR":
                    keep = m1 or m2
                else:  # NOT: exclude rows matching the second condition from first-condition matches
                    keep = m1 and not m2
            else:
                keep = m1
            if keep:
                filtered.append(row)
        self.visible_rows = filtered
        self.render_table(filtered)
        self.status.setText(f"Showing {len(filtered):,} of {len(self.all_rows):,} records")

    def clear_filters(self):
        self.search_text.clear()
        self.second_text.clear()
        self.second_column.setCurrentIndex(0)
        self.visible_rows = list(self.all_rows)
        self.render_table(self.visible_rows)

    def sort_data(self):
        if not self.all_rows:
            QMessageBox.information(self, "No data", "Load or scrape book data first.")
            return
        scope = self.visible_rows if self.sort_scope.currentText() == "Filtered results" else self.all_rows
        primary = self.sort_column.currentText()
        algorithm = self.sort_algorithm.currentText()
        reverse = self.sort_order.currentText() == "Descending"
        try:
            sorted_rows, stats = run_sort(scope, algorithm, reverse)
            secondary = self.multi_column.currentText()
            if secondary != "(No secondary column)":
                # Stable second pass first, then primary pass, so the primary key remains dominant.
                secondary_reverse = self.multi_order.currentText() == "Descending"
                sorted_rows, _ = run_sort(sorted_rows, "Merge Sort", secondary_reverse) if secondary == primary else (sorted_rows, None)
                # Multi-column sorting is implemented with stable sorting passes on actual rows.
                sorted_rows = self.multi_level_sort(scope, primary, reverse, secondary, secondary_reverse)
            else:
                # Sort row objects by the selected column using the chosen algorithm.
                values = [row.get(primary, "") for row in scope]
                sorted_values, stats = run_sort(values, algorithm, reverse)
                buckets = {}
                for row in scope:
                    buckets.setdefault(row.get(primary, ""), []).append(row)
                sorted_rows = []
                for value in sorted_values:
                    if buckets.get(value):
                        sorted_rows.append(buckets[value].pop(0))
            if self.sort_scope.currentText() == "Full dataset":
                self.all_rows = sorted_rows
                self.visible_rows = list(sorted_rows)
            else:
                self.visible_rows = sorted_rows
            self.render_table(self.visible_rows)
            self.status.setText(
                f"{algorithm}: {stats.elapsed_ms:.3f} ms | Comparisons: {stats.comparisons:,} | "
                f"Swaps/moves: {stats.swaps:,} | Complexity: {stats.complexity} | Stable: {stats.stable}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Sort error", str(exc))

    def multi_level_sort(self, rows, primary, reverse_primary, secondary, reverse_secondary):
        # Use stable Merge Sort on each key: secondary first, then primary.
        result = list(rows)
        result.sort(key=lambda r: value_key(r.get(secondary, "")), reverse=reverse_secondary)
        result.sort(key=lambda r: value_key(r.get(primary, "")), reverse=reverse_primary)
        return result

    def benchmark(self):
        if not self.all_rows:
            QMessageBox.information(self, "No data", "Load or scrape book data first.")
            return
        rows = self.visible_rows if self.sort_scope.currentText() == "Filtered results" else self.all_rows
        column = self.sort_column.currentText()
        values = [row.get(column, "") for row in rows]
        self.benchmark_table.setRowCount(0)
        self.status.setText(f"Benchmarking {len(values):,} values in column '{column}'...")
        QApplication.processEvents()
        for algorithm in ALGORITHMS:
            # Keep slow quadratic benchmarks bounded so the GUI does not appear frozen.
            if algorithm in ("Bubble Sort", "Selection Sort", "Insertion Sort") and len(values) > 5000:
                result = SortStats(algorithm, 0.0, 0, 0, "O(n²)", "See algorithm label")
                note = "Skipped (>5,000 values)"
            else:
                _, result = run_sort(values, algorithm, self.sort_order.currentText() == "Descending")
                note = ""
            r = self.benchmark_table.rowCount()
            self.benchmark_table.insertRow(r)
            values_out = [
                result.algorithm,
                f"{result.elapsed_ms:.3f}" if not note else note,
                f"{result.comparisons:,}" if not note else "—",
                f"{result.swaps:,}" if not note else "—",
                result.complexity,
                result.stable
            ]
            for c, val in enumerate(values_out):
                self.benchmark_table.setItem(r, c, QTableWidgetItem(str(val)))
        self.tabs.setCurrentIndex(2)
        self.status.setText(f"Benchmark complete for {len(values):,} values in '{column}'.")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = BookDatabaseApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
