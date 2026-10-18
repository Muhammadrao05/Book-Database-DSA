# Book Database — CS200 DSA Project 1

A beginner-friendly Python desktop application for collecting book records, viewing them in a table, searching/filtering, sorting, and benchmarking sorting algorithms.

## Included features

- PyQt6 desktop GUI
- Book dataset with 10 fields
- Open Library Search API source configured by default
- Target record count defaults to 15,000
- Start / pause / resume / stop controls and progress bar
- Saves records to CSV while scraping
- Load an existing CSV file
- Contains / starts with / ends with / equals / not-contains filters
- Two-filter AND / OR / NOT logic
- Seven sorting algorithms: Bubble, Selection, Insertion, Merge, Quick, Heap, Shell
- Sort timing, comparisons, swaps/moves, complexity and stability labels
- Benchmark table
- Multi-column sorting controls

## Important project notes

1. The assignment guideline asks for at least 15,000 entities and at least 8 attributes. The program requests up to 15,000 records by default, but the final number depends on source availability, API limits, duplicates, network access, and the query. Confirm the final count in `data/books.csv`.
2. The default source is the Open Library Search API. This is a public search API rather than parsing the HTML of a website. If your instructor strictly requires HTML web scraping, use the URL input with a permitted paginated book-listing website and verify that it provides enough records. Generic HTML parsing is best-effort and may need site-specific selectors.
3. Public services can rate-limit requests or change their response. If scraping stops early, the log shows the error or the number collected.
4. Quadratic algorithms (Bubble, Selection, Insertion) are skipped in the benchmark when more than 5,000 values are selected, to avoid very long runs. Reduce the filtered dataset size to benchmark them on the full list.
5. The assignment says to include every sorting algorithm studied in class plus at least two additional algorithms. The exact class list was not included in the guideline PDF, so compare the list in `app.py` with your lecture notes and adjust if needed.
6. The displayed comparison and swap/move counts are implementation-level metrics. Merge sort counts merge writes as moves; insertion sort counts shifts as moves. Counts can differ between implementations.
7. The program includes a stable Python sort for the multi-level sorting feature. If your teacher requires every sort operation to use your own algorithm implementation, replace `multi_level_sort` with stable passes using the custom Merge Sort implementation.

## Setup on Windows / VS Code

1. Install Python 3.11 or newer from https://www.python.org/downloads/
2. Extract the ZIP folder.
3. Open the `Book_DSA_Project` folder in VS Code.
4. Open **Terminal → New Terminal**.
5. Create a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use Command Prompt terminal and run:

   ```bat
   .venv\Scripts\activate.bat
   ```

6. Install packages:

   ```bash
   python -m pip install -r requirements.txt
   ```

7. Run the program:

   ```bash
   python app.py
   ```

8. Open the **Scraper** tab. The default URL is an Open Library search URL. Keep the target at 15,000 and click **Start Scraping**.
9. Wait for the progress bar to finish. You can pause/resume/stop. The CSV is saved in `data/books.csv` by default.
10. Return to **Database & Search** to search and sort the collected records.

## Dataset fields

- Book ID
- Title
- Authors
- Subjects
- First Publish Year
- Edition Count
- ISBNs
- Publishers
- Languages
- Open Library URL

Some records may have blank values because source records do not always contain every field. Missing source data is not fabricated.

## Submission checklist

- [ ] Program runs on the evaluation computer
- [ ] Screenshot of the GUI
- [ ] CSV contains 15,000 or more unique records (verify actual count)
- [ ] At least 8 populated/defined attributes are present
- [ ] All class sorting algorithms plus two additional algorithms are included
- [ ] Sorting metrics and complexity/stability labels checked against lecture expectations
- [ ] Benchmark results tested on a manageable dataset
- [ ] Search operators and multi-level sorting tested
- [ ] Scraping pause/resume/stop tested
- [ ] Be ready to explain each function and algorithm during evaluation
