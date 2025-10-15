# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Olive Young product crawler that extracts product IDs from Excel files and crawls the Olive Young website for product information. The project uses Playwright with stealth settings to bypass CloudFlare protection and includes comprehensive progress tracking with tqdm.

## Key Commands

### Setup and Installation
```bash
# Install dependencies and set up virtual environment
make install

# Install with development dependencies (includes linting tools)
make install-dev
```

### Running the Crawler
```bash
# Main crawler execution
make run

# Resume from interrupted crawling session
make resume

# Direct execution
python main.py
```

### Testing
```bash
# Run all tests
make test

# Run tests with coverage report
make test-coverage

# Run specific test modules
make test-excel      # Excel processor tests
make test-crawler    # Crawler tests only  
make test-main       # Main crawler tests

# Run by test categories
make test-integration # Integration tests only
make test-unit       # Unit tests only
make test-fast       # Skip slow tests
```

### Code Quality
```bash
# Lint code (requires dev dependencies)
make lint

# Format code (requires dev dependencies)  
make format

# Type checking (requires dev dependencies)
make typecheck

# Run all quality checks
make quality
```

### Analysis
```bash
# Analyze crawling results and extract IDs
make analyze

# Show statistics only (no file output)
make analyze-stats
```

## Architecture

### Core Components

1. **ExcelProcessor** (`excel_processor.py`): Handles Excel file loading and filtering of product IDs starting with 'A'
2. **OliveYoungCrawler** (`crawler.py`): Main crawler with CloudFlare bypass using Playwright
3. **MainCrawler** (`main_crawler.py`): Orchestrates Excel processing and crawling with progress tracking
4. **main.py**: Entry point that delegates to MainCrawler

### Data Flow
1. Load Excel file (`data/Qoo10_ItemInfo.xlsx`) containing `seller_unique_item_id` column
2. Filter IDs starting with uppercase 'A' 
3. Crawl Olive Young product pages with throttling and stealth browser settings
4. Save results to JSON with product status, timestamps, and crawl statistics

### Key Configuration
- **Concurrency**: Default 3 simultaneous requests (configurable via `max_concurrent`)
- **Delays**: 2-4 second delays between requests (configurable via `delay_range`)  
- **Output**: Results saved to `olive_young_products.json` by default
- **Browser**: Uses headful Playwright with stealth settings and random User-Agents

### Testing Structure
- Uses pytest with asyncio support
- Test markers: `@pytest.mark.asyncio`, `@pytest.mark.slow`, `@pytest.mark.integration`, `@pytest.mark.unit`
- Mock data generation in `tests/test_data/sample_qoo10_data.py`
- Coverage reports generated to `htmlcov/` directory

### Dependencies
- **Core**: playwright, pandas, openpyxl, tqdm, aiofiles, asyncio-throttle
- **Testing**: pytest, pytest-asyncio, pytest-mock, pytest-cov
- **Development**: ruff, black, mypy, isort (optional)

## Important Files
- `data/Qoo10_ItemInfo.xlsx`: Input Excel file with product IDs
- `olive_young_products.json`: Default output file with crawl results
- `Makefile`: Contains all project commands and workflows
- `pytest.ini`: Test configuration with markers and async settings