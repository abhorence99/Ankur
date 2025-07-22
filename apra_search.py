#!/usr/bin/env uv run python
"""
APRA AMCOS Song Catalogue Search Script (Production Version)

Searches the APRA AMCOS catalogue using Playwright with proper JavaScript handling.
Replaces the original apra_search.py with a working Playwright implementation.
"""

import argparse
import sys
import re
import time
from typing import Dict, List, Optional, Any
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup


def search_apra_catalogue(title: Optional[str] = None, 
                         writer_surname: Optional[str] = None, 
                         performer: Optional[str] = None,
                         headless: bool = True,
                         verbose: bool = False) -> Dict[str, Any]:
    """
    Search APRA AMCOS Song Catalogue using Playwright browser automation
    """
    
    if not title and not performer:
        return {
            'found': False,
            'count': 0,
            'results': [],
            'message': 'Error: Title or performer is required for search'
        }
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=headless, timeout=90000)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            page.set_default_timeout(60000)
            
            if verbose:
                print("Loading APRA AMCOS search page...", file=sys.stderr)
            
            # Load the page
            page.goto("https://www.apraamcos.com.au/works-search", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)  # Wait for dynamic content
            
            if verbose:
                print("Filling search form...", file=sys.stderr)
            
            # Use JavaScript to find, fill, and submit the form
            search_script = f"""
            () => {{
                // Find search inputs by placeholder
                const inputs = document.querySelectorAll('input[type="search"]');
                let titleInput = null;
                let writerInput = null;
                let performerInput = null;
                
                inputs.forEach(input => {{
                    const placeholder = input.placeholder || '';
                    if (placeholder.toLowerCase().includes('song title')) {{
                        titleInput = input;
                    }} else if (placeholder.toLowerCase().includes('writer')) {{
                        writerInput = input;
                    }} else if (placeholder.toLowerCase().includes('performer')) {{
                        performerInput = input;
                    }}
                }});
                
                // Fill the fields
                const fillField = (input, value) => {{
                    if (input && value) {{
                        input.value = value;
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return true;
                    }}
                    return false;
                }};
                
                const filled = {{
                    title: fillField(titleInput, "{title or ''}"),
                    writer: fillField(writerInput, "{writer_surname or ''}"),
                    performer: fillField(performerInput, "{performer or ''}")
                }};
                
                // Submit the search
                if (titleInput) {{
                    titleInput.focus();
                    titleInput.dispatchEvent(new KeyboardEvent('keydown', {{
                        key: 'Enter',
                        code: 'Enter',
                        which: 13,
                        keyCode: 13,
                        bubbles: true
                    }}));
                }}
                
                return filled;
            }}
            """
            
            # Execute the form filling and submission
            fill_result = page.evaluate(search_script)
            
            if verbose:
                print(f"Form filled: {fill_result}", file=sys.stderr)
                print("Waiting for search results...", file=sys.stderr)
            
            # Wait for results to load - try multiple strategies
            results_loaded = False
            
            # Strategy 1: Wait for URL to include search parameters
            for i in range(15):  # 15 seconds max
                current_url = page.url
                if 'title=' in current_url or 'performer=' in current_url:
                    if verbose:
                        print(f"✓ Search URL detected: {current_url}", file=sys.stderr)
                    break
                page.wait_for_timeout(1000)
            
            # Strategy 2: Wait for dynamic content to appear
            page.wait_for_timeout(5000)  # Base wait for content to load
            
            # Strategy 3: Extended wait for results with checking
            for attempt in range(20):  # Check every 2 seconds for up to 40 seconds
                try:
                    # Check for various result indicators
                    page_content = page.content()
                    soup = BeautifulSoup(page_content, 'html.parser')
                    
                    # Check for result divs
                    result_divs = soup.find_all('div', id=re.compile(r'^GW\d+'))
                    if result_divs:
                        if verbose:
                            print(f"✓ Found {len(result_divs)} work containers", file=sys.stderr)
                        results_loaded = True
                        break
                    
                    # Check for results header
                    results_header = soup.find('h6', string=re.compile(r'\d+\s+results?'))
                    if results_header:
                        if verbose:
                            print(f"✓ Found results header: {results_header.get_text()}", file=sys.stderr)
                        results_loaded = True
                        break
                    
                    # Check page text for our search terms
                    page_text = soup.get_text().lower()
                    if title and title.lower() in page_text and ('writer' in page_text or 'performer' in page_text):
                        if verbose:
                            print("✓ Found search term in results content", file=sys.stderr)
                        results_loaded = True
                        break
                    
                    # Check for "no results" message
                    if 'no results' in page_text or '0 results' in page_text:
                        if verbose:
                            print("✓ 'No results' message detected", file=sys.stderr)
                        results_loaded = True
                        break
                        
                except Exception as e:
                    if verbose:
                        print(f"Error checking results (attempt {attempt + 1}): {e}", file=sys.stderr)
                
                # Progress indicator
                if verbose and (attempt + 1) % 5 == 0:
                    print(f"Still waiting for results... ({(attempt + 1) * 2}s)", file=sys.stderr)
                
                page.wait_for_timeout(2000)  # Wait 2 seconds before next check
            
            # Get final page content
            final_content = page.content()
            
            # Save for debugging
            with open('apra_search_results.html', 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            if verbose:
                print("✓ Final content saved to apra_search_results.html", file=sys.stderr)
            
            # Parse the results
            result = parse_search_results(final_content, page.url, verbose)
            return result
            
        except Exception as e:
            return {
                'found': False,
                'count': 0,
                'results': [],
                'message': f'Search error: {str(e)}'
            }
        finally:
            if 'browser' in locals():
                browser.close()


def parse_search_results(html_content: str, search_url: str, verbose: bool = False) -> Dict[str, Any]:
    """Parse HTML response to extract search results"""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for results count header
    results_header = soup.find('h6', string=re.compile(r'\d+\s+results?'))
    
    # Look for work containers
    result_divs = soup.find_all('div', id=re.compile(r'^GW\d+'))
    
    if verbose:
        print(f"Parsing results: header={'found' if results_header else 'not found'}, containers={len(result_divs)}", file=sys.stderr)
    
    # Check if we have no results
    if not results_header and not result_divs:
        page_text = soup.get_text().lower()
        no_results_indicators = ['no results found', '0 results', 'sorry, no results', 'nothing found']
        
        for indicator in no_results_indicators:
            if indicator in page_text:
                return {
                    'found': False,
                    'count': 0,
                    'results': [],
                    'message': 'Search completed but found no results',
                    'search_url': search_url
                }
        
        return {
            'found': False,
            'count': 0,
            'results': [],
            'message': 'No results found (check apra_search_results.html for debugging)',
            'search_url': search_url
        }
    
    # Parse individual results
    results = []
    for result_div in result_divs:
        parsed_result = parse_single_result(result_div)
        if parsed_result:
            results.append(parsed_result)
    
    # Get count from header if available
    count = len(results)
    if results_header:
        count_match = re.search(r'(\d+)\s+results?', results_header.get_text())
        if count_match:
            count = int(count_match.group(1))
    
    if verbose:
        print(f"Parsed {len(results)} results successfully", file=sys.stderr)
    
    return {
        'found': len(results) > 0,
        'count': count,
        'results': results,
        'message': f'Found {len(results)} result(s)',
        'search_url': search_url
    }


def parse_single_result(result_div) -> Optional[Dict[str, Any]]:
    """Parse a single search result"""
    
    try:
        result = {
            'work_id': result_div.get('id', ''),
            'title': '',
            'writers': [],
            'performers': [],
            'publishers': [],
            'amcos_control': '',
            'alternate_titles': [],
            'local_work': False
        }
        
        # Extract title
        title_h4 = result_div.find('h4')
        if title_h4:
            result['title'] = ''.join(title_h4.stripped_strings)
        
        # Parse list items for different fields
        list_items = result_div.find_all('li', class_='grid')
        
        for item in list_items:
            label_div = item.find('div', class_='font-medium')
            content_div = item.find('div', class_='caption')
            
            if not label_div or not content_div:
                continue
                
            label = label_div.get_text(strip=True).lower()
            
            if 'writers' in label:
                writers = []
                writer_list = content_div.find('ul')
                if writer_list:
                    for li in writer_list.find_all('li'):
                        writer_name = ''.join(li.stripped_strings)
                        if writer_name:
                            writers.append(writer_name)
                result['writers'] = writers
                
            elif 'work id' in label:
                result['work_id'] = content_div.get_text(strip=True)
                
            elif 'amcos control' in label:
                result['amcos_control'] = content_div.get_text(strip=True)
                
            elif 'alternate titles' in label:
                titles = []
                title_list = content_div.find('ul')
                if title_list:
                    for li in title_list.find_all('li'):
                        titles.append(li.get_text(strip=True))
                result['alternate_titles'] = titles
                
            elif 'publishers' in label:
                publishers = []
                pub_list = content_div.find('ul')
                if pub_list:
                    for li in pub_list.find_all('li'):
                        pub_text = li.get_text(strip=True)
                        pub_clean = re.sub(r'- APRA.*?- AMCOS.*?$', '', pub_text).strip()
                        if pub_clean:
                            publishers.append(pub_clean)
                result['publishers'] = publishers
                
            elif 'local work' in label:
                has_green_tick = content_div.find('path', fill='#0B9C00')
                result['local_work'] = bool(has_green_tick)
                
            elif 'performers' in label:
                performers = []
                perf_list = content_div.find('ul')
                if perf_list:
                    for li in perf_list.find_all('li'):
                        perf_name = ''.join(li.stripped_strings)
                        if perf_name:
                            performers.append(perf_name)
                result['performers'] = performers
        
        return result
        
    except Exception as e:
        print(f"Error parsing result: {e}", file=sys.stderr)
        return None


def format_result_output(result: Dict[str, Any]) -> str:
    """Format a single result for display"""
    
    output = []
    output.append(f"Title: {result['title']}")
    output.append(f"Work ID: {result['work_id']}")
    output.append(f"AMCOS Control: {result['amcos_control']}")
    output.append(f"Local Work: {'Yes' if result['local_work'] else 'No'}")
    
    if result['writers']:
        output.append(f"Writers ({len(result['writers'])}): {', '.join(result['writers'])}")
    
    if result['performers']:
        perf_count = len(result['performers'])
        if perf_count <= 5:
            output.append(f"Performers ({perf_count}): {', '.join(result['performers'])}")
        else:
            output.append(f"Performers ({perf_count}): {', '.join(result['performers'][:5])}... (+{perf_count-5} more)")
    
    if result['publishers']:
        output.append(f"Publishers ({len(result['publishers'])}): {', '.join(result['publishers'])}")
    
    if result['alternate_titles']:
        output.append(f"Alternate Titles: {', '.join(result['alternate_titles'])}")
    
    return '\n'.join(output)


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(
        description='Search APRA AMCOS Song Catalogue',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --title "ordinary" --performer "alex warren"
  %(prog)s --title "bohemian rhapsody" --writer "mercury"
  %(prog)s --performer "the beatles"
        """)
    
    parser.add_argument('--title', '-t', help='Song title to search for')
    parser.add_argument('--writer', '-w', help='Writer surname (last name only)')
    parser.add_argument('--performer', '-p', help='Performer name')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--show-browser', action='store_true', help='Show browser window (for debugging)')
    
    args = parser.parse_args()
    
    # Check that at least title or performer is provided
    if not args.title and not args.performer:
        parser.error("Either --title or --performer must be specified")
    
    # Perform search
    if args.verbose:
        print(f"Searching for:", file=sys.stderr)
        if args.title:
            print(f"  Title: {args.title}", file=sys.stderr)
        if args.writer:
            print(f"  Writer: {args.writer}", file=sys.stderr)
        if args.performer:
            print(f"  Performer: {args.performer}", file=sys.stderr)
        print(file=sys.stderr)
    
    result = search_apra_catalogue(
        title=args.title,
        writer_surname=args.writer,
        performer=args.performer,
        headless=not args.show_browser,
        verbose=args.verbose
    )
    
    # Display results
    if result['found']:
        print(f"Found {result['count']} result(s):")
        print("=" * 50)
        
        for i, res in enumerate(result['results'], 1):
            if i > 1:
                print("-" * 50)
            print(format_result_output(res))
        
        if args.verbose:
            print(f"\nSearch URL: {result.get('search_url', '')}", file=sys.stderr)
    else:
        print(result['message'])
        if args.verbose:
            print(f"Search URL: {result.get('search_url', '')}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()