# Indian Filings Pipeline MVP

A data ingestion pipeline for collecting annual filings and related documents from Indian companies listed on NSE and BSE exchanges.

## 🎯 Project Overview

This MVP collects documents from the top 50 Indian companies for use in multimodal chat PDF applications. The pipeline scrapes, validates, stores, and organizes company filings for LLM-based analysis.

### Week 1 Features (Current)
- ✅ Basic scraping from NSE and BSE portals
- ✅ Document download and validation
- ✅ PostgreSQL database storage
- ✅ File organization and management
- ✅ Comprehensive logging and monitoring
- ✅ Docker containerization

### Planned Features (Weeks 2-8)
- 📄 PDF text extraction and processing
- 🔍 Document chunking for LLM consumption
- 🌐 REST API for data access
- 📊 Advanced search and filtering
- 🔄 Automated scheduling
- 📈 Enhanced monitoring dashboard

## 🏗️ Architecture

```
indian_filings_pipeline/
├── config/               # Configuration files
├── src/
│   ├── database/         # Database models and connections
│   ├── scrapers/         # Web scrapers (NSE, BSE, Screener.in)
│   ├── storage/          # File and document management
│   └── utils/            # Utilities and helpers
├── scripts/              # Executable scripts
├── data/                 # Downloaded documents and logs
└── tests/                # Test files
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Docker & Docker Compose (optional)

### Option 1: Docker Setup (Recommended)

1. **Clone the repository**
```bash
git clone <repository-url>
cd indian_filings_pipeline
```

2. **Start services**
```bash
docker-compose up -d
```

3. **Initialize database**
```bash
docker-compose exec pipeline python scripts/setup_database.py
```

4. **Run scrapers**
```bash
docker-compose exec pipeline python scripts/run_scraper.py --limit 5
```

### Option 2: Local Development Setup

1. **Clone and setup environment**
```bash
git clone <repository-url>
cd indian_filings_pipeline
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env if needed (SQLite database path)
```

4. **Initialize database**
```bash
python scripts/setup_database.py
```

5. **Run health check**
```bash
python scripts/health_check.py
```

6. **Start scraping**
```bash
python scripts/run_scraper.py --limit 5 --log-level INFO
```

## 📖 Usage

### Running Scrapers

**Basic scraping (first 5 companies):**
```bash
python scripts/run_scraper.py --limit 5
```

**Scrape specific companies with all scrapers:**
```bash
python scripts/run_scraper.py --companies RELIANCE TCS HDFCBANK
```

**Run only NSE scraper:**
```bash
python scripts/run_scraper.py --scraper nse --limit 10
```

**Run only Screener.in scraper:**
```bash
python scripts/run_scraper.py --scraper screener --limit 5
```

**Run all three scrapers:**
```bash
python scripts/run_scraper.py --scraper all --limit 10
```

**Dry run (validation only):**
```bash
python scripts/run_scraper.py --dry-run
```

**Save results to file:**
```bash
python scripts/run_scraper.py --limit 3 --output results.json
```

### Database Operations

**Check database status:**
```bash
python scripts/health_check.py
```

**View database statistics:**
```python
from src.database.connection import get_table_stats
stats = get_table_stats()
print(stats)
```

### File Management

**Check storage usage:**
```python
from src.storage.file_manager import FileManager
fm = FileManager()
summary = fm.get_storage_summary()
print(summary)
```

**Validate file integrity:**
```python
issues = fm.validate_storage_integrity()
print(f"Found {issues['total_issues']} issues")
```

## 📊 Database Schema

### Key Tables

**Companies**: Master list of 50 companies
- `symbol`, `name`, `sector`, `exchange`
- `bse_code`, `nse_symbol`, `website`, `ir_page`

**Documents**: Downloaded document metadata
- `title`, `document_type`, `period`, `year`, `quarter`
- `file_path`, `file_size`, `file_hash`
- `source_url`, `download_status`, `published_date`

**Scraping Logs**: Audit trail of scraping activities
- `scraper_name`, `action`, `status`
- `documents_found`, `documents_downloaded`, `execution_time`

## 🗂️ File Organization

Documents are organized in the following structure:
```
data/downloads/
├── RELIANCE/
│   ├── 2023/
│   │   ├── annual_reports/
│   │   ├── quarterly_results/
│   │   └── presentations/
│   └── 2024/
└── TCS/
    ├── 2023/
    └── 2024/
