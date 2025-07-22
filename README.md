# APRA AMCOS Song Catalogue Search

A Python script to search the APRA AMCOS Song Catalogue for songs by title, writer surname, or performer name. This tool allows you to search for copyright information from the command line.

## Features

- **Command-line interface** for single searches
- **Comprehensive data extraction**: title, writers, performers, publishers, AMCOS control percentage, alternate titles, and local work status
- **Multiple search parameters**: search by song title, writer surname, and/or performer name
- **Error handling** for network issues and invalid responses  
- **Session management** with proper headers and cookies
- **Verbose output** for debugging and detailed information

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. If you don't have uv installed:

```bash
# Install uv (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv
```

### Clone and Setup

```bash
git clone <repository-url>
cd apra2

# Dependencies are automatically managed by uv
# The script will install them when first run
```

## Usage

### Command Line Interface

```bash
./apra_search.py [OPTIONS]
```

**Options:**
- `--title, -t`: Song title to search for
- `--writer, -w`: Writer surname (last name only)  
- `--performer, -p`: Performer name
- `--verbose, -v`: Verbose output (shows search parameters and URL)
- `--help, -h`: Show help message

**Requirements:**
- At least one of `--title` or `--performer` must be specified
- Writer searches require either title or performer

### Examples

**Search by title and performer:**
```bash
./apra_search.py --title "ordinary" --performer "alex warren"
```

**Search by title and writer:**
```bash
./apra_search.py --title "bohemian rhapsody" --writer "mercury"
```

**Search by performer only:**
```bash
./apra_search.py --performer "the beatles"
```

**Verbose output:**
```bash
./apra_search.py --title "ordinary" --performer "alex warren" --verbose
```

## Example Output

```
Found 1 result(s):
==================================================
Title: ORDINARY
Work ID: GW74660605
AMCOS Control: 100%
Local Work: No
Writers (4): YARON ADAM, SHAPIRO CAL, HUGHES ALEXANDER WARREN, CHAPMAN MARGARET ELIZABETH
Performers (30): ANDYLP, VARIOUS ARTISTS, ADAM FEDIY, ALEX WARREN, ALEX WARREN (TIK TOK CONTRIBUTOR)... (+25 more)
Publishers (3): SONY MUSIC PUBLISHING (AUSTRALIA) P/L, WARNER CHAPPELL MUSIC AUSTRALIA PTY LTD, MUSHROOM MUSIC/HIPGNOSIS
Alternate Titles: ORDINARY (OFFICIAL MUSIC VIDEO), ALEX WARREN - ORDINARY
```

## Python API Usage

The script can also be imported and used programmatically:

```python
from apra_search import search_apra_catalogue

# Search for a song
result = search_apra_catalogue(
    title="ordinary", 
    performer="alex warren"
)

if result['found']:
    print(f"Found {result['count']} result(s)")
    for song in result['results']:
        print(f"Title: {song['title']}")
        print(f"Writers: {', '.join(song['writers'])}")
else:
    print(result['message'])
```

## Return Data Structure

The search function returns a dictionary with:

```python
{
    'found': bool,           # Whether results were found
    'count': int,           # Number of results returned
    'results': [            # List of song dictionaries
        {
            'work_id': str,           # APRA work ID (e.g., "GW74660605")
            'title': str,             # Song title
            'writers': [str],         # List of writer names
            'performers': [str],      # List of performer names
            'publishers': [str],      # List of publisher names
            'amcos_control': str,     # AMCOS control percentage (e.g., "100%")
            'alternate_titles': [str], # Alternative titles
            'local_work': bool        # Whether it's a local work
        }
    ],
    'message': str,         # Status message
    'search_url': str       # The search URL used
}
```

## Future Enhancements

The script is designed to support future batch processing capabilities:

- **CSV input**: Process multiple searches from a CSV file
- **JSON/CSV output**: Export results in structured formats
- **Rate limiting**: Respectful requests to the APRA AMCOS server
- **Progress tracking**: Status updates for large batch operations

## Technical Notes

### How It Works

1. **Session Management**: Creates a requests session to handle cookies and headers
2. **Initial Page Load**: Visits the search page to establish session
3. **Search Request**: Submits search parameters via GET (and POST fallback)
4. **HTML Parsing**: Uses BeautifulSoup to extract structured data from results
5. **Data Cleaning**: Processes and formats the extracted information

### Limitations

- The APRA AMCOS website may use JavaScript rendering for some searches
- Search results are limited to what's publicly available on the website
- Rate limiting should be implemented for heavy usage
- Some concatenated names in the source data may need manual cleanup

### Dependencies

- `requests`: HTTP client for web requests
- `beautifulsoup4`: HTML parsing and data extraction
- `typing`: Type hints support

## Troubleshooting

**"No results found" when results should exist:**
- The website may be using JavaScript rendering
- Try different search terms or combinations
- Check if the website structure has changed

**Network errors:**
- Check internet connection
- The APRA AMCOS website may be temporarily unavailable
- Try again after a few minutes

**Permission errors:**
```bash
chmod +x apra_search_final.py
```

## License

This tool is for educational and research purposes. Please respect the APRA AMCOS website's terms of service and use responsibly.

## Contributing

Feel free to submit issues and enhancement requests. This tool was designed to be easily extensible for additional features like batch processing.