```

## 🔧 Configuration

Key settings in `config/settings.py`:

```python
# Database (SQLite)
DATABASE_URL = "sqlite:///data/indian_filings.db"

# Scraping
REQUEST_DELAY = 2.0  # Delay between requests
MAX_RETRIES = 3      # Retry failed requests
REQUEST_TIMEOUT = 30  # Request timeout

# File validation
MIN_FILE_SIZE = 50 * 1024     # 50KB minimum
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB maximum
```

## 📋 Monitoring

### Logs Location
- **Application logs**: `data/logs/pipeline.log`
- **Error logs**: `data/logs/errors.log`  
- **Scraper logs**: `data/logs/scrapers.log`
- **Session logs**: `data/logs/session_*.log`

### Health Monitoring
```bash
# Check system health
python scripts/health_check.py

# View recent logs
tail -f data/logs/pipeline.log
```

### Database Monitoring
Access SQLite-web at `http://localhost:8080` for database management

## 🐛 Troubleshooting

### Common Issues

**Database connection failed:**
```bash
# Check if database file exists and is writable
ls -la data/indian_filings.db

# Test connection manually
python -c "from src.database.connection import test_database_connection; print(test_database_connection())"
```

**Scraping errors:**
```bash
# Check logs for specific errors
grep ERROR data/logs/scrapers.log

# Run with debug logging
python scripts/run_scraper.py --log-level DEBUG --limit 1
```

**File permission issues:**
```bash
# Fix permissions
chmod -R 755 data/
chown -R $USER:$USER data/
```

**Missing dependencies:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Error Codes

- **Exit 0**: Success
- **Exit 1**: General failure or validation error
- **Database issues**: Check DATABASE_URL in .env and ensure data directory is writable
- **File system issues**: Check directory permissions
- **Network issues**: Check internet connection and rate limiting

## 🧪 Testing

**Run basic tests:**
```bash
# Health check
python scripts/health_check.py

# Database test
python -c "from src.database.connection import test_database_connection; print(test_database_connection())"

# File system test
python -c "from src.storage.file_manager import FileManager; fm = FileManager(); print('File system OK')"
```

## 📈 Performance

### Expected Performance (50 companies)
- **NSE Scraper**: ~5-10 documents per company
- **BSE Scraper**: ~3-8 documents per company  
- **Screener.in Scraper**: ~2-5 documents per company
- **Download speed**: 1-2 MB/min (with 2s delays)
- **Processing time**: 20-40 minutes for full run (all 3 scrapers)
- **Storage usage**: 500MB-2GB for complete dataset

### Optimization Tips
- Adjust `REQUEST_DELAY` for faster/slower scraping
- Use `--limit` for testing with fewer companies
- Monitor logs for rate limiting issues
- Use Docker for consistent performance

## 🛠️ Development

### Adding New Scrapers
1. Create new scraper class inheriting from `BaseScraper`
2. Implement `discover_documents()` and `scrape_company()` methods
3. Add to `run_scraper.py` scrapers list
4. Update company data with new source URLs

### Database Migrations
```bash
# Create new migration
# (Will be added in future weeks with Alembic)

# For now, modify models.py and recreate tables
python scripts/setup_database.py
```

## 📝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-scraper`)
3. Make changes and test thoroughly
4. Commit changes (`git commit -am 'Add new scraper'`)
5. Push to branch (`git push origin feature/new-scraper`)
6. Create Pull Request

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

## 🤝 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review logs in `data/logs/`
3. Run health check: `python scripts/health_check.py`
4. Create an issue with error logs and steps to reproduce

---

**Next Week**: PDF text extraction and document processing pipeline